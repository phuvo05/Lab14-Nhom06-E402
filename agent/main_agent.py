import asyncio
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


MODEL_PRICING_PER_1M = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-5.4": {"input": 2.50, "output": 15.00},
}


class MainAgent:
    """
    RAG Agent sử dụng OpenAI GPT-4o mini cho generation
    và OpenAI text-embedding-3-small cho retrieval.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        vector_store=None,
        system_prompt: Optional[str] = None,
    ):
        self.name = "SupportAgent-v2"
        self.model = model
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.total_tokens = 0
        self.total_cost = 0.0

        self.system_prompt = system_prompt or (
            "Bạn là một trợ lý hỗ trợ khách hàng chuyên nghiệp. "
            "Hãy trả lời câu hỏi chỉ dựa TRÊN NGỮ CẢNH ĐƯỢC CUNG CẤP. "
            "Nếu ngữ cảnh không chứa thông tin cần thiết, hãy nói rõ: "
            "'Tôi không tìm thấy thông tin này trong tài liệu.' "
            "KHÔNG được bịa đặt thông tin. "
            "Không suy diễn thêm chính sách, giá tiền, quy trình hay thời hạn nếu tài liệu không nêu. "
            "Nếu câu hỏi nguy hiểm, trái phép hoặc không phù hợp với vai trò hỗ trợ, hãy từ chối ngắn gọn và an toàn. "
            "Trả lời bằng tiếng Việt, lịch sự và chuyên nghiệp."
        )

    def set_vector_store(self, vs):
        self.vector_store = vs

    async def _generate_with_openai(
        self, question: str, contexts: List[str]
    ) -> Dict:
        try:
            from openai import OpenAI
            client = OpenAI()

            if contexts:
                context_text = "\n\n".join(
                    f"--- Ngữ cảnh {i+1} ---\n{c}" for i, c in enumerate(contexts)
                )
            else:
                context_text = (
                    "Không có ngữ cảnh liên quan nào được truy xuất. "
                    "Hãy thông báo rõ rằng tài liệu hiện tại không chứa thông tin cần thiết."
                )

            user_prompt = f"""Ngữ cảnh tài liệu:
{context_text}

Câu hỏi: {question}

Câu trả lời (dựa trên ngữ cảnh trên):"""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_completion_tokens=500,
            )

            answer = response.choices[0].message.content.strip()
            usage = response.usage

            pricing = MODEL_PRICING_PER_1M.get(self.model, MODEL_PRICING_PER_1M["gpt-4o-mini"])
            input_cost = (usage.prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (usage.completion_tokens / 1_000_000) * pricing["output"]
            cost = input_cost + output_cost

            self.total_tokens += usage.total_tokens
            self.total_cost += cost

            return {
                "answer": answer,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                },
                "cost": cost,
                "finish_reason": response.choices[0].finish_reason,
            }
        except Exception as e:
            return {
                "answer": f"Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi: {str(e)}",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "cost": 0.0,
                "finish_reason": "error",
            }

    async def query(self, question: str) -> Dict:
        contexts = []
        retrieved_ids = []
        retrieved_docs = []

        if self.vector_store:
            retrieved_docs = self.vector_store.search(question, top_k=5)
            contexts = [doc.text for doc in retrieved_docs]
            retrieved_ids = [doc.id for doc in retrieved_docs]

        result = await self._generate_with_openai(question, contexts)

        return {
            "answer": result["answer"],
            "contexts": contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "model": self.model,
                "tokens_used": result["usage"]["total_tokens"],
                "usage": result["usage"],
                "cost": result["cost"],
                "finish_reason": result["finish_reason"],
                "sources": [
                    doc.metadata.get("source", "unknown") for doc in retrieved_docs
                ],
                "retrieval_count": len(retrieved_docs),
            },
        }

    def reset_usage(self):
        self.total_tokens = 0
        self.total_cost = 0.0


if __name__ == "__main__":
    async def test():
        agent = MainAgent()
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)

    asyncio.run(test())
