import asyncio
from typing import List, Dict, Any, Optional
from collections import defaultdict


class RetrievalEvaluator:
    def __init__(self):
        pass

    def calculate_hit_rate(
        self,
        expected_ids: List[str],
        retrieved_ids: List[str],
        top_k: int = 3,
    ) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0
        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_hit_rate_at_k(
        self,
        expected_ids: List[str],
        retrieved_ids: List[str],
        k_values: List[int] = None,
    ) -> Dict[int, float]:
        if k_values is None:
            k_values = [1, 3, 5]
        results = {}
        for k in k_values:
            results[f"hit_rate@{k}"] = self.calculate_hit_rate(
                expected_ids, retrieved_ids, top_k=k
            )
        return results

    def calculate_mrr(
        self, expected_ids: List[str], retrieved_ids: List[str]
    ) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    def calculate_ndcg(
        self, expected_ids: List[str], retrieved_ids: List[str], k: int = 5
    ) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0

        ideal_order = expected_ids[:k]
        dcg = 0.0
        for i, rid in enumerate(retrieved_ids[:k]):
            if rid in expected_ids:
                pos = expected_ids.index(rid)
                dcg += 1.0 / (pos + 1) if pos < k else 0.0

        idcg = sum(1.0 / (i + 1) for i in range(min(len(ideal_order), k)))

        return dcg / idcg if idcg > 0 else 0.0

    async def evaluate_batch(
        self, dataset: List[Dict], vector_store=None
    ) -> Dict[str, Any]:
        hit_rates = []
        mrr_scores = []
        ndcg_scores = []

        retrieval_failures = []
        retrieval_success = []

        for item in dataset:
            expected_ids = item.get("expected_retrieval_ids", [])
            retrieved_ids = item.get("retrieved_ids", [])

            if not expected_ids:
                continue

            hit = self.calculate_hit_rate(expected_ids, retrieved_ids)
            mrr = self.calculate_mrr(expected_ids, retrieved_ids)
            ndcg = self.calculate_ndcg(expected_ids, retrieved_ids)

            hit_rates.append(hit)
            mrr_scores.append(mrr)
            ndcg_scores.append(ndcg)

            if hit == 0.0:
                retrieval_failures.append({
                    "question": item["question"],
                    "expected_ids": expected_ids,
                    "retrieved_ids": retrieved_ids,
                    "mrr": mrr,
                })
            else:
                retrieval_success.append(item["question"])

        avg_hit = sum(hit_rates) / len(hit_rates) if hit_rates else 0.0
        avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

        hit_at_k = self._calculate_avg_hit_at_k(dataset)

        return {
            "avg_hit_rate": round(avg_hit, 4),
            "avg_mrr": round(avg_mrr, 4),
            "avg_ndcg": round(avg_ndcg, 4),
            "total_cases": len(hit_rates),
            "retrieval_failures": retrieval_failures,
            "retrieval_success_count": len(retrieval_success),
            "hit_rate_at_k": {k: round(v, 4) for k, v in hit_at_k.items()},
        }

    def _calculate_avg_hit_at_k(self, dataset: List[Dict]) -> Dict[int, float]:
        k_values = [1, 3, 5]
        results = {}
        for k in k_values:
            hits = [
                self.calculate_hit_rate(
                    item.get("expected_retrieval_ids", []),
                    item.get("retrieved_ids", []),
                    top_k=k,
                )
                for item in dataset
                if item.get("expected_retrieval_ids")
            ]
            results[k] = sum(hits) / len(hits) if hits else 0.0
        return results

    def cluster_retrieval_failures(
        self, failures: List[Dict]
    ) -> Dict[str, List[Dict]]:
        clusters = defaultdict(list)
        for failure in failures:
            expected = set(failure["expected_ids"])
            retrieved = set(failure["retrieved_ids"])

            if not retrieved:
                clusters["empty_retrieval"].append(failure)
            elif failure["mrr"] > 0:
                clusters["partial_match"].append(failure)
            else:
                clusters["no_match"].append(failure)

        return dict(clusters)
