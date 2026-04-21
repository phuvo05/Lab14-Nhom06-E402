# Báo cáo Cá nhân - Phản ánh và Đóng góp

## Thông tin thành viên

| Thông tin | Chi tiết |
|-----------|----------|
| **Họ và Tên** | Đào Hồng Sơn |
| **MSSV** | 2A202600462 |
| **Vai trò** | AI/Backend Engineer - Multi-Judge Specialist |
| **Nhóm** | Nhom06-E402 |

---

## 1. Đóng góp kỹ thuật (Engineering Contribution)

### Module chịu trách nhiệm chính

#### 1.1 `engine/llm_judge.py` - Multi-Judge Consensus Engine
- **Mô tả:** Implement hệ thống đánh giá sử dụng đồng thời 2 model judges (GPT-4o-mini và Claude-3.5-Haiku) để tăng độ tin cậy.
- **Tính năng chính:**
  - Gọi song song 2 model judges bằng `asyncio.gather`
  - Tính Cohen's Kappa để đo độ đồng thuận
  - Agreement Rate: `1.0 - |score_a - score_b| / 5.0`
  - Conflict Resolution: Khi lệch > 1 điểm, dùng weighted average (60/40)
  - Position Bias Check: Đổi chỗ response để phát hiện bias
  - Rubrics chi tiết: Accuracy, Tone, Safety, Completeness

#### 1.2 `engine/metrics.py` - RAGAS Metrics Wrapper
- **Mô tả:** Implement wrapper cho faithfulness và answer relevancy evaluation.
- **Tính năng:**
  - `calculate_faithfulness()`: Đánh giá câu trả lời có trung thành với context
  - `calculate_answer_relevancy()`: Đánh giá mức độ liên quan đến câu hỏi
  - `calculate_context_precision()`: Đánh giá retrieval quality
  - Heuristic fallback khi API fails

### Code mẫu đóng góp chính

```python:88:110:engine/llm_judge.py
async def evaluate_multi_judge(self, question, answer, ground_truth):
    score_gpt_raw, score_claude_raw = await asyncio.gather(
        self._call_openai(question, answer, ground_truth),
        self._call_anthropic(question, answer, ground_truth),
    )

    if abs(score_gpt - score_claude) > 1.0:
        final = max(score_gpt, score_claude) * 0.6 + min(score_gpt, score_claude) * 0.4
    else:
        final = (score_gpt + score_claude) / 2

    return {"final_score": round(final, 2), "agreement_rate": round(agreement, 4),
            "cohens_kappa": round(kappa, 4), "individual_scores": {...}}
```

---

## 2. Kiến thức học được (Technical Depth)

### 2.1 Cohen's Kappa
- Đo độ đồng thuận giữa 2 raters (judges) đã điều chỉnh cho chance agreement.
- Công thức: `κ = (Po - Pe) / (1 - Pe)`
  - Po = observed agreement
  - Pe = expected agreement by chance
- Interpretation: κ > 0.8 = almost perfect, 0.6-0.8 = substantial, < 0.6 = moderate/poor

### 2.2 Position Bias in LLM Evaluation
- Judge models có xu hướng đánh giá response đầu tiên cao hơn dù nội dung tương đương.
- Cách phát hiện: Đổi chỗ A/B trong prompt, so sánh điểm.
- **Giải pháp:** Randomize thứ tự options trong judge prompt.

### 2.3 Multi-Judge Reliability
- Tin vào 1 judge duy nhất (ví dụ GPT-4o) là rủi ro trong production
- Multi-judge giảm variance và tăng reliability
- Trade-off: Chi phí tăng gấp đôi, latency tăng nhưng accuracy tăng đáng kể

### 2.4 Cost-Quality Trade-off Analysis
| Strategy | Cost | Quality Gain |
|----------|------|-------------|
| Single GPT-4o | $0.60/eval | Baseline |
| 2x GPT-4o-mini | $0.30/eval | Similar quality |
| GPT-4o + Claude | $0.85/eval | +15% reliability |

---

## 3. Khó khăn và cách giải quyết (Problem Solving)

### Khó khăn 1: Claude API không có sẵn cho tất cả thành viên
- **Vấn đề:** Không phải ai cũng có API key cho Claude.
- **Giải pháp:** Sử dụng Claude Haiku (rẻ nhất, ~$0.25/1M tokens) thay vì Claude Sonnet.
- **Kết quả:** Giảm 70% chi phí Claude, vẫn đảm bảo diversity.

### Khó khăn 2: Xử lý xung đột điểm số giữa 2 judges
- **Vấn đề:** Khi 2 judges cho điểm lệch nhau nhiều (ví dụ 2.0 vs 4.5), simple average không hợp lý.
- **Giải pháp:** Weighted average: `max*0.6 + min*0.4` - bias towards higher score (benefit of doubt).
- **Kết quả:** Logic xử lý xung đột tự động, không cần human intervention.

### Khó khăn 3: Retry khi API call thất bại
- **Vấn đề:** Một số API call fail do network hoặc rate limit.
- **Giải pháp:** Implement `asyncio.wait_for` với timeout, fallback scores khi fail.
- **Kết quả:** Pipeline không crash khi có 1-2 API failures.

---

## 4. Điểm mạnh và Điểm yếu

| | |
|---|---|
| **Điểm mạnh** | Hiểu sâu về LLM evaluation, multi-model consensus, bias detection |
| **Điểm yếu** | Chưa implement được calibrated scoring (raw score → probability) |

---

## 5. Kế hoạch cải tiến cá nhân

- [ ] Implement calibrated scoring: chuyển raw scores sang calibrated probabilities
- [ ] Thêm Bayesian averaging cho multi-judge aggregation
- [ ] Implement majority voting với weighted scores thay vì simple/weighted average
