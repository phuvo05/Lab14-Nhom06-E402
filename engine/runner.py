import asyncio
import os
import time
import json
from typing import List, Dict, Any, Optional
from tqdm.asyncio import tqdm
from dotenv import load_dotenv

load_dotenv()


class BenchmarkRunner:
    def __init__(
        self,
        agent,
        evaluator,
        judge,
        max_concurrency: int = 10,
        request_timeout: float = 60.0,
    ):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.timeout = request_timeout
        self.total_tokens = 0
        self.total_cost = 0.0
        self.errors = 0

    async def _run_single_with_semaphore(self, test_case: Dict) -> Dict:
        async with self.semaphore:
            return await self._run_single_safe(test_case)

    async def _run_single_safe(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                self.agent.query(test_case["question"]), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            self.errors += 1
            return {
                "test_case": test_case["question"],
                "agent_response": "[TIMEOUT]",
                "latency": self.timeout,
                "ragas": {
                    "faithfulness": 0.0,
                    "relevancy": 0.0,
                    "retrieval": {
                        "hit_rate": 0.0,
                        "mrr": 0.0,
                        "ndcg": 0.0,
                        "context_precision": 0.0,
                        "context_recall": 0.0,
                    },
                },
                "judge": {
                    "final_score": 1.0,
                    "agreement_rate": 0.0,
                    "cohens_kappa": 0.0,
                    "error": "Timeout",
                },
                "status": "timeout",
            }
        except Exception as e:
            self.errors += 1
            return {
                "test_case": test_case["question"],
                "agent_response": f"[ERROR: {e}]",
                "latency": time.perf_counter() - start_time,
                "ragas": {
                    "faithfulness": 0.0,
                    "relevancy": 0.0,
                    "retrieval": {
                        "hit_rate": 0.0,
                        "mrr": 0.0,
                        "ndcg": 0.0,
                        "context_precision": 0.0,
                        "context_recall": 0.0,
                    },
                },
                "judge": {
                    "final_score": 1.0,
                    "agreement_rate": 0.0,
                    "cohens_kappa": 0.0,
                    "error": str(e),
                },
                "status": "error",
            }

        latency = time.perf_counter() - start_time

        if "usage" in response.get("metadata", {}):
            self.total_tokens += response["metadata"].get("usage", {}).get("total_tokens", 0)
        if "cost" in response.get("metadata", {}):
            self.total_cost += response["metadata"]["cost"]

        expected_ids = test_case.get("expected_retrieval_ids", [])
        retrieved_ids = response.get("retrieved_ids", [])
        contexts = response.get("contexts", [])

        ragas_task = self.evaluator.calculate_ragas_metrics(
            question=test_case["question"],
            answer=response["answer"],
            contexts=contexts,
            expected_ids=expected_ids,
            retrieved_ids=retrieved_ids,
        )
        judge_task = self.judge.evaluate_multi_judge(
            question=test_case["question"],
            answer=response["answer"],
            ground_truth=test_case["expected_answer"],
        )

        ragas_scores, judge_result = await asyncio.gather(ragas_task, judge_task)

        hit_rate = ragas_scores["retrieval"].get("hit_rate", 0.0)
        mrr = ragas_scores["retrieval"].get("mrr", 0.0)
        ctx_prec = ragas_scores["retrieval"].get("context_precision", 0.0)
        ctx_recall = ragas_scores["retrieval"].get("context_recall", 0.0)
        ndcg = self.evaluator.calculate_ndcg(expected_ids, retrieved_ids, k=5)

        ragas_scores["retrieval"]["ndcg"] = round(ndcg, 4)
        ragas_scores["retrieval"]["context_precision"] = round(ctx_prec, 4)
        ragas_scores["retrieval"]["context_recall"] = round(ctx_recall, 4)

        return {
            "test_case": test_case["question"],
            "agent_response": response["answer"],
            "contexts_used": contexts,
            "retrieved_ids": retrieved_ids,
            "latency": round(latency, 4),
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": "fail" if judge_result["final_score"] < 3 else "pass",
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 10) -> List[Dict]:
        results = []
        total_cases = len(dataset)
        max_concurrency = self.semaphore._value

        print(f"  Running benchmark on {total_cases} cases (batch_size={batch_size}, concurrency={max_concurrency})...")

        for i in range(0, total_cases, batch_size):
            batch = dataset[i:i + batch_size]
            tasks = [self._run_single_with_semaphore(case) for case in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    self.errors += 1
                    results.append({
                        "test_case": "unknown",
                        "agent_response": f"[EXCEPTION: {result}]",
                        "latency": 0,
                        "ragas": {
                            "faithfulness": 0.0,
                            "relevancy": 0.0,
                            "retrieval": {
                                "hit_rate": 0.0,
                                "mrr": 0.0,
                                "ndcg": 0.0,
                                "context_precision": 0.0,
                                "context_recall": 0.0,
                            },
                        },
                        "judge": {
                            "final_score": 1.0,
                            "agreement_rate": 0.0,
                            "cohens_kappa": 0.0,
                        },
                        "status": "exception",
                    })
                else:
                    results.append(result)

            completed = min(i + batch_size, total_cases)
            print(f"  Progress: {completed}/{total_cases} cases completed")

        return results

    def get_cost_report(self, num_cases: int) -> Dict[str, Any]:
        return {
            "total_cost": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "cost_per_eval": round(self.total_cost / num_cases, 6) if num_cases > 0 else 0,
            "tokens_per_eval": round(self.total_tokens / num_cases, 2) if num_cases > 0 else 0,
            "error_count": self.errors,
        }


def save_reports(
    v1_summary: Dict,
    v2_summary: Dict,
    v1_results: List[Dict],
    v2_results: List[Dict],
    gate_decision: Dict,
    output_dir: str = "reports",
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    report = {
        "v1_summary": v1_summary,
        "v2_summary": v2_summary,
        "gate_decision": gate_decision,
    }

    with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "benchmark_results.json"), "w", encoding="utf-8") as f:
        json.dump({"v1_results": v1_results, "v2_results": v2_results}, f, ensure_ascii=False, indent=2)

    print(f"  Reports saved to {output_dir}/")


def auto_release_gate(v1_summary: Dict, v2_summary: Dict) -> Dict[str, Any]:
    delta_score = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    delta_hit_rate = v2_summary["metrics"]["hit_rate"] - v1_summary["metrics"]["hit_rate"]
    agreement = v2_summary["metrics"]["agreement_rate"]

    if delta_score > 0 and delta_hit_rate >= -0.05 and agreement >= 0.7:
        decision = "APPROVE"
        message = "Update meets quality thresholds. RELEASE APPROVED."
    elif delta_score >= 0 and delta_hit_rate >= -0.10:
        decision = "CONDITIONAL"
        message = "Update meets minimum thresholds. CONDITIONAL RELEASE."
    else:
        decision = "BLOCK"
        message = "Update fails quality thresholds. RELEASE BLOCKED."

    return {
        "decision": decision,
        "message": message,
        "delta_score": round(delta_score, 4),
        "delta_hit_rate": round(delta_hit_rate, 4),
        "agreement_rate": round(agreement, 4),
        "thresholds": {
            "score_delta": {"APPROVE": ">0", "CONDITIONAL": ">=0", "BLOCK": "<0"},
            "hit_rate_delta": {"APPROVE": ">=-0.05", "CONDITIONAL": ">=-0.10", "BLOCK": "<-0.10"},
            "agreement_rate": {"APPROVE": ">=0.7", "CONDITIONAL": "any", "BLOCK": "N/A"},
        },
    }
