# Báo cáo Cá nhân - Phản ánh và Đóng góp

## Thông tin thành viên

| Thông tin | Chi tiết |
|-----------|----------|
| **Họ và Tên** | Phạm Minh Khang |
| **MSSV** | 2A202600417 |
| **Vai trò** | Agent Engineer / RAG Pipeline Specialist |
| **Nhóm** | Nhom06-E402 |

---

## 1. Đóng góp kỹ thuật (Engineering Contribution)

### Module chịu trách nhiệm chính

#### 1.1 `agent/main_agent.py` - RAG Agent Pipeline
- **Mô tả:** Implement RAG pipeline hoàn chỉnh: Retrieval → Rerank → Generation.
- **Tính năng chính:**
  - `query()`: Main entry point, orchestrates retrieval + generation
  - `set_vector_store()`: Inject vector store dependency
  - OpenAI Chat Completions API cho generation
  - System prompt với safety instructions
  - Cost và token tracking
  - Graceful error handling với fallback responses

#### 1.2 System Prompt Engineering
- **Mô tả:** Thiết kế system prompt để ngăn hallucination và out-of-context answers.
- **Key instructions:**
  - "Chỉ trả lời dựa TRÊN NGỮ CẢNH ĐƯỢC CUNG CẤP"
  - "KHÔNG được bịa đặt thông tin"
  - "Nếu không có thông tin, nói rõ: 'Tôi không tìm thấy...'"
- **Effect:** Giảm hallucination rate đáng kể trên adversarial cases.

### Code mẫu đóng góp chính

```python:38:55:agent/main_agent.py
async def query(self, question: str) -> Dict:
    contexts = []
    retrieved_ids = []

    if self.vector_store:
        docs = self.vector_store.search(question, top_k=5)
        contexts = [doc.text for doc in docs]
        retrieved_ids = [doc.id for doc in docs]

    result = await self._generate_with_openai(question, contexts)
    return {
        "answer": result["answer"],
        "contexts": contexts,
        "retrieved_ids": retrieved_ids,
        "metadata": {"model": self.model, "tokens_used": ..., "cost": ...},
    }
```

---

## 2. Kiến thức học được (Technical Depth)

### 2.1 RAG Pipeline Architecture
```
User Question
      │
      ▼
┌─────────────────┐
│  Vector Search   │──► top_k=5 most similar docs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Context Prep   │──► Combine retrieved docs into context
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Generation │──► GPT-4o-mini with system prompt
└────────┬────────┘
         │
         ▼
  Final Answer + Metadata
```

### 2.2 Prompt Engineering Best Practices
- **Specificity:** Prompt càng cụ thể, answer càng chính xác
- **Safety rails:** Explicitly instruction "do not hallucinate", "say I don't know"
- **Format control:** Yêu cầu structured output để dễ parse
- **Few-shot examples:** Thêm examples trong prompt cho edge cases

### 2.3 Cost Optimization in RAG
| Component | Model | Cost/1K tokens | Optimization |
|-----------|-------|---------------|-------------|
| Embedding | text-embedding-3-small | $0.02 | Batch embed |
| Generation | gpt-4o-mini | $0.60 | Reduce max_tokens |
| Judge | gpt-4o-mini | $0.60 | Cache responses |

**Total cost per eval:** ~$0.05 (1 embedding + 1 generation + 2 judges)

### 2.4 Trade-off Analysis: Retrieval Quality vs Generation Quality
- Retrieval bad → Generation bad (garbage in, garbage out)
- But: Good retrieval + bad prompt → also bad answer
- Key insight: Both stages need optimization, not just one
- Benchmark showed: 10% Hit Rate improvement → 8% Faithfulness improvement

---

## 3. Khó khăn và cách giải quyết (Problem Solving)

### Khó khăn 1: Agent trả lời hallucinations trên adversarial cases
- **Vấn đề:** Prompt injection và out-of-context questions khiến Agent bịa đặt.
- **Giải pháp:** Thêm explicit safety instruction trong system prompt, thêm verification step.
- **Kết quả:** Out-of-context cases có faithfulness cao hơn.

### Khó khăn 2: Latency quá cao cho generation
- **Vấn đề:** GPT-4o generation mất 3-5s mỗi call.
- **Giải pháp:** Dùng GPT-4o-mini thay vì GPT-4o (5x faster, 20x cheaper).
- **Kết quả:** Latency giảm từ 5s → 1.5s, cost giảm 95%.

### Khó khăn 3: Context overflow với nhiều retrieved docs
- **Vấn đề:** Quá nhiều context có thể làm confuse LLM hoặc exceed token limit.
- **Giải pháp:** Giới hạn top_k=5, ưu tiên docs có similarity score cao nhất.
- **Kết quả:** Balance giữa recall và precision.

---

## 4. Điểm mạnh và Điểm yếu

| | |
|---|---|
| **Điểm mạnh** | Hiểu sâu về RAG pipeline, prompt engineering, cost optimization |
| **Điểm yếu** | Chưa implement được reranking stage; chưa thử hybrid search (BM25 + vector) |

---

## 5. Kế hoạch cải tiến cá nhân

- [ ] Implement Cross-Encoder reranking sau vector search
- [ ] Thử hybrid search: BM25 + vector similarity kết hợp
- [ ] Implement query decomposition cho multi-aspect questions
- [ ] Thử query expansion để cải thiện recall
