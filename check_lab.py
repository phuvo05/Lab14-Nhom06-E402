import json
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def validate_lab():
    print("[CHECK] Validating lab submission format...")

    required_files = [
        "reports/summary.json",
        "reports/benchmark_results.json",
        "analysis/failure_analysis.md"
    ]

    missing = []
    for f in required_files:
        if os.path.exists(f):
            print(f"[OK] Found: {f}")
        else:
            print(f"[FAIL] Missing: {f}")
            missing.append(f)

    if missing:
        print(f"\n[FAIL] Missing {len(missing)} file(s). Please add them before submitting.")
        return

    try:
        with open("reports/summary.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[FAIL] File reports/summary.json is not valid JSON: {e}")
        return

    v1_data = data.get("v1_summary", {})
    v2_data = data.get("v2_summary", data)

    if "metrics" not in v2_data or "metadata" not in v2_data:
        print("[FAIL] File summary.json missing 'metrics' or 'metadata' field in v2_summary.")
        return

    metrics = v2_data["metrics"]
    v1_metrics = v1_data.get("metrics", {})

    print(f"\n--- Quick Stats ---")
    print(f"Total cases: {v2_data['metadata'].get('total', 'N/A')}")
    print(f"Dataset size: {v2_data['metadata'].get('dataset_size', 'N/A')}")

    avg_score = metrics.get("avg_score", 0)
    print(f"Avg Score: {avg_score:.2f} / 5.0")

    print(f"\n--- V1 Results ---")
    print(f"  Avg Score: {v1_metrics.get('avg_score', 'N/A')}")
    print(f"  Hit Rate:  {v1_metrics.get('hit_rate', 'N/A')}")
    print(f"  MRR:       {v1_metrics.get('mrr', 'N/A')}")
    print(f"  NDCG@5:    {v1_metrics.get('ndcg', 'N/A')}")
    print(f"  Faithful.: {v1_metrics.get('avg_faithfulness', 'N/A')}")
    print(f"  Latency:   {v1_metrics.get('avg_latency_ms', 'N/A')}ms")

    print(f"\n--- V2 Results ---")
    print(f"  Avg Score:      {metrics.get('avg_score', 'N/A')}")
    print(f"  Hit Rate:       {metrics.get('hit_rate', 'N/A')}")
    print(f"  MRR:            {metrics.get('mrr', 'N/A')}")
    print(f"  NDCG@5:         {metrics.get('ndcg', 'N/A')}")
    print(f"  Faithfulness:   {metrics.get('avg_faithfulness', 'N/A')}")
    print(f"  Relevancy:      {metrics.get('avg_relevancy', 'N/A')}")
    print(f"  Agreement Rate: {metrics.get('agreement_rate', 'N/A')}")
    print(f"  Cohen's Kappa:  {metrics.get('cohens_kappa', 'N/A')}")
    print(f"  Context Prec.:  {metrics.get('context_precision', 'N/A')}")
    print(f"  Context Recall: {metrics.get('context_recall', 'N/A')}")
    print(f"  Latency:        {metrics.get('avg_latency_ms', 'N/A')}ms")

    print(f"\n--- Retrieval Evaluation ---")
    has_hit_rate = "hit_rate" in metrics
    has_mrr = "mrr" in metrics
    has_ndcg = "ndcg" in metrics
    has_ctx_prec = "context_precision" in metrics
    has_ctx_recall = "context_recall" in metrics
    if has_hit_rate:
        print(f"[OK] Hit Rate found: {metrics['hit_rate']*100:.1f}%")
    else:
        print(f"[FAIL] Hit Rate missing.")

    if has_mrr:
        print(f"[OK] MRR found: {metrics['mrr']:.4f}")
    else:
        print(f"[FAIL] MRR missing.")

    if has_ndcg:
        print(f"[OK] NDCG@5 found: {metrics['ndcg']:.4f}")
    else:
        print(f"[WARN] NDCG@5 missing (bonus metric).")

    if has_ctx_prec:
        print(f"[OK] Context Precision found: {metrics['context_precision']:.4f}")
    if has_ctx_recall:
        print(f"[OK] Context Recall found: {metrics['context_recall']:.4f}")

    print(f"\n--- Multi-Judge Evaluation ---")
    has_agreement = "agreement_rate" in metrics
    has_kappa = "cohens_kappa" in metrics
    if has_agreement:
        print(f"[OK] Agreement Rate found: {metrics['agreement_rate']*100:.1f}%")
    else:
        print(f"[FAIL] Agreement Rate missing.")

    if has_kappa:
        print(f"[OK] Cohen's Kappa found: {metrics['cohens_kappa']:.4f}")
    else:
        print(f"[WARN] Cohen's Kappa missing.")

    if v2_data.get("metadata", {}).get("version"):
        print(f"\n[OK] Agent version info found: {v2_data['metadata']['version']}")

    if "gate_decision" in data:
        gate = data["gate_decision"]
        print(f"\n--- Regression Gate ---")
        print(f"Decision: {gate.get('decision', 'N/A')}")
        print(f"Delta Score: {gate.get('delta_score', 0):+.4f}")
        print(f"Delta Hit Rate: {gate.get('delta_hit_rate', 0):+.4f}")
        print(f"Agreement Rate: {gate.get('agreement_rate', 0):.4f}")
        print(f"Thresholds used: {gate.get('thresholds', {})}")

    if v1_data and v2_data:
        delta = metrics.get("avg_score", 0) - v1_metrics.get("avg_score", 0)
        delta_hit = metrics.get("hit_rate", 0) - v1_metrics.get("hit_rate", 0)
        print(f"\n--- Regression Comparison ---")
        print(f"  V1 → V2 Score Delta: {delta:+.4f}")
        print(f"  V1 → V2 Hit Rate Delta: {delta_hit:+.4f}")
        print(f"  Expected Gate: ", end="")
        if gate.get("decision") == "APPROVE":
            print("APPROVE (improvement)")
        elif gate.get("decision") == "CONDITIONAL":
            print("CONDITIONAL (acceptable)")
        elif gate.get("decision") == "BLOCK":
            print("BLOCK (needs work)")
        else:
            print("UNKNOWN")

    score_checks = []
    if avg_score >= 4.0:
        score_checks.append("HIGH SCORE")
    elif avg_score >= 3.5:
        score_checks.append("GOOD SCORE")
    elif avg_score >= 3.0:
        score_checks.append("ACCEPTABLE")
    else:
        score_checks.append("LOW SCORE")

    print(f"\n[SUCCESS] Lab is ready for grading!")
    print(f"  Status checks passed: {len(score_checks)}")

    return True


if __name__ == "__main__":
    validate_lab()
