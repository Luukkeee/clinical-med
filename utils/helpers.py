import re
import hashlib
from typing import List, Dict, Any


def extract_numbers(text: str) -> List[Dict[str, Any]]:
    """Extract numeric values with context from text."""
    patterns = [
        (r'(\d+\.?\d*)\s*(%)', 'percentage'),
        (r'(\d+\.?\d*)\s*(mg|mcg|µg|g|kg|ml|mL|L|mmol|mEq|units?|IU)', 'dosage'),
        (r'(\d+\.?\d*)\s*(/\s*\d+\.?\d*)\s*(mmHg|mm\s*Hg)', 'blood_pressure'),
        (r'(\d+\.?\d*)\s*(mmHg|mm\s*Hg)', 'pressure'),
        (r'(\d+\.?\d*)\s*(mg/dL|mmol/L|g/dL|mEq/L|ng/mL|pg/mL|µg/dL)', 'lab_value'),
        (r'(\d+\.?\d*)\s*(bpm|beats?\s*per\s*min)', 'heart_rate'),
        (r'(\d+\.?\d*)\s*(breaths?\s*per\s*min|/min)', 'respiratory_rate'),
        (r'(\d+\.?\d*)\s*(°[CF]|degrees?\s*[CF])', 'temperature'),
        (r'(\d+\.?\d*)\s*(hours?|hrs?|minutes?|mins?|days?|weeks?|months?|years?)', 'duration'),
        (r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', 'range'),
    ]

    results = []
    for pattern, num_type in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            results.append({
                'value': match.group(0),
                'type': num_type,
                'position': match.start(),
                'context': text[max(0, match.start() - 30):match.end() + 30]
            })
    return results


def compute_similarity(text1: str, text2: str) -> float:
    """Compute simple text similarity using Jaccard index."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


def generate_doc_id(text: str) -> str:
    """Generate a unique document ID from text content."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


MEDICAL_ONTOLOGY = {
    "hypertension": ["high blood pressure", "HTN", "elevated BP", "arterial hypertension"],
    "diabetes": ["diabetes mellitus", "DM", "T2DM", "type 2 diabetes", "hyperglycemia"],
    "heart failure": ["HF", "CHF", "congestive heart failure", "cardiac failure", "ventricular dysfunction"],
    "myocardial infarction": ["MI", "heart attack", "STEMI", "NSTEMI", "acute coronary syndrome", "ACS"],
    "stroke": ["CVA", "cerebrovascular accident", "ischemic stroke", "hemorrhagic stroke", "TIA"],
    "asthma": ["bronchial asthma", "reactive airway disease", "bronchospasm"],
    "COPD": ["chronic obstructive pulmonary disease", "emphysema", "chronic bronchitis"],
    "pneumonia": ["lower respiratory tract infection", "CAP", "community-acquired pneumonia", "HAP"],
    "sepsis": ["septicemia", "systemic infection", "SIRS", "septic shock"],
    "anaphylaxis": ["anaphylactic shock", "severe allergic reaction", "type I hypersensitivity"],
    "atrial fibrillation": ["AFib", "AF", "atrial flutter", "irregular heartbeat"],
    "DVT": ["deep vein thrombosis", "venous thromboembolism", "VTE", "blood clot"],
    "pulmonary embolism": ["PE", "lung clot", "pulmonary thromboembolism"],
    "CKD": ["chronic kidney disease", "renal insufficiency", "renal failure"],
    "AKI": ["acute kidney injury", "acute renal failure", "renal impairment"],
    "cirrhosis": ["liver cirrhosis", "hepatic cirrhosis", "end-stage liver disease"],
    "GI bleeding": ["gastrointestinal hemorrhage", "upper GI bleed", "lower GI bleed", "melena", "hematemesis"],
    "thyroid": ["hypothyroidism", "hyperthyroidism", "thyroid disorder", "TSH"],
    "epilepsy": ["seizure disorder", "convulsions", "seizures"],
    "depression": ["major depressive disorder", "MDD", "clinical depression"],
    "warfarin": ["coumadin", "anticoagulant", "blood thinner"],
    "metformin": ["glucophage", "biguanide", "antidiabetic"],
    "lisinopril": ["ACE inhibitor", "ACEI", "prinivil", "zestril"],
    "amlodipine": ["norvasc", "calcium channel blocker", "CCB"],
    "atorvastatin": ["lipitor", "statin", "HMG-CoA reductase inhibitor"],
}


def expand_query_with_ontology(query: str) -> str:
    """Expand a clinical query with related medical terms."""
    expanded_terms = []
    query_lower = query.lower()

    for term, synonyms in MEDICAL_ONTOLOGY.items():
        if term.lower() in query_lower:
            expanded_terms.extend(synonyms[:3])
        for syn in synonyms:
            if syn.lower() in query_lower:
                expanded_terms.append(term)
                expanded_terms.extend([s for s in synonyms if s.lower() != syn.lower()][:2])
                break

    if expanded_terms:
        return f"{query} [Related: {', '.join(set(expanded_terms))}]"
    return query
