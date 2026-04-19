import json
from typing import Dict, Any
from .base_agent import BaseAgent


class ClinicalQueryAnalyst(BaseAgent):
    """Agent 1: Expands clinical queries using medical ontologies."""

    def __init__(self, llm_client=None):
        super().__init__(
            name="Clinical Query Analyst",
            description="Expands queries using medical ontologies and identifies clinical concepts"
        )
        self.llm = llm_client

    # Broad set of clinical / medical keywords used to decide if a query is relevant
    CLINICAL_KEYWORDS = {
        # conditions & body systems
        "hypertension", "diabetes", "asthma", "copd", "pneumonia", "sepsis",
        "anaphylaxis", "stroke", "heart", "cardiac", "renal", "kidney", "liver",
        "hepatic", "lung", "pulmonary", "thyroid", "cancer", "tumor", "infection",
        "fever", "pain", "inflammation", "edema", "bleeding", "hemorrhage",
        "anemia", "clot", "embolism", "thrombosis", "arrhythmia", "fibrillation",
        "infarction", "ischemia", "angina", "cholesterol", "lipid", "obesity",
        "seizure", "epilepsy", "migraine", "depression", "anxiety", "psychosis",
        "schizophrenia", "dementia", "alzheimer", "parkinson", "arthritis",
        "osteoporosis", "fracture", "allergy", "autoimmune", "hiv", "aids",
        "hepatitis", "tuberculosis", "malaria", "covid", "influenza", "vaccine",
        "pregnancy", "neonatal", "pediatric", "geriatric",
        # clinical actions
        "treatment", "therapy", "drug", "medication", "dose", "dosage",
        "prescri", "diagnos", "prognos", "symptom", "sign", "lab", "blood",
        "test", "screening", "imaging", "mri", "ct scan", "x-ray", "ultrasound",
        "biopsy", "surgery", "procedure", "transplant", "ventilat", "intubat",
        "transfusion", "dialysis", "chemotherapy", "radiation", "antibiotic",
        "antiviral", "antifungal", "analgesic", "opioid", "nsaid", "steroid",
        "insulin", "metformin", "statin", "ace inhibitor", "beta blocker",
        "diuretic", "anticoagul", "thrombolytic", "vasopressor", "epinephrine",
        # medical terms
        "clinical", "patient", "physician", "medical", "pathology", "physiology",
        "pharmacol", "toxicol", "contraindic", "adverse", "side effect",
        "interact", "prophyla", "prevent", "chronic", "acute", "emergency",
        "critical", "intensive care", "icu", "ER", "hospital",
        "guideline", "protocol", "triage", "vital", "bp", "mmhg",
        "mg", "ml", "mcg", "iv", "im", "oral", "subcutaneous", "intravenous",
        "hba1c", "egfr", "creatinine", "potassium", "sodium", "glucose",
        "hemoglobin", "platelet", "wbc", "ekg", "ecg", "echo",
        "cpap", "bipap", "oxygen", "saturation", "spo2",
        "first-line", "second-line", "monotherapy", "combination therapy",
        "disease", "disorder", "syndrome", "condition", "illness",
        "manage", "comorbid", "differential", "etiology", "pathogenesis",
        "mortal", "morbid", "survival", "remission", "relapse",
        "aki", "ckd", "stemi", "nstemi", "acs", "dvt", "pe", "vte",
        "dka", "hhs", "ards", "sirs", "gcs", "apache",
        "health", "wellbeing", "nutrition", "diet", "exercise",
    }

    REJECTION_RESPONSE = (
        "I'm sorry, but I can only assist with **clinical and medical queries**.\n\n"
        "I'm designed to answer questions about:\n"
        "- Disease diagnosis, treatment, and management\n"
        "- Medications, dosages, and drug interactions\n"
        "- Clinical guidelines and medical protocols\n"
        "- Lab values, imaging, and diagnostic criteria\n"
        "- Emergency and critical care management\n\n"
        "Please rephrase your question in a clinical context, or try one of the sample queries."
    )

    def _is_clinical_query(self, query: str) -> bool:
        """Return True if the query is related to clinical / medical topics."""
        query_lower = query.lower()
        # Check each keyword; use `in` so partial stems like "diagnos" match "diagnosis"
        for kw in self.CLINICAL_KEYWORDS:
            if kw in query_lower:
                return True
        return False

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "")
        self.log(f"Analyzing query: {query[:100]}...")

        # ── Clinical relevance gate ──────────────────────────────────
        if not self._is_clinical_query(query):
            self.log("Query rejected: not clinically relevant.")
            context["rejected"] = True
            context["response"] = self.REJECTION_RESPONSE
            context["original_query"] = query
            context["expanded_query"] = query
            context["medical_concepts"] = []
            context["query_type"] = "non_clinical"
            context["urgency"] = "routine"
            return context

        from utils.helpers import expand_query_with_ontology, MEDICAL_ONTOLOGY

        # Expand query with medical ontology
        expanded_query = expand_query_with_ontology(query)

        # Extract medical concepts from the query
        concepts = []
        query_lower = query.lower()
        for term, synonyms in MEDICAL_ONTOLOGY.items():
            if term.lower() in query_lower:
                concepts.append(term)
            for syn in synonyms:
                if syn.lower() in query_lower:
                    concepts.append(term)
                    break

        # Determine query type and urgency
        urgency = "routine"
        emergency_keywords = ["emergency", "urgent", "stat", "critical", "acute", "severe",
                              "shock", "arrest", "code", "crisis", "anaphylaxis", "bleeding",
                              "hemorrhage", "overdose", "poisoning"]
        if any(kw in query_lower for kw in emergency_keywords):
            urgency = "urgent"

        query_type = "clinical_management"
        if any(w in query_lower for w in ["diagnos", "criteria", "screening", "test"]):
            query_type = "diagnosis"
        elif any(w in query_lower for w in ["treat", "therap", "drug", "medicat", "dose", "prescri"]):
            query_type = "treatment"
        elif any(w in query_lower for w in ["prevent", "prophyla", "screen"]):
            query_type = "prevention"
        elif any(w in query_lower for w in ["interact", "contraindic", "side effect", "adverse"]):
            query_type = "pharmacology"

        # Use LLM for enhanced expansion if available
        if self.llm:
            try:
                system_prompt = (
                    "You are a clinical query analyst. Expand the following clinical query with "
                    "relevant medical terminology, related conditions, and key clinical concepts. "
                    "Return JSON with: expanded_query, medical_concepts (list), query_type, urgency."
                )
                response = self.llm.generate(system_prompt, query)
                try:
                    llm_result = json.loads(response)
                    if "expanded_query" in llm_result:
                        expanded_query = llm_result["expanded_query"]
                    if "medical_concepts" in llm_result:
                        concepts = list(set(concepts + llm_result["medical_concepts"]))
                except json.JSONDecodeError:
                    pass
            except Exception as e:
                self.log(f"LLM expansion failed, using ontology-based expansion: {e}")

        if not concepts:
            concepts = [w for w in query.split() if len(w) > 3][:5]

        context["expanded_query"] = expanded_query
        context["original_query"] = query
        context["medical_concepts"] = concepts
        context["query_type"] = query_type
        context["urgency"] = urgency

        self.log(f"Expanded query with {len(concepts)} medical concepts. Type: {query_type}, Urgency: {urgency}")
        return context
