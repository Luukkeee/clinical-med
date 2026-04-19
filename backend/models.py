from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000, description="Clinical query")
    enable_web_search: bool = Field(default=False, description="Enable web search for latest info")


class Citation(BaseModel):
    source: str
    section: str
    category: str
    relevance_score: float


class SafetyReport(BaseModel):
    grounding_score: float = 0.0
    grounded_sentences: int = 0
    total_sentences: int = 0
    ungrounded_sentences: List[str] = []
    numeric_validation: str = "passed"
    numeric_mismatches: List[Dict[str, Any]] = []
    numeric_verified: int = 0
    dangerous_content: bool = False
    danger_flags: List[str] = []
    safety_passed: bool = True


class QueryAnalysis(BaseModel):
    expanded_query: str = ""
    medical_concepts: List[str] = []
    query_type: str = ""
    urgency: str = "routine"


class RetrievalStats(BaseModel):
    total_retrieved: int = 0
    evidence_used: int = 0


class AgentTiming(BaseModel):
    agent: str
    time_seconds: float


class PerformanceStats(BaseModel):
    total_time_seconds: float = 0.0
    agent_timings: List[AgentTiming] = []


class QueryResponse(BaseModel):
    query: str
    response: str
    confidence_score: float
    risk_level: str
    citations: List[Citation] = []
    safety_report: SafetyReport = SafetyReport()
    confidence_reasoning: str = ""
    query_analysis: QueryAnalysis = QueryAnalysis()
    retrieval_stats: RetrievalStats = RetrievalStats()
    performance: PerformanceStats = PerformanceStats()


class AnalyticsResponse(BaseModel):
    total_queries: int
    avg_confidence: float
    risk_distribution: Dict[str, int]
    avg_response_time: float
    queries: List[Dict[str, Any]] = []


class HealthResponse(BaseModel):
    status: str
    mode: str
    vector_store_ready: bool
    total_chunks: int
    documents_loaded: int
