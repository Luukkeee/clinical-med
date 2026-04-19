import re
import json
from typing import Dict, Any, List
from .base_agent import BaseAgent


class PatientSafetyOfficer(BaseAgent):
    """Agent 5: Validates response grounding and numeric accuracy."""

    def __init__(self, llm_client=None):
        super().__init__(
            name="Patient Safety Officer",
            description="Performs grounding validation and numeric cross-verification for safety"
        )
        self.llm = llm_client

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        response = context.get("response", "")
        evidence = context.get("ranked_evidence", [])

        self.log("Running safety validation...")

        # Sentence-level grounding check
        grounding_result = self._check_grounding(response, evidence)

        # Numeric cross-verification
        numeric_result = self._verify_numerics(response, evidence)

        # Check for dangerous content
        danger_flags = self._check_dangerous_content(response)

        # LLM-based safety check if available
        llm_safety = {}
        if self.llm:
            llm_safety = self._llm_safety_check(response, evidence)

        # Compile safety report
        safety_report = {
            "grounding_score": grounding_result["score"],
            "grounded_sentences": grounding_result["grounded"],
            "total_sentences": grounding_result["total"],
            "ungrounded_sentences": grounding_result["ungrounded_list"],
            "numeric_validation": numeric_result["status"],
            "numeric_mismatches": numeric_result["mismatches"],
            "numeric_verified": numeric_result["verified"],
            "dangerous_content": danger_flags["has_dangerous"],
            "danger_flags": danger_flags["flags"],
            "safety_passed": (
                grounding_result["score"] >= 0.7
                and numeric_result["status"] == "passed"
                and not danger_flags["has_dangerous"]
            )
        }

        if llm_safety:
            safety_report["llm_safety_check"] = llm_safety

        # Add warnings to response if safety issues found
        if not safety_report["safety_passed"]:
            warnings = self._generate_safety_warnings(safety_report)
            context["response"] = response + "\n\n" + warnings

        context["safety_report"] = safety_report

        self.log(
            f"Safety check: grounding={grounding_result['score']:.2f}, "
            f"numerics={numeric_result['status']}, "
            f"dangerous={danger_flags['has_dangerous']}"
        )
        return context

    def _check_grounding(self, response: str, evidence: List[Dict]) -> Dict:
        """Check if response sentences are grounded in evidence."""
        # Extract sentences from response (skip headers and empty lines)
        lines = response.split("\n")
        sentences = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("**") or line.startswith("#") or line.startswith("-"):
                continue
            for sent in re.split(r'(?<=[.!?])\s+', line):
                sent = sent.strip()
                if len(sent) > 20:
                    sentences.append(sent)

        if not sentences:
            return {"score": 1.0, "grounded": 0, "total": 0, "ungrounded_list": []}

        evidence_text = " ".join(chunk.get("text", "") for chunk in evidence).lower()

        grounded = 0
        ungrounded_list = []
        for sent in sentences:
            # Check if key terms from sentence appear in evidence
            words = set(sent.lower().split())
            stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "and",
                          "or", "for", "to", "in", "of", "on", "at", "by", "with",
                          "this", "that", "it", "its", "as", "from", "not", "but"}
            key_words = words - stop_words
            key_words = {w for w in key_words if len(w) > 2}

            if not key_words:
                grounded += 1
                continue

            matches = sum(1 for w in key_words if w in evidence_text)
            overlap = matches / len(key_words) if key_words else 0

            if overlap >= 0.4:
                grounded += 1
            else:
                ungrounded_list.append(sent[:80])

        total = len(sentences)
        score = grounded / total if total > 0 else 1.0

        return {
            "score": round(score, 2),
            "grounded": grounded,
            "total": total,
            "ungrounded_list": ungrounded_list[:5]
        }

    def _verify_numerics(self, response: str, evidence: List[Dict]) -> Dict:
        """Verify numeric values in response against evidence."""
        from utils.helpers import extract_numbers

        response_numbers = extract_numbers(response)
        evidence_text = " ".join(chunk.get("text", "") for chunk in evidence)
        evidence_numbers = extract_numbers(evidence_text)

        if not response_numbers:
            return {"status": "passed", "mismatches": [], "verified": 0}

        evidence_values = set()
        for num in evidence_numbers:
            evidence_values.add(num["value"].strip().lower())

        verified = 0
        mismatches = []
        for num in response_numbers:
            val = num["value"].strip().lower()
            if val in evidence_values:
                verified += 1
            else:
                # Check if the number is close to any evidence number
                found = False
                for ev_val in evidence_values:
                    if val in ev_val or ev_val in val:
                        found = True
                        verified += 1
                        break
                if not found:
                    mismatches.append({
                        "value": num["value"],
                        "type": num["type"],
                        "context": num["context"]
                    })

        status = "passed" if len(mismatches) <= 1 else "warning"
        if len(mismatches) > 3:
            status = "failed"

        return {
            "status": status,
            "mismatches": mismatches[:5],
            "verified": verified,
            "total_checked": len(response_numbers)
        }

    def _check_dangerous_content(self, response: str) -> Dict:
        """Check for potentially dangerous medical content."""
        flags = []
        response_lower = response.lower()

        # Check for absolute statements without qualifiers
        absolute_patterns = [
            (r'\b(always|never)\b.*(?:take|give|administer|prescribe)', "Absolute treatment directive without qualification"),
            (r'(?:stop|discontinue)\s+all\s+medication', "Blanket medication discontinuation advice"),
            (r'no\s+need\s+(?:for|to)\s+(?:consult|see|visit)\s+(?:a\s+)?(?:doctor|physician)', "Discouraging medical consultation"),
        ]

        for pattern, msg in absolute_patterns:
            if re.search(pattern, response_lower):
                flags.append(msg)

        # Check for potentially dangerous drug combinations mentioned positively
        dangerous_combos = [
            ("maoi", "ssri", "Potentially dangerous MAOI-SSRI combination"),
            ("warfarin", "aspirin", "Note: Warfarin-aspirin combination requires careful monitoring"),
        ]

        for drug1, drug2, msg in dangerous_combos:
            if drug1 in response_lower and drug2 in response_lower:
                if "contraindicated" not in response_lower and "avoid" not in response_lower:
                    flags.append(msg)

        return {
            "has_dangerous": len(flags) > 0,
            "flags": flags
        }

    def _llm_safety_check(self, response: str, evidence: List[Dict]) -> Dict:
        """Use LLM for additional safety checking."""
        evidence_text = " ".join(chunk.get("text", "")[:200] for chunk in evidence[:5])

        system_prompt = """You are a patient safety officer reviewing a clinical AI response.
Check for:
1. Claims not supported by the evidence
2. Incorrect numeric values
3. Dangerous or misleading recommendations
4. Missing important safety warnings

Return JSON: {"safety_issues": [], "grounding_score": 0.0-1.0, "numeric_validation": "passed/failed", "dangerous_content": false}"""

        user_prompt = f"""Response to review:
{response[:1000]}

Evidence sources:
{evidence_text[:1000]}"""

        try:
            result = self.llm.generate(system_prompt, user_prompt, temperature=0.1)
            return json.loads(result)
        except Exception:
            return {}

    def _generate_safety_warnings(self, safety_report: Dict) -> str:
        """Generate safety warning text."""
        warnings = ["---", "**⚠️ Safety Warnings:**"]

        if safety_report["grounding_score"] < 0.7:
            warnings.append(
                f"- Grounding score: {safety_report['grounding_score']:.0%}. "
                "Some statements may not be fully supported by retrieved evidence."
            )

        if safety_report["numeric_validation"] != "passed":
            warnings.append(
                "- Numeric validation: Some values could not be verified against source evidence. "
                "Please verify all dosages and thresholds with primary references."
            )

        if safety_report["dangerous_content"]:
            for flag in safety_report["danger_flags"]:
                warnings.append(f"- ⚠️ {flag}")

        warnings.append("- **Always consult qualified healthcare providers for clinical decisions.**")
        return "\n".join(warnings)
