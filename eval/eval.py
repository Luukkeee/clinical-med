"""
MedRAG Evaluation Script
Run: python eval.py --mode full
"""
import os
import sys
import json
import argparse
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.metrics import compute_all_metrics, print_metrics_report


def load_datasets(datasets_path: str):
    """Load all evaluation datasets."""
    all_questions = []
    dataset_files = ["medqa_sample.json", "pubmed_qa_sample.json", "bioasq_sample.json"]

    for filename in dataset_files:
        filepath = os.path.join(datasets_path, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_questions.extend(data)
                print(f"Loaded {len(data)} questions from {filename}")
        else:
            print(f"Warning: {filename} not found")

    return all_questions


def run_evaluation(mode: str = "full", max_questions: int = None, dataset: str = "all"):
    """Run the evaluation pipeline."""
    print("\n" + "=" * 60)
    print("  MedRAG Evaluation")
    print("=" * 60)

    # Initialize the system
    from backend.config import config
    from utils.vector_store import FAISSVectorStore
    from utils.llm import LLMClient
    from agents.pipeline import ClinicalPipeline

    llm_mode = "demo" if config.is_demo_mode() else "full"
    print(f"LLM Mode: {llm_mode}")

    llm_client = LLMClient(
        api_key=config.OPENAI_API_KEY,
        model=config.LLM_MODEL,
        mode=llm_mode
    )

    vector_store = FAISSVectorStore(
        store_path=config.VECTOR_STORE_PATH,
        embedding_model=config.EMBEDDING_MODEL
    )

    if not vector_store.is_built():
        print("Vector store not built. Run the backend first to build it.")
        print("Or run: python run.py --build-index")
        return

    vector_store.load()
    pipeline = ClinicalPipeline(vector_store=vector_store, llm_client=llm_client)

    # Load datasets
    datasets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")
    questions = load_datasets(datasets_path)

    if not questions:
        print("No evaluation questions found!")
        return

    # Filter by dataset if specified
    if dataset != "all":
        dataset_map = {
            "medqa": range(1, 71),
            "pubmed": range(71, 141),
            "bioasq": range(141, 216)
        }
        if dataset in dataset_map:
            valid_ids = set(dataset_map[dataset])
            questions = [q for q in questions if q["id"] in valid_ids]

    if max_questions:
        questions = questions[:max_questions]

    print(f"Evaluating {len(questions)} questions...")
    print("-" * 60)

    responses = []
    start_time = time.time()

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['question'][:70]}...", end=" ", flush=True)

        try:
            result = pipeline.process_query(q["question"])
            responses.append(result)
            conf = result.get("confidence_score", 0)
            risk = result.get("risk_level", "?")
            t = result.get("performance", {}).get("total_time_seconds", 0)
            print(f"✓ conf={conf:.0%} risk={risk} t={t:.1f}s")
        except Exception as e:
            print(f"✗ Error: {e}")
            responses.append({
                "response": "",
                "confidence_score": 0,
                "risk_level": "unknown",
                "safety_report": {},
                "performance": {"total_time_seconds": 0}
            })

    total_time = time.time() - start_time

    # Compute metrics
    metrics = compute_all_metrics(responses, questions)
    metrics["total_eval_time"] = round(total_time, 2)

    # Print report
    print_metrics_report(metrics)

    # Breakdown by category
    print("\n  Category Breakdown:")
    categories = {}
    for resp, q in zip(responses, questions):
        cat = q.get("category", "Unknown")
        if cat not in categories:
            categories[cat] = {"responses": [], "questions": []}
        categories[cat]["responses"].append(resp)
        categories[cat]["questions"].append(q)

    for cat, data in sorted(categories.items()):
        cat_metrics = compute_all_metrics(data["responses"], data["questions"])
        print(f"  {cat:25s} | n={cat_metrics['total_evaluated']:3d} | "
              f"halluc={cat_metrics['hallucination_rate']:.0%} | "
              f"complete={cat_metrics['answer_completeness']:.0%} | "
              f"conf={cat_metrics['avg_confidence']:.0%}")

    # Save results
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": metrics,
            "category_breakdown": {
                cat: compute_all_metrics(data["responses"], data["questions"])
                for cat, data in categories.items()
            },
            "config": {
                "mode": llm_mode,
                "model": config.LLM_MODEL,
                "total_questions": len(questions),
                "total_time": total_time
            }
        }, f, indent=2)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MedRAG Evaluation")
    parser.add_argument("--mode", choices=["full", "quick"], default="full",
                        help="Evaluation mode (full=all questions, quick=subset)")
    parser.add_argument("--max", type=int, default=None,
                        help="Maximum number of questions to evaluate")
    parser.add_argument("--dataset", choices=["all", "medqa", "pubmed", "bioasq"],
                        default="all", help="Which dataset to evaluate")
    args = parser.parse_args()

    max_q = args.max or (20 if args.mode == "quick" else None)
    run_evaluation(mode=args.mode, max_questions=max_q, dataset=args.dataset)
