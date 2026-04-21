import asyncio
import json
import os
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.runner import BenchmarkRunner, save_reports, auto_release_gate
from engine.metrics import MetricsCalculator
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge
from agent.main_agent import MainAgent
from agent.vector_store import build_vector_store_from_dataset
from data.synthetic_gen import generate_synthetic_dataset


def load_dataset(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]
    return dataset if dataset else None


async def run_benchmark_for_version(
    agent_version: str,
    dataset: list,
    agent: MainAgent,
    judge: LLMJudge,
    evaluator: MetricsCalculator,
    max_concurrency: int = 10,
) -> tuple:
    print(f"\n{'='*60}")
    print(f"  BENCHMARK RUN - {agent_version}")
    print(f"{'='*60}")

    vs = build_vector_store_from_dataset(dataset)
    agent.set_vector_store(vs)

    runner = BenchmarkRunner(agent, evaluator, judge, max_concurrency=max_concurrency)

    results = await runner.run_all(dataset, batch_size=10)
    total = len(results)

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = total - passed

    avg_score = sum(r["judge"]["final_score"] for r in results) / total
    avg_faithfulness = sum(r["ragas"]["faithfulness"] for r in results) / total
    avg_relevancy = sum(r["ragas"]["relevancy"] for r in results) / total

    hit_rates = [r["ragas"]["retrieval"].get("hit_rate", 0) for r in results]
    mrr_scores = [r["ragas"]["retrieval"].get("mrr", 0) for r in results]
    agreements = [r["judge"]["agreement_rate"] for r in results]
    kappas = [r["judge"].get("cohens_kappa", 0) for r in results]
    ndcgs = [r["ragas"]["retrieval"].get("ndcg", 0) for r in results]
    ctx_precisions = [r["ragas"]["retrieval"].get("context_precision", 0) for r in results]
    ctx_recalls = [r["ragas"]["retrieval"].get("context_recall", 0) for r in results]
    latencies = [r["latency"] for r in results]

    avg_hit_rate = sum(hit_rates) / len(hit_rates) if hit_rates else 0
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0
    avg_agreement = sum(agreements) / len(agreements) if agreements else 0
    avg_kappa = sum(kappas) / len(kappas) if kappas else 0
    avg_ndcg = sum(ndcgs) / len(ndcgs) if ndcgs else 0
    avg_ctx_precision = sum(ctx_precisions) / len(ctx_precisions) if ctx_precisions else 0
    avg_ctx_recall = sum(ctx_recalls) / len(ctx_recalls) if ctx_recalls else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    cost_report = runner.get_cost_report(total)

    summary = {
        "metadata": {
            "version": agent_version,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total, 4) if total > 0 else 0,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_size": len(dataset),
            "max_concurrency": max_concurrency,
        },
        "metrics": {
            "avg_score": round(avg_score, 4),
            "avg_faithfulness": round(avg_faithfulness, 4),
            "avg_relevancy": round(avg_relevancy, 4),
            "hit_rate": round(avg_hit_rate, 4),
            "mrr": round(avg_mrr, 4),
            "ndcg": round(avg_ndcg, 4),
            "agreement_rate": round(avg_agreement, 4),
            "cohens_kappa": round(avg_kappa, 4),
            "context_precision": round(avg_ctx_precision, 4),
            "context_recall": round(avg_ctx_recall, 4),
            "avg_latency_ms": round(avg_latency * 1000, 2),
        },
        "cost_report": cost_report,
    }

    print(f"\n  --- RESULTS ---")
    print(f"  Total cases:    {total}")
    print(f"  Passed:         {passed} ({passed/total*100:.1f}%)")
    print(f"  Failed:         {failed}")
    print(f"  Avg Score:      {avg_score:.2f} / 5.0")
    print(f"  Avg Faithful.:   {avg_faithfulness:.4f}")
    print(f"  Avg Relevancy:  {avg_relevancy:.4f}")
    print(f"  Hit Rate:       {avg_hit_rate:.4f}")
    print(f"  MRR:            {avg_mrr:.4f}")
    print(f"  NDCG@5:         {avg_ndcg:.4f}")
    print(f"  Agreement Rate:  {avg_agreement:.4f}")
    print(f"  Cohen's Kappa:   {avg_kappa:.4f}")
    print(f"  Context Prec.:  {avg_ctx_precision:.4f}")
    print(f"  Context Recall: {avg_ctx_recall:.4f}")
    print(f"  Avg Latency:    {avg_latency*1000:.0f}ms")
    print(f"  Total Cost:     ${cost_report['total_cost']:.4f}")
    print(f"  Total Tokens:   {cost_report['total_tokens']}")

    return results, summary


def print_regression_comparison(v1_summary: dict, v2_summary: dict, gate: dict):
    print(f"\n{'='*60}")
    print(f"  REGRESSION COMPARISON: V1 vs V2")
    print(f"{'='*60}")
    print(f"  {'Metric':<25} {'V1':>10} {'V2':>10} {'Delta':>10}")
    print(f"  {'-'*55}")
    print(f"  {'Avg Score':<25} {v1_summary['metrics']['avg_score']:>10.4f} {v2_summary['metrics']['avg_score']:>10.4f} {gate['delta_score']:>+10.4f}")
    print(f"  {'Hit Rate':<25} {v1_summary['metrics']['hit_rate']:>10.4f} {v2_summary['metrics']['hit_rate']:>10.4f} {gate['delta_hit_rate']:>+10.4f}")
    print(f"  {'MRR':<25} {v1_summary['metrics']['mrr']:>10.4f} {v2_summary['metrics']['mrr']:>10.4f} {v2_summary['metrics']['mrr'] - v1_summary['metrics']['mrr']:>+10.4f}")
    print(f"  {'NDCG@5':<25} {v1_summary['metrics']['ndcg']:>10.4f} {v2_summary['metrics']['ndcg']:>10.4f} {v2_summary['metrics']['ndcg'] - v1_summary['metrics']['ndcg']:>+10.4f}")
    print(f"  {'Agreement Rate':<25} {v1_summary['metrics']['agreement_rate']:>10.4f} {v2_summary['metrics']['agreement_rate']:>10.4f} {v2_summary['metrics']['agreement_rate'] - v1_summary['metrics']['agreement_rate']:>+10.4f}")
    kappa_label = "Cohen's Kappa"
    print(f"  {kappa_label:<25} {v1_summary['metrics']['cohens_kappa']:>10.4f} {v2_summary['metrics']['cohens_kappa']:>10.4f} {v2_summary['metrics']['cohens_kappa'] - v1_summary['metrics']['cohens_kappa']:>+10.4f}")
    print(f"  {'Faithfulness':<25} {v1_summary['metrics']['avg_faithfulness']:>10.4f} {v2_summary['metrics']['avg_faithfulness']:>10.4f} {v2_summary['metrics']['avg_faithfulness'] - v1_summary['metrics']['avg_faithfulness']:>+10.4f}")
    print(f"  {'Relevancy':<25} {v1_summary['metrics']['avg_relevancy']:>10.4f} {v2_summary['metrics']['avg_relevancy']:>10.4f} {v2_summary['metrics']['avg_relevancy'] - v1_summary['metrics']['avg_relevancy']:>+10.4f}")
    print(f"  {'Context Precision':<25} {v1_summary['metrics']['context_precision']:>10.4f} {v2_summary['metrics']['context_precision']:>10.4f} {v2_summary['metrics']['context_precision'] - v1_summary['metrics']['context_precision']:>+10.4f}")
    print(f"  {'Context Recall':<25} {v1_summary['metrics']['context_recall']:>10.4f} {v2_summary['metrics']['context_recall']:>10.4f} {v2_summary['metrics']['context_recall'] - v1_summary['metrics']['context_recall']:>+10.4f}")
    print(f"  {'Avg Latency (ms)':<25} {v1_summary['metrics']['avg_latency_ms']:>10.2f} {v2_summary['metrics']['avg_latency_ms']:>10.2f} {v2_summary['metrics']['avg_latency_ms'] - v1_summary['metrics']['avg_latency_ms']:>+10.2f}")
    print(f"\n  {'='*60}")
    print(f"  GATE DECISION: {gate['decision']}")
    print(f"  {gate['message']}")
    print(f"{'='*60}")


async def main():
    print("\n" + "="*60)
    print("  AI EVALUATION FACTORY - BENCHMARK RUNNER")
    print("="*60)

    dataset = load_dataset("data/golden_set.jsonl")
    if not dataset:
        print("\n  [STEP 1] Golden dataset not found. Generating...")
        dataset = await generate_synthetic_dataset()
        print(f"  [STEP 2] Generated {len(dataset)} cases. Proceeding with benchmark.\n")
    else:
        print(f"\n  [STEP 1] Loaded {len(dataset)} cases from data/golden_set.jsonl\n")

    judge = LLMJudge()
    evaluator = MetricsCalculator()

    MAX_CONCURRENCY = 10

    v1_agent = MainAgent(model="gpt-4o", agent_version="v1")
    v2_agent = MainAgent(model="gpt-4o", agent_version="v2")

    print(f"\n  [STEP 2] Running V1 (Dense Vector Search - Baseline) benchmark...")
    v1_results, v1_summary = await run_benchmark_for_version(
        "Agent_V1_DenseOnly", dataset, v1_agent, judge, evaluator,
        max_concurrency=MAX_CONCURRENCY
    )

    print(f"\n  [STEP 3] Running V2 (Hybrid + Reranking - Optimized) benchmark...")
    v2_results, v2_summary = await run_benchmark_for_version(
        "Agent_V2_HybridRerank", dataset, v2_agent, judge, evaluator,
        max_concurrency=MAX_CONCURRENCY
    )

    gate = auto_release_gate(v1_summary, v2_summary)

    print_regression_comparison(v1_summary, v2_summary, gate)

    os.makedirs("reports", exist_ok=True)
    save_reports(v1_summary, v2_summary, v1_results, v2_results, gate, "reports")

    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "v1_summary": v1_summary,
                "v2_summary": v2_summary,
                "gate_decision": gate,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(
            {"v1_results": v1_results, "v2_results": v2_results},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n  [STEP 4] Reports saved to reports/")
    print(f"  [STEP 5] Benchmark complete!")

    return v1_summary, v2_summary, gate


if __name__ == "__main__":
    asyncio.run(main())
