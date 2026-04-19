import json
from typing import Dict, Any
from .base_agent import BaseAgent


class ConfidenceRiskAgent(BaseAgent):
    """Agent 6: Outputs confidence score and risk level for each response."""

    def __init__(self, llm_client=None):
        super().__init__(
            name="Confidence & Risk Agent",
            description="Calculates confidence score and clinical risk level for the response"
        )
        self.llm = llm_client

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Calculating confidence and risk scores...")

        safety_report = context.get("safety_report", {})
        evidence = context.get("ranked_evidence", [])
        query_type = context.get("query_type", "clinical_management")
        urgency = context.get("urgency", "routine")

        # Calculate confidence score
        confidence = self._calculate_confidence(safety_report, evidence, context)

        # Determine risk level
        risk_level = self._determine_risk_level(confidence, safety_report, urgency, query_type)

        # Build reasoning
        reasoning = self._build_reasoning(confidence, risk_level, safety_report, evidence)

        # LLM-based confidence assessment if available
        if self.llm:
            llm_assessment = self._llm_confidence_assessment(context)
            if llm_assessment:
                # Blend LLM assessment with calculated scores
                if "confidence_score" in llm_assessment:
                    llm_conf = llm_assessment["confidence_score"]
                    if isinstance(llm_conf, (int, float)):
                        confidence = round(0.6 * confidence + 0.4 * llm_conf, 2)

        context["confidence_score"] = confidence
        context["risk_level"] = risk_level
        context["confidence_reasoning"] = reasoning

        # Add confidence info to response
        response = context.get("response", "")
        confidence_block = (
            f"\n\n---\n"
            f"**Confidence:** {confidence:.0%}\n"
            f"**Risk Level:** {risk_level.capitalize()}\n"
        )
        context["response"] = response + confidence_block

        self.log(f"Confidence: {confidence:.0%}, Risk: {risk_level}")
        return context

    def _calculate_confidence(self, safety_report: Dict, evidence: list,
                              context: Dict) -> float:
        """Calculate overall confidence score."""
        scores = []

        # Factor 1: Grounding score (high weight)
        grounding = safety_report.get("grounding_score", 0.5)
        scores.append(("grounding", grounding, 0.30))

        # Factor 2: Evidence quantity and quality
        evidence_count = len(evidence)
        if evidence_count >= 8:
            evidence_score = 1.0
        elif evidence_count >= 5:
            evidence_score = 0.85
        elif evidence_count >= 3:
            evidence_score = 0.7
        elif evidence_count >= 1:
            evidence_score = 0.5
        else:
            evidence_score = 0.1
        scores.append(("evidence_quantity", evidence_score, 0.20))

        # Factor 3: Average relevance score of evidence
        if evidence:
            avg_relevance = sum(e.get("relevance_score", 0) for e in evidence) / len(evidence)
        else:
            avg_relevance = 0.0
        scores.append(("evidence_relevance", min(avg_relevance * 2, 1.0), 0.20))

        # Factor 4: Numeric validation
        numeric_status = safety_report.get("numeric_validation", "passed")
        if numeric_status == "passed":
            numeric_score = 1.0
        elif numeric_status == "warning":
            numeric_score = 0.6
        else:
            numeric_score = 0.3
        scores.append(("numeric_validation", numeric_score, 0.15))

        # Factor 5: Safety passed
        safety_passed = safety_report.get("safety_passed", False)
        safety_score = 1.0 if safety_passed else 0.4
        scores.append(("safety", safety_score, 0.15))

        # Weighted sum
        confidence = sum(score * weight for _, score, weight in scores)

        return round(max(0.05, min(0.99, confidence)), 2)

    def _determine_risk_level(self, confidence: float, safety_report: Dict,
                              urgency: str, query_type: str) -> str:
        """Determine clinical risk level."""
        # Base risk from confidence
        if confidence >= 0.85:
            risk = "low"
        elif confidence >= 0.65:
            risk = "moderate"
        else:
            risk = "high"

        # Elevate risk for safety issues
        if safety_report.get("dangerous_content", False):
            risk = "high"

        if safety_report.get("numeric_validation") == "failed":
            risk = max(risk, "moderate", key=lambda x: ["low", "moderate", "high"].index(x))

        # Elevate risk for urgent/treatment queries
        if urgency == "urgent" and risk == "low":
            risk = "moderate"

        if query_type == "treatment" and risk == "low" and confidence < 0.90:
            risk = "moderate"

        return risk

    def _build_reasoning(self, confidence: float, risk_level: str,
                         safety_report: Dict, evidence: list) -> str:
        """Build human-readable reasoning for the scores."""
        reasons = []

        if confidence >= 0.85:
            reasons.append("Response is well-grounded in retrieved evidence.")
        elif confidence >= 0.65:
            reasons.append("Response is partially supported by evidence with some gaps.")
        else:
            reasons.append("Limited evidence support for this response.")

        if evidence:
            avg_rel = sum(e.get("relevance_score", 0) for e in evidence) / len(evidence)
            reasons.append(f"Average evidence relevance: {avg_rel:.2f}")

        grounding = safety_report.get("grounding_score", 0)
        reasons.append(f"Grounding score: {grounding:.0%}")

        if safety_report.get("numeric_mismatches"):
            reasons.append(f"Numeric mismatches found: {len(safety_report['numeric_mismatches'])}")

        if safety_report.get("danger_flags"):
            reasons.append(f"Safety flags: {len(safety_report['danger_flags'])}")

        return " | ".join(reasons)

    def _llm_confidence_assessment(self, context: Dict) -> Dict:
        """Use LLM for confidence assessment."""
        response = context.get("response", "")[:500]
        evidence_count = context.get("evidence_count", 0)

        system_prompt = """You are a clinical confidence assessor. Evaluate the confidence and risk of a clinical AI response.
Return JSON: {"confidence_score": 0.0-1.0, "risk_level": "low/moderate/high", "reasoning": "brief explanation"}"""

        user_prompt = f"""Response preview: {response}
Evidence chunks used: {evidence_count}
Query type: {context.get('query_type', 'unknown')}"""

        try:
            result = self.llm.generate(system_prompt, user_prompt, temperature=0.1)
            return json.loads(result)
        except Exception:
            return {}
