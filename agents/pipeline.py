import time
from typing import Dict, Any, Optional
from .clinical_query_analyst import ClinicalQueryAnalyst
from .medical_retriever import MedicalRetriever
from .evidence_appraiser import EvidenceAppraiser
from .physician_synthesizer import PhysicianSynthesizer
from .patient_safety_officer import PatientSafetyOfficer
from .confidence_risk_agent import ConfidenceRiskAgent


class ClinicalPipeline:
    """
    6-Agent Clinical Safety Pipeline.
    Chains agents sequentially for safe, grounded clinical responses.
    """

    def __init__(self, vector_store=None, llm_client=None, web_search_tool=None):
        self.agents = [
            ClinicalQueryAnalyst(llm_client=llm_client),
            MedicalRetriever(vector_store=vector_store, web_search_tool=web_search_tool),
            EvidenceAppraiser(),
            PhysicianSynthesizer(llm_client=llm_client),
            PatientSafetyOfficer(llm_client=llm_client),
            ConfidenceRiskAgent(llm_client=llm_client),
        ]
        self.query_history = []

    def process_query(self, query: str, enable_web_search: bool = False,
                       pre_fetched_web_results: list = None) -> Dict[str, Any]:
        """Process a clinical query through the full 6-agent pipeline."""
        start_time = time.time()

        context = {
            "query": query,
            "enable_web_search": enable_web_search,
            "pipeline_start": start_time,
        }
        if pre_fetched_web_results:
            context["pre_fetched_web_results"] = pre_fetched_web_results

        agent_timings = []
        all_logs = []

        for agent in self.agents:
            agent.clear_logs()
            agent_start = time.time()

            try:
                context = agent.process(context)
            except Exception as e:
                context[f"error_{agent.name}"] = str(e)
                agent.log(f"ERROR: {e}")

            agent_time = time.time() - agent_start
            agent_timings.append({
                "agent": agent.name,
                "time_seconds": round(agent_time, 3)
            })
            all_logs.extend(agent.get_logs())

            # Short-circuit: if the query was rejected as non-clinical, stop
            if context.get("rejected"):
                break

        total_time = time.time() - start_time

        result = {
            "query": query,
            "response": context.get("response", "Unable to generate response."),
            "confidence_score": context.get("confidence_score", 0.0),
            "risk_level": context.get("risk_level", "unknown"),
            "citations": context.get("citations", []),
            "safety_report": context.get("safety_report", {}),
            "confidence_reasoning": context.get("confidence_reasoning", ""),
            "query_analysis": {
                "expanded_query": context.get("expanded_query", query),
                "medical_concepts": context.get("medical_concepts", []),
                "query_type": context.get("query_type", ""),
                "urgency": context.get("urgency", "routine"),
            },
            "retrieval_stats": {
                "total_retrieved": context.get("retrieval_count", 0),
                "evidence_used": context.get("evidence_count", 0),
            },
            "performance": {
                "total_time_seconds": round(total_time, 3),
                "agent_timings": agent_timings,
            },
            "pipeline_logs": all_logs,
        }

        self.query_history.append({
            "query": query,
            "confidence": result["confidence_score"],
            "risk_level": result["risk_level"],
            "time": total_time,
            "timestamp": start_time
        })

        return result

    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics data from pipeline history."""
        if not self.query_history:
            return {
                "total_queries": 0,
                "avg_confidence": 0,
                "risk_distribution": {},
                "avg_response_time": 0,
                "queries": []
            }

        confidences = [q["confidence"] for q in self.query_history]
        risk_counts = {}
        for q in self.query_history:
            risk = q["risk_level"]
            risk_counts[risk] = risk_counts.get(risk, 0) + 1

        return {
            "total_queries": len(self.query_history),
            "avg_confidence": round(sum(confidences) / len(confidences), 2),
            "risk_distribution": risk_counts,
            "avg_response_time": round(
                sum(q["time"] for q in self.query_history) / len(self.query_history), 3
            ),
            "queries": self.query_history[-20:]  # Last 20 queries
        }
