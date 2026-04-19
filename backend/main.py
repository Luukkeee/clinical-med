import os
import sys
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import config
from backend.models import QueryRequest, QueryResponse, AnalyticsResponse, HealthResponse
from utils.vector_store import FAISSVectorStore
from utils.llm import LLMClient
from agents.pipeline import ClinicalPipeline
from tools.web_search import WebSearchTool

# Global state
pipeline = None
vector_store = None


def init_system():
    """Initialize the MedRAG system."""
    global pipeline, vector_store

    print("=" * 60)
    print("  MedRAG — Clinical Decision Support System")
    print("=" * 60)

    mode = "demo" if config.is_demo_mode() else "full"
    print(f"Mode: {mode}")

    # Initialize LLM client
    llm_client = LLMClient(
        api_key=config.OPENAI_API_KEY,
        model=config.LLM_MODEL,
        mode=mode
    )

    # Initialize vector store
    vector_store = FAISSVectorStore(
        store_path=config.VECTOR_STORE_PATH,
        embedding_model=config.EMBEDDING_MODEL,
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP
    )

    # Build vector store if not exists
    if not vector_store.is_built():
        print("Building vector store from clinical documents...")
        documents = load_clinical_documents()
        if documents:
            vector_store.build_from_documents(documents)
        else:
            print("WARNING: No clinical documents found!")
    else:
        vector_store.load()

    # Initialize web search tool (always enabled — PubMed is free)
    web_search = WebSearchTool(enabled=True)

    # Initialize pipeline
    pipeline = ClinicalPipeline(
        vector_store=vector_store,
        llm_client=llm_client,
        web_search_tool=web_search
    )

    print(f"Vector store: {len(vector_store.chunks)} chunks indexed")
    print("System ready!")
    print("=" * 60)


def load_clinical_documents():
    """Load clinical documents from the documents directory."""
    docs_path = config.DOCUMENTS_PATH
    documents = []

    if not os.path.exists(docs_path):
        print(f"Documents directory not found: {docs_path}")
        return documents

    for filename in os.listdir(docs_path):
        if filename.endswith(".json"):
            filepath = os.path.join(docs_path, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    documents.extend(data)
                else:
                    documents.append(data)
                print(f"Loaded: {filename} ({len(data) if isinstance(data, list) else 1} documents)")
            except Exception as e:
                print(f"Error loading {filename}: {e}")

    return documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    init_system()
    yield


app = FastAPI(
    title="MedRAG — Clinical Decision Support API",
    description="Multi-agent clinical AI system with anti-hallucination pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a clinical query through the 6-agent pipeline."""
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: pipeline.process_query(
            query=request.query,
            enable_web_search=request.enable_web_search
        )
    )
    return result


@app.get("/api/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    """Get pipeline analytics and performance data."""
    return pipeline.get_analytics()


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """System health check."""
    return {
        "status": "healthy",
        "mode": "demo" if config.is_demo_mode() else "full",
        "vector_store_ready": vector_store.is_built() if vector_store else False,
        "total_chunks": len(vector_store.chunks) if vector_store else 0,
        "documents_loaded": len(set(c.get("document", "") for c in vector_store.chunks)) if vector_store else 0
    }


@app.post("/api/webscrape")
async def webscrape(request: QueryRequest):
    """Scrape PubMed for a clinical query and return synthesized results."""
    import asyncio
    from tools.web_search import WebSearchTool

    loop = asyncio.get_event_loop()
    scraper = WebSearchTool(enabled=True)

    # Run synchronous scraping in a thread so it doesn't block the event loop
    raw = await loop.run_in_executor(
        None, lambda: scraper.search_and_scrape(request.query, max_results=8)
    )

    # Run scraped articles through the pipeline for synthesis if we have results
    synthesized = None
    if raw["results"] and pipeline:
        # Pass already-scraped articles into the pipeline to avoid re-fetching
        synthesized = await loop.run_in_executor(
            None, lambda: pipeline.process_query(
                query=request.query,
                enable_web_search=True,
                pre_fetched_web_results=raw["results"]
            )
        )

    return {
        "scrape_results": raw,
        "synthesized_response": synthesized,
    }


@app.get("/api/sample-queries")
async def get_sample_queries():
    """Return sample clinical queries for the UI."""
    return {
        "queries": [
            "What is the first-line treatment for Stage 2 hypertension?",
            "How do you manage acute STEMI with door-to-balloon time?",
            "What are the diagnostic criteria for Type 2 Diabetes?",
            "Describe the management of acute anaphylaxis.",
            "What is the hour-1 bundle for sepsis management?",
            "How do you manage atrial fibrillation with anticoagulation?",
            "What are the KDIGO staging criteria for acute kidney injury?",
            "Describe the stepwise treatment approach for asthma.",
            "What medications are contraindicated in pregnancy?",
            "How do you manage severe hyperkalemia with ECG changes?",
        ]
    }


# Serve frontend static files if they exist
frontend_build = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "out")
if os.path.exists(frontend_build):
    app.mount("/", StaticFiles(directory=frontend_build, html=True), name="frontend")
