import os
import json
from typing import List, Dict, Any, Optional


class LLMClient:
    """LLM client supporting OpenAI API and demo mode."""

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini", mode: str = "demo"):
        self.model = model
        self.mode = mode
        self.api_key = api_key
        self._client = None
        self.last_call_failed = False

        if self.mode == "full" and self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                print("Warning: openai package not installed. Falling back to demo mode.")
                self.mode = "demo"

    def generate(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Generate a response from the LLM."""
        if self.mode == "full" and self._client:
            return self._call_openai(system_prompt, user_prompt, temperature, max_tokens)
        return self._demo_generate(system_prompt, user_prompt)

    def _call_openai(self, system_prompt: str, user_prompt: str,
                     temperature: float, max_tokens: int) -> str:
        """Call OpenAI API."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            self.last_call_failed = False
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            self.last_call_failed = True
            return self._demo_generate(system_prompt, user_prompt)

    def _demo_generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response in demo mode using template-based responses."""
        if "expand" in system_prompt.lower() or "query analyst" in system_prompt.lower():
            return self._demo_query_expansion(user_prompt)
        elif "synthesiz" in system_prompt.lower() or "physician" in system_prompt.lower():
            return self._demo_synthesis(user_prompt)
        elif "safety" in system_prompt.lower():
            return self._demo_safety_check(user_prompt)
        elif "confidence" in system_prompt.lower() or "risk" in system_prompt.lower():
            return self._demo_confidence(user_prompt)
        return "Based on the available clinical evidence, further evaluation is recommended."

    def _demo_query_expansion(self, user_prompt: str) -> str:
        return json.dumps({
            "expanded_query": user_prompt,
            "medical_concepts": ["clinical assessment", "evidence-based treatment", "patient management"],
            "query_type": "clinical_management",
            "urgency": "routine"
        })

    def _demo_synthesis(self, user_prompt: str) -> str:
        return (
            "Based on the retrieved clinical evidence:\n\n"
            "**Clinical Assessment:**\n"
            "The available evidence supports a structured approach to this clinical question.\n\n"
            "**Recommendations:**\n"
            "1. Follow established clinical guidelines for management\n"
            "2. Consider patient-specific factors including comorbidities\n"
            "3. Monitor response to treatment and adjust as needed\n\n"
            "**Evidence Sources:**\n"
            "Recommendations are based on current clinical guidelines and peer-reviewed evidence."
        )

    def _demo_safety_check(self, user_prompt: str) -> str:
        return json.dumps({
            "safety_issues": [],
            "grounding_score": 0.92,
            "numeric_validation": "passed",
            "dangerous_content": False,
            "validated_response": True
        })

    def _demo_confidence(self, user_prompt: str) -> str:
        return json.dumps({
            "confidence_score": 0.88,
            "risk_level": "low",
            "reasoning": "Response is well-grounded in retrieved evidence with consistent numeric data."
        })
