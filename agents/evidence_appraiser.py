import re
from typing import Dict, Any, List
from .base_agent import BaseAgent


class EvidenceAppraiser(BaseAgent):
    """Agent 3: Hybrid ranking combining semantic, numeric, and keyword signals."""

    def __init__(self):
        super().__init__(
            name="Evidence Appraiser",
            description="Applies hybrid ranking to retrieved evidence (semantic + numeric + keyword)"
        )

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        chunks = context.get("retrieved_chunks", [])
        query = context.get("expanded_query", context.get("query", ""))
        query_type = context.get("query_type", "clinical_management")

        self.log(f"Appraising {len(chunks)} evidence chunks...")

        if not chunks:
            context["ranked_evidence"] = []
            context["evidence_count"] = 0
            self.log("No chunks to appraise")
            return context

        scored_chunks = []
        for chunk in chunks:
            score = self._compute_hybrid_score(chunk, query, query_type)
            chunk["relevance_score"] = score
            scored_chunks.append(chunk)

        # Sort by relevance score
        scored_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Take top results
        top_k = min(10, len(scored_chunks))
        ranked_evidence = scored_chunks[:top_k]

        context["ranked_evidence"] = ranked_evidence
        context["evidence_count"] = len(ranked_evidence)
        context["all_appraised"] = len(scored_chunks)

        self.log(f"Ranked {len(scored_chunks)} chunks, selected top {top_k}")
        return context

    def _compute_hybrid_score(self, chunk: Dict[str, Any], query: str,
                              query_type: str) -> float:
        """Compute hybrid relevance score combining multiple signals."""
        # Semantic similarity score (from FAISS)
        semantic_score = chunk.get("similarity_score", 0.0)

        # Numeric relevance score
        numeric_score = self._compute_numeric_score(chunk, query_type)

        # Keyword match score
        keyword_score = self._compute_keyword_score(chunk, query)

        # Section relevance score
        section_score = self._compute_section_score(chunk, query_type)

        # Weighted combination
        weights = {
            "semantic": 0.40,
            "numeric": 0.20,
            "keyword": 0.25,
            "section": 0.15
        }

        # Adjust weights based on query type
        if query_type == "treatment":
            weights["numeric"] = 0.30
            weights["semantic"] = 0.30
        elif query_type == "diagnosis":
            weights["keyword"] = 0.30
            weights["numeric"] = 0.15

        final_score = (
            weights["semantic"] * semantic_score +
            weights["numeric"] * numeric_score +
            weights["keyword"] * keyword_score +
            weights["section"] * section_score
        )

        return round(final_score, 4)

    def _compute_numeric_score(self, chunk: Dict[str, Any], query_type: str) -> float:
        """Score chunks based on presence of actionable numeric data."""
        text = chunk.get("text", "")
        score = 0.0

        # Check for numeric data presence
        if chunk.get("has_numeric_data", False):
            score += 0.3

        # Specific numeric patterns
        dosage_pattern = r'\d+\.?\d*\s*(mg|mcg|µg|g|ml|mL|units?|IU)'
        if re.search(dosage_pattern, text, re.IGNORECASE):
            score += 0.3

        lab_pattern = r'\d+\.?\d*\s*(mg/dL|mmol/L|g/dL|mEq/L|ng/mL)'
        if re.search(lab_pattern, text, re.IGNORECASE):
            score += 0.2

        bp_pattern = r'\d+/\d+\s*mmHg'
        if re.search(bp_pattern, text, re.IGNORECASE):
            score += 0.2

        # Ranges (e.g., "140-180 mg/dL")
        range_pattern = r'\d+\.?\d*\s*-\s*\d+\.?\d*'
        if re.search(range_pattern, text):
            score += 0.1

        return min(score, 1.0)

    def _compute_keyword_score(self, chunk: Dict[str, Any], query: str) -> float:
        """Score based on keyword overlap with query."""
        text = chunk.get("text", "").lower()
        query_words = set(query.lower().split())

        # Remove common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "can", "shall",
                      "for", "and", "nor", "but", "or", "yet", "so", "at", "by",
                      "in", "of", "on", "to", "with", "from", "up", "about", "into",
                      "what", "how", "which", "who", "when", "where", "why", "this",
                      "that", "these", "those", "it", "its"}
        query_keywords = query_words - stop_words

        if not query_keywords:
            return 0.0

        matches = sum(1 for kw in query_keywords if kw in text)
        return matches / len(query_keywords)

    def _compute_section_score(self, chunk: Dict[str, Any], query_type: str) -> float:
        """Score based on section heading relevance."""
        section = chunk.get("section", "").lower()

        section_relevance = {
            "treatment": ["treatment", "therapy", "pharmacotherapy", "management", "dosing", "medication"],
            "diagnosis": ["diagnosis", "classification", "screening", "criteria", "staging"],
            "prevention": ["prevention", "prophylaxis", "screening", "monitoring", "follow-up"],
            "pharmacology": ["drug", "interaction", "contraindication", "safety", "adjustment", "dose"],
            "clinical_management": ["management", "treatment", "guidelines", "protocol"]
        }

        relevant_terms = section_relevance.get(query_type, section_relevance["clinical_management"])

        if any(term in section for term in relevant_terms):
            return 1.0
        return 0.3
