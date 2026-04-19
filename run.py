"""
MedRAG — Main Run Script
Usage:
  python run.py                  # Start backend server
  python run.py --build-index    # Build FAISS index from documents
  python run.py --demo           # Run a demo query
  python run.py --eval           # Run evaluation
"""
import os
import sys
import json
import argparse

# Set project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


def build_index():
    """Build the FAISS vector store from clinical documents."""
    from backend.config import config
    from utils.vector_store import FAISSVectorStore

    print("Building FAISS index from clinical documents...")

    # Load documents
    docs_path = config.DOCUMENTS_PATH
    documents = []
    for filename in os.listdir(docs_path):
        if filename.endswith(".json"):
            filepath = os.path.join(docs_path, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                documents.extend(data)
            else:
                documents.append(data)
            print(f"  Loaded: {filename}")

    if not documents:
        print("No documents found!")
        return

    # Build vector store
    vector_store = FAISSVectorStore(
        store_path=config.VECTOR_STORE_PATH,
        embedding_model=config.EMBEDDING_MODEL,
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP
    )

    num_chunks = vector_store.build_from_documents(documents)
    print(f"Index built with {num_chunks} chunks.")


def run_demo():
    """Run a demo query through the pipeline."""
    from backend.config import config
    from utils.vector_store import FAISSVectorStore
    from utils.llm import LLMClient
    from agents.pipeline import ClinicalPipeline

    print("\n" + "=" * 60)
    print("  MedRAG Demo")
    print("=" * 60)

    # Initialize
    mode = "demo" if config.is_demo_mode() else "full"
    llm = LLMClient(api_key=config.OPENAI_API_KEY, model=config.LLM_MODEL, mode=mode)

    vs = FAISSVectorStore(store_path=config.VECTOR_STORE_PATH, embedding_model=config.EMBEDDING_MODEL)
    if not vs.is_built():
        print("Vector store not built. Building now...")
        build_index()
        vs = FAISSVectorStore(store_path=config.VECTOR_STORE_PATH, embedding_model=config.EMBEDDING_MODEL)

    vs.load()
    pipeline = ClinicalPipeline(vector_store=vs, llm_client=llm)

    # Demo queries
    demo_queries = [
        "What is the first-line treatment for Stage 2 hypertension?",
        "How do you manage acute anaphylaxis?",
        "What are the diagnostic criteria for Type 2 Diabetes?",
    ]

    for query in demo_queries:
        print(f"\n{'─' * 60}")
        print(f"Query: {query}")
        print(f"{'─' * 60}")

        result = pipeline.process_query(query)

        print(f"\nResponse:")
        print(result["response"][:500])
        print(f"\nConfidence: {result['confidence_score']:.0%}")
        print(f"Risk Level: {result['risk_level']}")
        print(f"Evidence Used: {result['retrieval_stats']['evidence_used']}")
        print(f"Time: {result['performance']['total_time_seconds']:.2f}s")
        print(f"Safety Passed: {result['safety_report'].get('safety_passed', 'N/A')}")

    print(f"\n{'=' * 60}")
    print("Demo complete!")


def start_server():
    """Start the FastAPI backend server."""
    import uvicorn
    from backend.config import config

    print("Starting MedRAG backend server...")
    print(f"API: http://localhost:{config.BACKEND_PORT}")
    print(f"Docs: http://localhost:{config.BACKEND_PORT}/docs")
    print(f"Frontend: http://localhost:3000 (run 'cd frontend && npm run dev' separately)")

    uvicorn.run(
        "backend.main:app",
        host=config.BACKEND_HOST,
        port=config.BACKEND_PORT,
        reload=False,
        log_level="info"
    )


def run_eval():
    """Run the evaluation script."""
    from eval.eval import run_evaluation
    run_evaluation(mode="quick", max_questions=20)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MedRAG — Clinical Decision Support System")
    parser.add_argument("--build-index", action="store_true", help="Build FAISS index from documents")
    parser.add_argument("--demo", action="store_true", help="Run demo queries")
    parser.add_argument("--eval", action="store_true", help="Run evaluation")
    parser.add_argument("--port", type=int, default=None, help="Override server port")
    args = parser.parse_args()

    if args.port:
        os.environ["BACKEND_PORT"] = str(args.port)

    if args.build_index:
        build_index()
    elif args.demo:
        run_demo()
    elif args.eval:
        run_eval()
    else:
        start_server()
