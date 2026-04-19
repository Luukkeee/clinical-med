import re
from typing import List, Dict, Any


class HybridRanker:
    """Hybrid ranking tool combining semantic, numeric, and keyword scoring."""

    def __init__(self):
        self.weights = {
            "semantic": 0.40,
            "numeric": 0.25,
            "keyword": 0.25,
            "freshness": 0.10
        }

    def rank(self, chunks: List[Dict[str, Any]], query: str,
             query_type: str = "general") -> List[Dict[str, Any]]:
        """Rank chunks using hybrid scoring."""
        scored = []
        for chunk in chunks:
            score = self._compute_score(chunk, query, query_type)
            chunk["hybrid_score"] = score
            scored.append(chunk)

        scored.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return scored

    def _compute_score(self, chunk: Dict[str, Any], query: str,
                       query_type: str) -> float:
        semantic = chunk.get("similarity_score", 0.0)
        numeric = self._numeric_score(chunk)
        keyword = self._keyword_score(chunk, query)
        freshness = self._freshness_score(chunk)

        return (
            self.weights["semantic"] * semantic +
            self.weights["numeric"] * numeric +
            self.weights["keyword"] * keyword +
            self.weights["freshness"] * freshness
        )

    def _numeric_score(self, chunk: Dict[str, Any]) -> float:
        if chunk.get("has_numeric_data", False):
            return 0.8
        text = chunk.get("text", "")
        if re.search(r'\d+\.?\d*\s*(mg|mcg|g|ml|mmHg|%|mg/dL|mmol/L)', text, re.I):
            return 0.6
        return 0.2

    def _keyword_score(self, chunk: Dict[str, Any], query: str) -> float:
        text = chunk.get("text", "").lower()
        query_words = set(query.lower().split())
        stop = {"the", "a", "an", "is", "are", "for", "and", "or", "to", "in", "of", "on",
                "what", "how", "which", "with", "this", "that"}
        keywords = query_words - stop
        if not keywords:
            return 0.0
        return sum(1 for k in keywords if k in text) / len(keywords)

    def _freshness_score(self, chunk: Dict[str, Any]) -> float:
        year = chunk.get("metadata", {}).get("year", 2020)
        if year >= 2024:
            return 1.0
        elif year >= 2022:
            return 0.8
        elif year >= 2020:
            return 0.6
        return 0.4
