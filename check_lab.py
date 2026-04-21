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

    # 1. Kiểm tra sự tồn tại của tất cả file
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

    # 2. Kiểm tra nội dung summary.json
    try:
        with open("reports/summary.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[FAIL] File reports/summary.json is not valid JSON: {e}")
        return

    v2_data = data.get("v2_summary", data)
    if "metrics" not in v2_data or "metadata" not in v2_data:
        print("[FAIL] File summary.json missing 'metrics' or 'metadata' field in v2_summary.")
        return

    metrics = v2_data["metrics"]

    print(f"\n--- Quick Stats ---")
    print(f"Total cases: {v2_data['metadata'].get('total', 'N/A')}")

    avg_score = metrics.get("avg_score", 0)
    print(f"Avg Score: {avg_score:.2f} / 5.0")

    # EXPERT CHECKS
    has_retrieval = "hit_rate" in metrics
    if has_retrieval:
        print(f"[OK] Retrieval Metrics found (Hit Rate: {metrics['hit_rate']*100:.1f}%)")
    else:
        print(f"[WARN] Missing Retrieval Metrics (hit_rate).")

    has_multi_judge = "agreement_rate" in metrics
    if has_multi_judge:
        print(f"[OK] Multi-Judge Metrics found (Agreement Rate: {metrics['agreement_rate']*100:.1f}%)")
    else:
        print(f"[WARN] Missing Multi-Judge Metrics (agreement_rate).")

    if v2_data.get("metadata", {}).get("version"):
        print(f"[OK] Agent version info found (Regression Mode)")

    if "gate_decision" in data:
        gate = data["gate_decision"]
        print(f"\n--- Regression Gate ---")
        print(f"Decision: {gate.get('decision', 'N/A')}")
        print(f"Delta Score: {gate.get('delta_score', 0):+.4f}")

    print("\n[SUCCESS] Lab is ready for grading!")

if __name__ == "__main__":
    validate_lab()
