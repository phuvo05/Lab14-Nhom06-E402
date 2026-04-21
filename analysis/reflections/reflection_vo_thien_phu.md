# Báo cáo Cá nhân - Phản ánh và Đóng góp

## Thông tin thành viên

| Thông tin | Chi tiết |
|-----------|----------|
| **Họ và Tên** | Võ Thiên Phú |
| **MSSV** | 2A202600336 |
| **Vai trò** | Data Team Lead / Retrieval Specialist |
| **Nhóm** | Nhom06-E402 |

---

## 1. Đóng góp kỹ thuật (Engineering Contribution)

### Module chịu trách nhiệm chính

#### 1.1 `agent/vector_store.py` - Vector Store Implementation
- **Mô tả:** Implement VectorStore sử dụng OpenAI `text-embedding-3-small` cho embeddings và in-memory storage cho documents.
- **Tính năng chính:**
  - `add_documents()`: Thêm documents và tự động compute embeddings
  - `search()`: Tìm kiếm top-k documents bằng cosine similarity
  - `build_vector_store_from_dataset()`: Helper function để build vector store từ golden dataset
  - Fallback fake embeddings khi không có API key
- **Kỹ thuật sử dụng:** NumPy dot product cho similarity, OpenAI Embeddings API, caching

#### 1.2 `data/synthetic_gen.py` - Golden Dataset Generator
- **Mô tả:** Implement hệ thống generate 50+ test cases với đa dạng categories và difficulty levels.
- **Phân bổ cases:**
  - 20 Easy (fact-check questions)
  - 19 Medium (reasoning questions)
  - 11 Hard (adversarial, edge cases, prompt injection, multi-turn)
- **Challenge:** Thiết kế Red Teaming cases để phá vỡ hệ thống (prompt injection, goal hijacking, out-of-context)

#### 1.3 Retrieval Evaluation (`engine/retrieval_eval.py`)
- Implement Hit Rate@K (K=1,3,5)
- Implement MRR (Mean Reciprocal Rank)
- Implement NDCG@K
- Failure clustering logic

### Code mẫu đóng góp chính

```python:1:40:agent/vector_store.py
def search(self, query: str, top_k: int = 5) -> List[Document]:
    query_emb = self._get_embedding(query)
    query_emb = query_emb / (np.linalg.norm(query_emb) + 1e-8)
    similarities = self.embeddings @ query_emb
    top_indices = np.argsort(similarities)[::-1][:top_k]
    return [self.documents[i] for i in top_indices]
```

---

## 2. Kiến thức học được (Technical Depth)

### 2.1 Retrieval Metrics
- **Hit Rate@K:** Tỉ lệ có ít nhất 1 relevant document trong top K kết quả. Công thức: `HR = |{relevant docs} ∩ {top-K}| / |{relevant docs}|`
- **MRR (Mean Reciprocal Rank):** Trung bình nghịch đảo của vị trí đầu tiên có relevant document. `MRR = mean(1/rank_i)`
- **NDCG@K:** Normalized Discounted Cumulative Gain - đánh giá cả relevance lẫn vị trí.

### 2.2 Semantic Chunking vs Fixed-Size Chunking
- Fixed-size: Đơn giản nhưng có thể cắt giữa câu/đoạn quan trọng
- Semantic: Cắt theo ngữ nghĩa (sentence, paragraph), giữ được context nguyên vẹn
- Trade-off: Semantic chunking tốt hơn cho RAG nhưng phức tạp hơn về implementation

### 2.3 Cost-Quality Trade-off
| Approach | Cost | Quality | Use Case |
|----------|------|---------|----------|
| GPT-4o | $15/1M in | Highest | Production judges |
| GPT-4o-mini | $0.15/1M in | High | Daily eval |
| Claude Haiku | $0.25/1M in | High | Secondary judge |

**Chiến lược:** Dùng GPT-4o-mini cho generation, Claude Haiku cho secondary judge, giảm 60% chi phí.

---

## 3. Khó khăn và cách giải quyết (Problem Solving)

### Khó khăn 1: API Rate Limiting
- **Vấn đề:** Khi chạy 50 cases với multi-judge (2 API calls mỗi case), dễ bị rate limit.
- **Giải pháp:** Implement `asyncio.Semaphore(max_concurrency=3)` và batch_size=3, retry logic 3 lần.
- **Kết quả:** Pipeline chạy ổn định không bị rate limit.

### Khó khăn 2: Embedding Consistency
- **Vấn đề:** Mỗi lần query, embedding có thể khác nhau do API.
- **Giải pháp:** Implement caching cho query embeddings trong `_embedding_cache`.
- **Kết quả:** Consistent search results, giảm API calls.

### Khó khăn 3: Fallback khi không có API key
- **Vấn đề:** Nếu không có API key, vector store không hoạt động.
- **Giải pháp:** Implement `_fake_embedding()` sử dụng character-based hash để tạo deterministic embeddings.
- **Kết quả:** Code hoạt động được trong demo mode.

---

## 4. Điểm mạnh và Điểm yếu

| | |
|---|---|
| **Điểm mạnh** | Hiểu sâu về retrieval systems, embeddings, vector similarity; thiết kế dataset có tính đa dạng cao |
| **Điểm yếu** | Chưa implement được Cross-Encoder reranking; chưa tối ưu hóa được chunking strategy |

---

## 5. Kế hoạch cải tiến cá nhân

- [ ] Implement Cross-Encoder reranking sau retrieval stage
- [ ] Thử nghiệm Semantic Chunking với LlamaIndex
- [ ] Tìm hiểu ColBERT (late interaction) cho retrieval thay vì bi-directional embedding
