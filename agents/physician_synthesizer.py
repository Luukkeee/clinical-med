from typing import Dict, Any
from .base_agent import BaseAgent


class PhysicianSynthesizer(BaseAgent):
    """Agent 4: Generates structured clinical response from ranked evidence."""

    def __init__(self, llm_client=None):
        super().__init__(
            name="Physician Synthesizer",
            description="Synthesizes clinical evidence into structured medical response"
        )
        self.llm = llm_client

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("original_query", context.get("query", ""))
        evidence = context.get("ranked_evidence", [])
        query_type = context.get("query_type", "clinical_management")
        urgency = context.get("urgency", "routine")

        self.log(f"Synthesizing response from {len(evidence)} evidence chunks...")

        if not evidence:
            context["response"] = "Insufficient evidence found to provide a clinical recommendation. Please consult primary medical references."
            context["citations"] = []
            return context

        # Build evidence text
        evidence_text = self._format_evidence(evidence)
        citations = self._extract_citations(evidence)

        # Generate response
        if self.llm and getattr(self.llm, 'mode', 'demo') == 'full':
            response = self._generate_with_llm(query, evidence_text, query_type, urgency)
            # If OpenAI API failed (quota/network), use evidence-based template instead of generic fallback
            if getattr(self.llm, 'last_call_failed', False):
                response = self._generate_template_response(query, evidence, query_type, urgency)
        else:
            response = self._generate_template_response(query, evidence, query_type, urgency)

        context["response"] = response
        context["citations"] = citations
        context["evidence_used"] = len(evidence)

        self.log(f"Generated response with {len(citations)} citations")
        return context

    def _format_evidence(self, evidence: list) -> str:
        """Format evidence chunks for LLM consumption."""
        parts = []
        for i, chunk in enumerate(evidence[:8], 1):
            source = chunk.get("document", "Unknown Source")
            section = chunk.get("section", "")
            text = chunk.get("text", "")
            score = chunk.get("relevance_score", 0)

            parts.append(
                f"[Evidence {i}] Source: {source} | Section: {section} | Relevance: {score:.2f}\n{text}"
            )
        return "\n\n".join(parts)

    def _extract_citations(self, evidence: list) -> list:
        """Extract citation information from evidence."""
        citations = []
        seen = set()
        for chunk in evidence:
            source = chunk.get("document", "Unknown")
            section = chunk.get("section", "")
            key = f"{source}|{section}"
            if key not in seen:
                seen.add(key)
                citations.append({
                    "source": source,
                    "section": section,
                    "category": chunk.get("category", ""),
                    "relevance_score": chunk.get("relevance_score", 0)
                })
        return citations

    def _generate_with_llm(self, query: str, evidence_text: str,
                           query_type: str, urgency: str) -> str:
        """Generate response using LLM."""
        system_prompt = f"""You are an expert physician synthesizer providing evidence-based clinical guidance.
Query Type: {query_type}
Urgency: {urgency}

CRITICAL RULES:
1. ONLY use information from the provided evidence. Do NOT hallucinate or add information not in the evidence.
2. Include specific numeric values (dosages, thresholds, lab values) from the evidence.
3. Structure your response with clear clinical headings.
4. If evidence is insufficient for any part, explicitly state that.
5. Include relevant warnings and contraindications.
6. Reference which evidence sources support each recommendation.

RESPONSE FORMAT:
**Clinical Assessment:**
[Brief assessment of the clinical question]

**Evidence-Based Recommendations:**
[Numbered recommendations with specific details from evidence]

**Key Values and Thresholds:**
[Relevant numeric values - dosages, lab targets, etc.]

**Warnings and Contraindications:**
[Safety information from the evidence]

**Evidence Quality:**
[Brief note on the strength of available evidence]"""

        user_prompt = f"""Clinical Query: {query}

Retrieved Evidence:
{evidence_text}

Provide a structured clinical response based ONLY on the above evidence."""

        return self.llm.generate(system_prompt, user_prompt, temperature=0.2)

    def _generate_template_response(self, query: str, evidence: list,
                                    query_type: str, urgency: str) -> str:
        """Generate response using templates when LLM is unavailable."""
        response_parts = []

        if urgency == "urgent":
            response_parts.append("**⚠️ URGENT CLINICAL QUERY**\n")

        response_parts.append("**Clinical Assessment:**")
        response_parts.append(f"Addressing clinical query regarding: {query}\n")

        response_parts.append("**Evidence-Based Recommendations:**")
        for i, chunk in enumerate(evidence[:5], 1):
            text = chunk.get("text", "")
            source = chunk.get("document", "Unknown")
            section = chunk.get("section", "")
            # Take first 2-3 sentences
            sentences = text.split(". ")
            summary = ". ".join(sentences[:3]) + ("." if not sentences[0].endswith(".") else "")
            response_parts.append(f"\n{i}. **{section}** (Source: {source})")
            response_parts.append(f"   {summary}")

        # Extract key numeric values
        import re
        numeric_values = []
        for chunk in evidence[:8]:
            text = chunk.get("text", "")
            numbers = re.findall(
                r'(?:\d+\.?\d*\s*(?:mg|mcg|g|kg|ml|mL|mmol|mEq|units?|IU|mg/dL|mmol/L|g/dL|mEq/L|mmHg|%|bpm)[/\w]*)',
                text, re.IGNORECASE
            )
            for n in numbers[:3]:
                if n not in numeric_values:
                    numeric_values.append(n)

        if numeric_values:
            response_parts.append("\n**Key Values and Thresholds:**")
            for val in numeric_values[:10]:
                response_parts.append(f"- {val}")

        response_parts.append("\n**Warnings:**")
        response_parts.append("- This response is based on retrieved clinical guidelines.")
        response_parts.append("- Always verify critical values with primary sources.")
        response_parts.append("- Individual patient factors must be considered.")

        response_parts.append(f"\n**Evidence Quality:**")
        avg_score = sum(c.get("relevance_score", 0) for c in evidence) / max(len(evidence), 1)
        response_parts.append(f"Based on {len(evidence)} evidence sources with average relevance score: {avg_score:.2f}")

        return "\n".join(response_parts)
