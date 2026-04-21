# Hướng dẫn Commit & Push cho Team - Nhom06-E402

## Quy tắc chung

1. **Mỗi thành viên làm việc trên branch riêng của mình**
2. **Commit thường xuyên** (ít nhất 1 commit cho mỗi module hoàn thành)
3. **PR/merge vào `main`** sau khi hoàn thành module
4. **Không push `.env`**, `data/golden_set.jsonl`, `reports/`, `__pycache__/`, `*.pyc` lên GitHub
5. **Message format:** `[Module] - Mô tả ngắn`

---

## Danh sách Branch và Module cho từng thành viên

### Thành viên 1: Võ Thiên Phú (MSSV: 2A202600336)
**Branch:** `feature/retrieval-and-dataset`

| # | File/Module | Mô tả commit |
|---|-------------|---------------|
| 1 | `agent/vector_store.py` | `[Retrieval] Implement VectorStore with OpenAI embeddings` |
| 2 | `data/synthetic_gen.py` | `[Dataset] Generate 50+ test cases with adversarial cases` |
| 3 | `engine/retrieval_eval.py` | `[Retrieval] Implement Hit Rate, MRR, NDCG metrics` |
| 4 | `data/golden_set.jsonl` | `[Dataset] Generated golden dataset (do NOT push this file)` |

**Script:**
```bash
git checkout -b feature/retrieval-and-dataset
git add agent/vector_store.py data/synthetic_gen.py engine/retrieval_eval.py
git commit -m "[Retrieval-Dataset] Complete retrieval pipeline and SDG module"
git push -u origin feature/retrieval-and-dataset
```

---

### Thành viên 2: Đào Hồng Sơn (MSSV: 2A202600462)
**Branch:** `feature/multi-judge-engine`

| # | File/Module | Mô tả commit |
|---|-------------|---------------|
| 1 | `engine/llm_judge.py` | `[Judge] Implement multi-judge with GPT and Claude` |
| 2 | `engine/metrics.py` | `[Metrics] Implement RAGAS faithfulness and relevancy wrapper` |
| 3 | `engine/judge.py` | `[Judge] Add judge wrapper module` |

**Script:**
```bash
git checkout -b feature/multi-judge-engine
git add engine/llm_judge.py engine/metrics.py engine/judge.py
git commit -m "[Judge] Multi-judge consensus engine with Cohen's Kappa"
git push -u origin feature/multi-judge-engine
```

---

### Thành viên 3: Phan Dương Định (MSSV: 2A202600277)
**Branch:** `feature/async-runner-and-orchestration`

| # | File/Module | Mô tả commit |
|---|-------------|---------------|
| 1 | `engine/runner.py` | `[Runner] Implement async BenchmarkRunner with concurrency control` |
| 2 | `main.py` | `[Main] Orchestrate full pipeline with V1 vs V2 regression` |
| 3 | `engine/runner.py` (update) | `[Runner] Add auto-release-gate logic` |

**Script:**
```bash
git checkout -b feature/async-runner-and-orchestration
git add engine/runner.py main.py
git commit -m "[Runner] Async benchmark runner with release gate and cost tracking"
git push -u origin feature/async-runner-and-orchestration
```

---

### Thành viên 4: Phạm Minh Khang (MSSV: 2A202600417)
**Branch:** `feature/rag-agent`

| # | File/Module | Mô tả commit |
|---|-------------|---------------|
| 1 | `agent/main_agent.py` | `[Agent] Implement RAG pipeline with GPT-4o-mini` |
| 2 | `agent/main_agent.py` (update) | `[Agent] Add system prompt safety rails and cost tracking` |

**Script:**
```bash
git checkout -b feature/rag-agent
git add agent/main_agent.py
git commit -m "[Agent] RAG agent pipeline with vector store integration"
git push -u origin feature/rag-agent
```

---

### Thành viên 5: Nguyễn Anh Quân (MSSV: 2A202600132)
**Branch:** `feature/analysis-and-docs`

| # | File/Module | Mô tả commit |
|---|-------------|---------------|
| 1 | `analysis/failure_analysis.md` | `[Analysis] Complete failure analysis with 5 Whys` |
| 2 | `analysis/reflections/` | `[Analysis] Add individual reflection reports for all members` |
| 3 | `check_lab.py` (nếu sửa) | `[Docs] Validation script ready for grading` |

**Script:**
```bash
git checkout -b feature/analysis-and-docs
git add analysis/failure_analysis.md analysis/reflections/
git commit -m "[Analysis] Failure analysis report and individual reflections"
git push -u origin feature/analysis-and-docs
```

---

## Quy trình Merge (Thứ tự)

```
1. feature/retrieval-and-dataset       → merge vào main TRƯỚC
2. feature/multi-judge-engine          → merge vào main
3. feature/async-runner-and-orchestration → merge vào main
4. feature/rag-agent                   → merge vào main
5. feature/analysis-and-docs           → merge vào main CUỐI CÙNG
```

### Merge commands:
```bash
# Switch to main
git checkout main
git pull origin main

# Merge each branch
git merge feature/retrieval-and-dataset --no-edit
git merge feature/multi-judge-engine --no-edit
git merge feature/async-runner-and-orchestration --no-edit
git merge feature/rag-agent --no-edit
git merge feature/analysis-and-docs --no-edit

# Push merged main
git push origin main
```

---

## Sau khi tất cả merge xong

### Mỗi thành viên chạy:
```bash
# Pull latest main
git checkout main
git pull origin main

# Verify all files
python check_lab.py

# Kiểm tra reports/
ls reports/
cat reports/summary.json | python -m json.tool | head -30
```

---

## Gitignore đã được cấu hình (không push lên GitHub)

```
.env                    # API keys
data/golden_set.jsonl   # Generated dataset
reports/                # Generated reports
__pycache__/            # Python cache
*.pyc
.DS_Store
```

---

## Lưu ý quan trọng

1. **KHÔNG BAO GIỜ push `.env`** - Có API keys!
2. **Commit message phải rõ ràng** - Mỗi commit mô tả 1 thay đổi cụ thể
3. **Test trước khi push** - Chạy `python check_lab.py` để verify
4. **Nếu conflict xảy ra** - Thông báo trong nhóm, không tự resolve mà không báo
5. **Branch name convention:** `feature/<module-name>` hoặc `fix/<issue-name>`

---

## Timeline đề xuất

| Thời gian | Việc cần làm |
|-----------|-------------|
| T0 - T15 | Tạo branches, assign modules |
| T15 - T60 | Implement modules (parallel) |
| T60 - T90 | PR reviews, merge |
| T90 - T120 | Integration test, fix conflicts |
| T120+ | Run benchmark, finalize reports |
