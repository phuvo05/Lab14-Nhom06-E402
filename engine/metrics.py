import asyncio
import time
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class MetricsCalculator:
    def __init__(self):
        self.rubrics = {
            "faithfulness": "Đánh giá câu trả lời có trung thành với context hay không. "
                            "Tính bằng tỉ lệ statements trong câu trả lời được hỗ trợ bởi context.",
            "relevancy": "Đánh giá mức độ câu trả lời liên quan đến câu hỏi.",
            "context_precision": "Đánh giá độ chính xác của context được retrieve.",
            "context_recall": "Đánh giá recall của context so với ground truth.",
        }

    async def calculate_faithfulness(
        self, question: str, answer: str, contexts: List[str]
    ) -> float:
        if not contexts:
            return 0.0

        try:
            from openai import OpenAI
            client = OpenAI()

            context_text = "\n".join(f"- {c}" for c in contexts[:3])
            prompt = f"""Bạn là một chuyên gia đánh giá faithfulness.
Hãy đánh giá câu trả lời dưới đây có trung thành với context hay không.
Tính điểm từ 0.0 đến 1.0 (1.0 = hoàn toàn trung thành, không bịa đặt).

Câu hỏi: {question}
Context:
{context_text}
Câu trả lời: {answer}

Chỉ trả về một con số duy nhất từ 0.0 đến 1.0, ví dụ: 0.85"""
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_completion_tokens=10,
            )
            score_text = response.choices[0].message.content.strip()
            score = float(score_text)
            return max(0.0, min(1.0, score))
        except Exception:
            return self._heuristic_faithfulness(answer, contexts)

    def _heuristic_faithfulness(self, answer: str, contexts: List[str]) -> float:
        context_text = " ".join(contexts).lower()
        answer_lower = answer.lower()
        words_in_answer = set(answer_lower.split())
        words_in_context = set(context_text.split())
        overlap = words_in_answer & words_in_context
        if not words_in_answer:
            return 1.0
        return len(overlap) / len(words_in_answer) * 0.8

    async def calculate_answer_relevancy(
        self, question: str, answer: str
    ) -> float:
        try:
            from openai import OpenAI
            client = OpenAI()

            prompt = f"""Đánh giá mức độ câu trả lời sau có liên quan đến câu hỏi hay không.
Điểm từ 0.0 đến 1.0 (1.0 = rất liên quan, 0.0 = không liên quan).

Câu hỏi: {question}
Câu trả lời: {answer}

Chỉ trả về một con số duy nhất từ 0.0 đến 1.0, ví dụ: 0.85"""
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_completion_tokens=10,
            )
            score_text = response.choices[0].message.content.strip()
            score = float(score_text)
            return max(0.0, min(1.0, score))
        except Exception:
            q_words = set(question.lower().split())
            a_words = set(answer.lower().split())
            if not q_words:
                return 0.5
            overlap = len(q_words & a_words) / len(q_words)
            return min(1.0, overlap + 0.3)

    async def calculate_context_precision(
        self, question: str, expected_ids: List[str], retrieved_ids: List[str]
    ) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0
        top_k = min(len(retrieved_ids), 5)
        relevant = 0
        for i, rid in enumerate(retrieved_ids[:top_k]):
            if rid in expected_ids:
                relevant += 1 / (i + 1)
        return min(1.0, relevant)

    async def calculate_context_recall(
        self, expected_ids: List[str], retrieved_ids: List[str]
    ) -> float:
        if not expected_ids:
            return 1.0
        if not retrieved_ids:
            return 0.0
        retrieved_set = set(retrieved_ids)
        expected_set = set(expected_ids)
        overlap = retrieved_set & expected_set
        return len(overlap) / len(expected_set)

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

    async def calculate_ragas_metrics(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        expected_ids: Optional[List[str]] = None,
        retrieved_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        faithfulness = await self.calculate_faithfulness(question, answer, contexts)
        relevancy = await self.calculate_answer_relevancy(question, answer)

        retrieval = {}
        if expected_ids is not None and retrieved_ids is not None:
            retrieval["hit_rate"] = 1.0 if any(e in retrieved_ids for e in expected_ids) else 0.0
            mrr = 0.0
            for i, rid in enumerate(retrieved_ids):
                if rid in expected_ids:
                    mrr = 1.0 / (i + 1)
                    break
            retrieval["mrr"] = mrr
            ctx_prec = await self.calculate_context_precision(
                question, expected_ids, retrieved_ids
            )
            ctx_recall = await self.calculate_context_recall(expected_ids, retrieved_ids)
            retrieval["context_precision"] = ctx_prec
            retrieval["context_recall"] = ctx_recall

        return {
            "faithfulness": round(faithfulness, 4),
            "relevancy": round(relevancy, 4),
            "retrieval": retrieval,
        }
