import re
from typing import List, Dict, Any


def compute_hallucination_rate(responses: List[Dict[str, Any]]) -> float:
    """Compute hallucination rate based on grounding scores."""
    if not responses:
        return 0.0
    hallucinated = sum(
        1 for r in responses
        if r.get("safety_report", {}).get("grounding_score", 1.0) < 0.7
    )
    return round(hallucinated / len(responses), 4)


def compute_numeric_accuracy(responses: List[Dict[str, Any]],
                             ground_truth: List[Dict[str, Any]]) -> float:
    """Compute numeric accuracy by checking key numeric values."""
    if not responses or not ground_truth:
        return 0.0

    correct = 0
    total = 0

    for resp, gt in zip(responses, ground_truth):
        key_facts = gt.get("key_facts", [])
        response_text = resp.get("response", "").lower()

        # Extract numeric facts
        numeric_facts = [f for f in key_facts if any(c.isdigit() for c in f)]
        if not numeric_facts:
            continue

        total += len(numeric_facts)
        for fact in numeric_facts:
            fact_lower = fact.lower()
            # Check if the numeric fact appears in the response
            if fact_lower in response_text:
                correct += 1
            else:
                # Check if key numbers from the fact appear
                numbers = re.findall(r'\d+\.?\d*', fact)
                if numbers and any(n in response_text for n in numbers):
                    correct += 0.5

    return round(correct / total if total > 0 else 0.0, 4)


def compute_answer_completeness(responses: List[Dict[str, Any]],
                                ground_truth: List[Dict[str, Any]]) -> float:
    """Compute how completely the response covers expected key facts."""
    if not responses or not ground_truth:
        return 0.0

    scores = []
    for resp, gt in zip(responses, ground_truth):
        key_facts = gt.get("key_facts", [])
        if not key_facts:
            continue

        response_text = resp.get("response", "").lower()
        covered = sum(1 for fact in key_facts if fact.lower() in response_text)
        scores.append(covered / len(key_facts))

    return round(sum(scores) / len(scores) if scores else 0.0, 4)


def compute_dangerous_error_rate(responses: List[Dict[str, Any]]) -> float:
    """Compute rate of dangerous errors caught by safety pipeline."""
    if not responses:
        return 0.0
    total_with_danger = sum(
        1 for r in responses
        if r.get("safety_report", {}).get("danger_flags")
    )
    return round(total_with_danger / len(responses), 4)


def compute_avg_confidence(responses: List[Dict[str, Any]]) -> float:
    """Compute average confidence score."""
    if not responses:
        return 0.0
    scores = [r.get("confidence_score", 0) for r in responses]
    return round(sum(scores) / len(scores), 4)


def compute_avg_response_time(responses: List[Dict[str, Any]]) -> float:
    """Compute average response time."""
    if not responses:
        return 0.0
    times = [r.get("performance", {}).get("total_time_seconds", 0) for r in responses]
    return round(sum(times) / len(times), 4)


def compute_all_metrics(responses: List[Dict[str, Any]],
                        ground_truth: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute all evaluation metrics."""
    return {
        "hallucination_rate": compute_hallucination_rate(responses),
        "numeric_accuracy": compute_numeric_accuracy(responses, ground_truth),
        "answer_completeness": compute_answer_completeness(responses, ground_truth),
        "dangerous_error_rate": compute_dangerous_error_rate(responses),
        "avg_confidence": compute_avg_confidence(responses),
        "avg_response_time": compute_avg_response_time(responses),
        "total_evaluated": len(responses),
    }


def print_metrics_report(metrics: Dict[str, Any]):
    """Print a formatted metrics report."""
    print("\n" + "=" * 60)
    print("  MedRAG Evaluation Report")
    print("=" * 60)
    print(f"  Total Questions Evaluated: {metrics['total_evaluated']}")
    print(f"  Hallucination Rate:        {metrics['hallucination_rate']:.1%}")
    print(f"  Numeric Accuracy:          {metrics['numeric_accuracy']:.1%}")
    print(f"  Answer Completeness:       {metrics['answer_completeness']:.1%}")
    print(f"  Dangerous Error Rate:      {metrics['dangerous_error_rate']:.1%}")
    print(f"  Average Confidence:        {metrics['avg_confidence']:.1%}")
    print(f"  Avg Response Time:         {metrics['avg_response_time']:.3f}s")
    print("=" * 60)
