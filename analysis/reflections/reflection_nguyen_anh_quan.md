# Báo cáo Cá nhân - Phản ánh và Đóng góp

## Thông tin thành viên

| Thông tin | Chi tiết |
|-----------|----------|
| **Họ và Tên** | Nguyễn Anh Quân |
| **MSSV** | 2A202600132 |
| **Vai trò** | Analyst / Failure Analysis Specialist |
| **Nhóm** | Nhom06-E402 |

---

## 1. Đóng góp kỹ thuật (Engineering Contribution)

### Module chịu trách nhiệm chính

#### 1.1 `analysis/failure_analysis.md` - Failure Analysis Report
- **Mô tả:** Thiết kế và hoàn thiện báo cáo phân tích lỗi toàn diện.
- **Phần phân tích:**
  - Tổng quan benchmark với metrics comparison V1 vs V2
  - Failure clustering: phân nhóm lỗi theo type (Hallucination, Incomplete, Tone, etc.)
  - 5 Whys root cause analysis cho 3 case tệ nhất
  - Action plan với priority và expected impact

#### 1.2 `check_lab.py` - Validation & Grading Script
- **Mô tả:** Script validation tự động kiểm tra format submission.
- **Tính năng:**
  - Check existence của required files
  - Validate JSON format của summary.json
  - Check required fields (metrics, metadata, hit_rate, agreement_rate)
  - Expert-level checks: retrieval metrics, multi-judge metrics, regression version

#### 1.3 Retrieval Failure Analysis
- Phân tích mối liên hệ Retrieval Quality vs Answer Quality
- Cluster retrieval failures: empty_retrieval, partial_match, no_match
- Đề xuất chiến lược cải thiện dựa trên data

### Analysis Framework

```python
Failure Analysis Pipeline:
  1. Collect all failed cases (score < 3.0)
  2. Classify failure type:
     - RAGAS metrics (faithfulness < 0.5 → Hallucination)
     - hit_rate == 0 → Retrieval Fail
     - score difference > 1.0 → Judge Conflict
  3. Apply 5 Whys for each failure cluster
  4. Prioritize actions by impact/frequency
```

---

## 2. Kiến thức học được (Technical Depth)

### 2.1 5 Whys Root Cause Analysis
- Phương pháp điều tra nguyên nhân gốc rễ bằng cách hỏi "Tại sao?" 5 lần liên tiếp.
- **Ví dụ:** Case retrieval fail
  - Why 1: Vector DB không tìm đúng docs → Why 2: Embedding không match → Why 3: Chunking quá lớn → ...
  - Root Cause: Chiến lược chunking không phù hợp với data structure

### 2.2 Failure Clustering Taxonomy
| Cluster | Trigger | Typical Solution |
|---------|---------|-----------------|
| Hallucination | faithfulness < 0.5 | Better prompt, fewer docs |
| Incomplete | relevancy < 0.5 | More context, better retrieval |
| Tone Mismatch | tone score < 2.5 | Prompt rewrite |
| Out of Context | Asked to hallucinate | Safety layer |
| Retrieval Fail | hit_rate = 0 | Better embeddings/chunks |

### 2.3 Metrics Interpretation
- **Faithfulness vs Relevancy:** Faithfulness đo answer-context match; Relevancy đo answer-question match
- **Hit Rate vs MRR:** Hit Rate chỉ quan tâm "có tìm được không"; MRR còn quan tâm "ở vị trí nào"
- **Agreement Rate vs Cohen's Kappa:** Agreement Rate đơn giản; Cohen's Kappa điều chỉnh cho chance

### 2.4 Data-Driven Decision Making
- Sử dụng metrics để drive engineering decisions
- A/B testing với regression comparison
- Prioritization framework: High impact + High frequency = Do first

---

## 3. Khó khăn và cách giải quyết (Problem Solving)

### Khó khăn 1: Thiết kế adversarial test cases hiệu quả
- **Vấn đề:** Làm sao tạo test cases đủ khó để phát hiện weaknesses mà không quá artificial.
- **Giải pháp:** Dựa trên real-world attack patterns (prompt injection, social engineering), phân bổ theo tỉ lệ real-world frequency.
- **Kết quả:** 15 adversarial cases phân bổ hợp lý, cover prompt injection, goal hijacking, out-of-context.

### Khó khăn 2: Xác định root cause thực sự
- **Vấn đề:** Nhiều lỗi có symptoms giống nhau nhưng root causes khác nhau.
- **Giải pháp:** Sử dụng decision tree để phân biệt: Check hit_rate → If 0 → Retrieval fail; If > 0 → Check faithfulness → If low → Hallucination; Else → Incomplete.
- **Kết quả:** Accuracy của failure classification tăng lên.

### Khó khăn 3: Đưa ra actionable recommendations
- **Vấn đề:** Nhiều analysis chỉ nói "cải thiện retrieval" nhưng không cụ thể.
- **Giải pháp:** Map root cause → specific action với expected impact và priority.
- **Kết quả:** Action plan có 6 items với rõ ràng priority và expected metrics improvement.

---

## 4. Điểm mạnh và Điểm yếu

| | |
|---|---|
| **Điểm mạnh** | Hiểu sâu về failure analysis, root cause analysis, data-driven decision making |
| **Điểm yếu** | Chưa implement được automated failure classification (cần ML model) |

---

## 5. Kế hoạch cải tiến cá nhân

- [ ] Implement automated failure classifier sử dụng LLM (thay vì rule-based)
- [ ] Thêm trend analysis: so sánh metrics qua nhiều versions
- [ ] Implement anomaly detection cho metrics (z-score)
- [ ] Tạo interactive dashboard cho failure analysis (Streamlit)
