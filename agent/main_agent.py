import asyncio
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


class MainAgent:
    """
    RAG Agent sử dụng OpenAI GPT-5.4 cho generation
    và OpenAI text-embedding-3-small cho retrieval.
    V1: Pure dense vector search
    V2: Hybrid search (dense + BM25) + Cross-Encoder reranking
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
        vector_store=None,
        system_prompt: Optional[str] = None,
        agent_version: str = "v1",
    ):
        self.name = f"SupportAgent-{agent_version.upper()}"
        self.model = model
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.agent_version = agent_version
        self.total_tokens = 0
        self.total_cost = 0.0

        if agent_version == "v1":
            self.system_prompt = system_prompt or (
                "Bạn là một trợ lý hỗ trợ khách hàng chuyên nghiệp. "
                "Hãy trả lời câu hỏi dựa TRÊN NGỮ CẢNH ĐƯỢC CUNG CẤP. "
                "Nếu ngữ cảnh không chứa thông tin cần thiết, hãy nói rõ: "
                "'Tôi không tìm thấy thông tin này trong tài liệu.' "
                "KHÔNG được bịa đặt thông tin. "
                "Trả lời bằng tiếng Việt, lịch sự và chuyên nghiệp."
            )
        else:
            self.system_prompt = system_prompt or (
                "Bạn là một trợ lý hỗ trợ khách hàng chuyên nghiệp. "
                "Hãy trả lời câu hỏi dựa TRÊN NGỮ CẢNH ĐƯỢC CUNG CẤP. "
                "Nếu ngữ cảnh không chứa thông tin cần thiết, hãy nói rõ: "
                "'Tôi không tìm thấy thông tin này trong tài liệu.' "
                "KHÔNG được bịa đặt thông tin. "
                "Trả lời bằng tiếng Việt, lịch sự và chuyên nghiệp. "
                "LUÔN ưu tiên thông tin từ ngữ cảnh đầu tiên (quan trọng nhất). "
                "Nếu câu hỏi hỏi về chính sách cụ thể, hãy trích dẫn đúng thông tin từ ngữ cảnh."
            )

    def set_vector_store(self, vs):
        self.vector_store = vs

    async def _generate_with_openai(
        self, question: str, contexts: List[str]
    ) -> Dict:
        try:
            from openai import OpenAI
            client = OpenAI()

            context_text = "\n\n".join(f"--- Ngữ cảnh {i+1} ---\n{c}" for i, c in enumerate(contexts))
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

            input_cost = (usage.prompt_tokens / 1_000_000) * 2.50
            output_cost = (usage.completion_tokens / 1_000_000) * 15.00
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
            }
        except Exception as e:
            return {
                "answer": f"Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi: {str(e)}",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "cost": 0.0,
            }

    def _retrieve(self, question: str) -> tuple:
        """Retrieve documents based on agent version."""
        if not self.vector_store:
            return [], []

        if self.agent_version == "v1":
            docs = self.vector_store.search_v1_style(question, top_k=5)
        else:
            docs = self.vector_store.search(question, top_k=5)

        contexts = [doc.text for doc in docs]
        retrieved_ids = [doc.id for doc in docs]
        return contexts, retrieved_ids

    async def query(self, question: str) -> Dict:
        contexts, retrieved_ids = self._retrieve(question)
        result = await self._generate_with_openai(question, contexts)

        sources = []
        if self.vector_store:
            try:
                for doc in self.vector_store.search(question, top_k=5):
                    sources.append(doc.metadata.get("source", "unknown"))
            except Exception:
                sources = [doc.metadata.get("source", "unknown") for doc in self.vector_store.search(question, top_k=5)]

        return {
            "answer": result["answer"],
            "contexts": contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "model": self.model,
                "version": self.agent_version,
                "tokens_used": result["usage"]["total_tokens"],
                "cost": result["cost"],
                "sources": sources,
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
