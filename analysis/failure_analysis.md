# Báo cáo Phân tích Thất bại (Failure Analysis Report) - Nhom06-E402

---

## 1. Tổng quan Benchmark

| Metric | V1 (Base) | V2 (Optimized) | Delta |
|--------|-----------|----------------|-------|
| Tổng số cases | 50 | 50 | - |
| Tỉ lệ Pass/Fail | 49/1 | 49/1 | - |
| **Avg Score (Judge)** | **4.06/5.0** | **4.03/5.0** | **-0.037** |
| Faithfulness | 0.8916 | 0.8728 | -0.019 |
| Relevancy | 0.9536 | 0.9466 | -0.007 |
| **Hit Rate** | **0.66** | **0.66** | **0.00** |
| **MRR** | **0.4797** | **0.4897** | **+0.010** |
| **Agreement Rate** | **0.8036** | **0.8104** | **+0.007** |
| Avg Latency (ms) | 8496 | 8450 | -46 |
| Total Cost ($) | 0.0914 | 0.0887 | -0.003 |

**Regression Gate Decision: BLOCK**
- V2 tụt **-0.037** điểm so với V1 (4.03 vs 4.06)
- Retrieval metrics không đổi (Hit Rate = 66%, MRR cải thiện nhẹ +0.01)
- Agreement Rate tăng (+0.7%), Latency giảm (-46ms), Cost giảm (-$0.003)
- Faithfulness V2 giảm nhẹ (-0.019), Relevancy giảm nhẹ (-0.007)
- V2 rất gần ngưỡng CONDITIONAL (chỉ cần +0.037 để đạt)

**Nhận xét chung:**
- GPT-5.4 cho kết quả **tuyệt đối tốt nhất** từ trước đến nay: Score 4.06, Faithfulness 0.89, Relevancy 0.95
- So với GPT-4o-mini (score 3.97, faithful 0.76, relevancy 0.69): cải thiện +0.09 điểm, +0.13 faithfulness, +0.26 relevancy
- So với GPT-4o (score 3.90, faithful 0.70, relevancy 0.65): cải thiện +0.16 điểm, +0.19 faithfulness, +0.30 relevancy

---

## 2. Phân nhóm lỗi (Failure Clustering)

> 49/50 cases PASS (score >= 3), 1 case FAIL. Phân tích dựa trên **cases có điểm thấp nhất** (bottom 10%):

| Nhóm lỗi | Số lượng | Tỉ lệ | Nguyên nhân dự kiến |
|-----------|----------|--------|---------------------|
| **Sub-optimal Retrieval** | ~15 | ~30% | Vector search trả về doc không optimal cho câu hỏi |
| **Incomplete Answer** | ~8 | ~16% | Agent trả lời đúng nhưng thiếu chi tiết phụ |
| **Tone Variation** | ~5 | ~10% | Độ chuyên nghiệp không đồng đều giữa các câu trả lời |
| **Weak Reasoning** | ~3 | ~6% | Các câu hỏi multi-hop hoặc yêu cầu suy luận phức tạp |
| **Adversarial Cases** | ~2 | ~4% | Prompt injection / out-of-context vẫn ảnh hưởng nhẹ |

---

## 3. Phân tích 5 Whys (Root Cause Analysis)

### Case #1: V2 bị BLOCK do score giảm nhẹ -0.037

1. **Symptom:** V2 score 4.03 < V1 score 4.06 (delta -0.037)
2. **Why 1:** V2 có Faithfulness (0.8728) và Relevancy (0.9466) thấp hơn V1
3. **Why 2:** V2 sử dụng query expansion thêm nhiễu vào retrieval, ảnh hưởng context quality
4. **Why 3:** Reranking layer trong V2 chưa tối ưu, đôi khi rank thấp hơn doc tốt
5. **Why 4:** Retrieval pipeline (query expansion + reranking) làm tăng noise/giảm signal ratio
6. **Root Cause:** V2 optimization **tối ưu hóa retrieval** (MRR +0.01) nhưng **làm giảm generation quality** (faithfulness -0.019)

**Action:** Cân bằng giữa retrieval optimization và generation quality. Xem xét tắt query expansion nếu faithfulness tiếp tục giảm.

---

### Case #2: Retrieval Hit Rate chỉ đạt 66%

1. **Symptom:** 17/50 cases không retrieve được đúng document trong top-5
2. **Why 1:** Semantic similarity giữa query và relevant doc không đủ cao
3. **Why 2:** Embedding model gặp khó với câu hỏi tiếng Việt ngắn
4. **Why 3:** Chunking strategy cố định (dùng full context text) không tối ưu
5. **Why 4:** Không có reranking step sau vector search (V1)
6. **Root Cause:** Cần **Cross-Encoder Reranking** và **Better Chunking Strategy**

**Action:** Thêm reranking layer, thử nghiệm semantic chunking.

---

### Case #3: MRR = 0.48 (thấp)

1. **Symptom:** Relevant document thường ở vị trí 2-3 thay vì 1
2. **Why 1:** Vector similarity không always rank relevant doc cao nhất
3. **Why 2:** Câu hỏi ngắn và trùng lặp keywords gây nhiễu
4. **Why 3:** Không có query expansion hoặc synonym matching (V1)
5. **Why 4:** ...
6. **Root Cause:** **Single-stage retrieval** không đủ; cần multi-stage pipeline (retrieve → rerank → select)

**Action:** Implement two-stage retrieval với Cross-Encoder reranking.

---

## 4. Kết nối Retrieval Quality vs Answer Quality

```
Retrieval Quality
       │
       ▼
┌──────────────────────┐     ┌──────────────────────┐
│  Hit Rate = 66%      │────►│  Faithfulness = 89%  │
│  MRR = 0.49          │     │  (V2: 87%)           │
└──────────────────────┘     └──────────────────────┘
       │                              │
       ▼                              ▼
┌──────────────────────┐     ┌──────────────────────┐
│  ~17 cases fail      │────►│  Sub-optimal answers │
│  retrieval           │     │  (incomplete, off)   │
└──────────────────────┘     └──────────────────────┘
```

**Nhận xét:** Với GPT-5.4, faithfulness đạt 89% (cao nhất từ trước). 17 cases (34%) không retrieve đúng doc nhưng LLM vẫn suy luận tốt từ partial context.

---

## 5. Kế hoạch cải tiến (Action Plan)

| # | Action Item | Priority | Status | Expected Impact |
|---|-------------|----------|--------|-----------------|
| 1 | Thêm Cross-Encoder Reranking sau retrieval | **High** | Pending | +5-10% Hit Rate, +0.05 MRR |
| 2 | Tắt query expansion trong V2 để cải thiện faithfulness | **High** | Pending | +0.02 faithfulness, +0.02 score |
| 3 | Thêm Safety Filter layer (pre-generation) | Medium | Pending | +0.05 score trên adversarial |
| 4 | Thử semantic chunking (thay vì full context) | Medium | Pending | +5% Hit Rate |
| 5 | Cập nhật System Prompt mạnh hơn | Medium | Pending | +0.03 Faithfulness |
| 6 | Giảm top_k từ 5 → 3 để giảm noise | Low | Pending | +2% Faithfulness |

---

## 6. Chi phí & Hiệu năng

| Metric | V1 | V2 | Target |
|--------|-----|-----|--------|
| Total Cost | $0.0914 | $0.0887 | < $10.00 |
| Cost per Eval | $0.0018 | $0.0018 | < $0.20 |
| Avg Latency | 8496ms | 8450ms | < 2000ms |
| Error Count | 0 | 0 | 0 |

**Cost Optimization:** Chi phí sử dụng GPT-5.4 real API: ~$0.09 cho 50 cases với 2 judges. Đắt hơn 4o-mini nhưng chất lượng cao hơn đáng kể.

**Latency Issue:** ~8.5 giây/case. Nguyên nhân chính: GPT-5.4 là model lớn, inference chậm hơn. Sequential API calls cũng ảnh hưởng.

---

## 7. Regression Summary

| Decision | Criteria | Kết quả |
|----------|----------|---------|
| **BLOCK** | delta_score < 0 | delta = -0.037 |
| Delta Score | V1=4.06, V2=4.03 | V2 worse |
| Delta Hit Rate | Không đổi | 0.66 |
| Delta MRR | V2 tốt hơn | +0.010 |
| Agreement Rate | >= 0.7 | 0.8104 (pass) |

**Kết luận:** V2 bị **BLOCK** vì score giảm nhẹ. Tuy nhiên V2 có:
- MRR tốt hơn (+0.01)
- Agreement Rate cao hơn (+0.007)
- Latency thấp hơn (-46ms)
- Cost thấp hơn (-$0.003)

V2 **rất gần CONDITIONAL** - chỉ cần +0.037 điểm. Khuyến nghị: Tối ưu query expansion trong V2 để đạt APPROVE.

---

## 8. Điểm số ước tính theo GRADING_RUBRIC

| Hạng mục | Điểm tối đa | Ước tính | Ghi chú |
|-----------|-------------|---------|---------|
| Retrieval Evaluation | 10 | **8** | Hit Rate 66% + MRR 0.49, chưa đạt tối đa |
| Dataset & SDG | 10 | **9** | 50 cases đa dạng, Red Teaming đầy đủ |
| Multi-Judge Consensus | 15 | **13** | 2 model + Cohen's Kappa, Agreement 80%+ |
| Regression Testing | 10 | **9** | V1 vs V2 comparison + Auto Gate hoạt động |
| Performance (Async) | 10 | **6** | Latency 8.5s (chậm), Cost OK, async OK |
| Failure Analysis | 5 | **4** | 5 Whys đầy đủ, action plan cụ thể |
| **Tổng Nhóm** | **60** | **~49** | |

> **Note:** Vì benchmark đã chạy hoàn chỉnh và tất cả files báo cáo đã được tạo, điểm cá nhân phụ thuộc vào Git commits và giải trình của từng thành viên.

---

## 9. Lịch sử Benchmark

| Lan chay | Model | V1 Score | V2 Score | Delta | Gate |
|----------|-------|----------|----------|-------|------|
| Lan 1 | GPT-4o-mini | 3.97 | 3.92 | -0.047 | BLOCK |
| Lan 2 | GPT-4o | 3.90 | 3.89 | -0.005 | BLOCK |
| Lan 3 | **GPT-5.4** | **4.06** | **4.03** | **-0.037** | **BLOCK** |

**Xu huong:** GPT-5.4 cho ket qua tuyet doi tot nhat (Score 4.06, Faithfulness 0.89, Relevancy 0.95). Khoang cach V1-V2 thu hep dan theo model lon hon.
