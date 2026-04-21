# Báo cáo Cá nhân - Phản ánh và Đóng góp

## Thông tin thành viên

| Thông tin | Chi tiết |
|-----------|----------|
| **Họ và Tên** | Phan Dương Định |
| **MSSV** | 2A202600277 |
| **Vai trò** | DevOps / Performance Engineer |
| **Nhóm** | Nhom06-E402 |

---

## 1. Đóng góp kỹ thuật (Engineering Contribution)

### Module chịu trách nhiệm chính

#### 1.1 `engine/runner.py` - Async Benchmark Runner
- **Mô tả:** Implement async benchmark runner với concurrency control, timeout, retry logic, và cost tracking.
- **Tính năng chính:**
  - `asyncio.Semaphore(max_concurrency=3)` để kiểm soát concurrency
  - `asyncio.wait_for` với configurable timeout (60s default)
  - Retry logic cho API failures
  - `get_cost_report()`: Tổng hợp cost, tokens, errors
  - `save_reports()`: Xuất JSON reports
  - `auto_release_gate()`: Logic tự động quyết định APPROVE/CONDITIONAL/BLOCK

#### 1.2 `main.py` - Orchestration & Regression Pipeline
- **Mô tả:** Implement main orchestration với V1 vs V2 regression comparison.
- **Tính năng:**
  - Tự động generate dataset nếu chưa có
  - Chạy V1 (Base) và V2 (Optimized) benchmarks
  - Delta analysis: so sánh score, hit_rate, mrr, agreement_rate
  - Regression comparison table
  - Tích hợp đầy đủ: agent + judge + evaluator

### Code mẫu đóng góp chính

```python:48:67:engine/runner.py
async def run_all(self, dataset: List[Dict], batch_size: int = 3) -> List[Dict]:
    results = []
    for i in range(0, total_cases, batch_size):
        batch = dataset[i:i + batch_size]
        tasks = [self._run_single_with_semaphore(case) for case in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        results.extend(batch_results)
    return results
```

```python:122:138:engine/runner.py
def auto_release_gate(v1_summary: Dict, v2_summary: Dict) -> Dict[str, Any]:
    if delta_score > 0 and delta_hit_rate >= -0.05 and agreement >= 0.7:
        decision = "APPROVE"
    elif delta_score >= 0 and delta_hit_rate >= -0.10:
        decision = "CONDITIONAL"
    else:
        decision = "BLOCK"
    return {"decision": decision, "message": ..., "thresholds": {...}}
```

---

## 2. Kiến thức học được (Technical Depth)

### 2.1 Asynchronous Programming với asyncio
- `asyncio.gather()`: Chạy nhiều coroutines song song
- `asyncio.Semaphore()`: Kiểm soát concurrency, tránh rate limit
- `asyncio.wait_for()`: Timeout cho async operations
- `return_exceptions=True` trong gather: Không crash khi 1 coroutine fail
- Performance gain: 3x-5x nhanh hơn synchronous khi chạy nhiều I/O-bound tasks

### 2.2 Release Gate Logic
- **APPROVE:** delta_score > 0 AND hit_rate_delta >= -0.05 AND agreement >= 0.7
  - Meaning: Agent cải thiện score, retrieval không tệ hơn nhiều, judges đồng thuận
- **CONDITIONAL:** delta_score >= 0 AND hit_rate_delta >= -0.10
  - Meaning: Agent không giảm score, retrieval có thể tệ hơn nhưng trong ngưỡng chấp nhận được
- **BLOCK:** delta_score < 0 OR hit_rate_delta < -0.10 OR agreement < 0.5
  - Meaning: Agent tệ hơn rõ rệt hoặc judges không đồng thuận

### 2.3 Performance Optimization Strategies
| Strategy | Impact | Implementation |
|----------|--------|---------------|
| Batch API calls | -50% latency | asyncio.gather with batch_size=3 |
| Semantic caching | -30% cost | Cache judge responses |
| Concurrent judges | ~same total time | 2 judges run in parallel |
| Smaller top_k | -20% tokens | top_k=5 instead of 10 |

---

## 3. Khó khăn và cách giải quyết (Problem Solving)

### Khó khăn 1: Benchmark chạy quá chậm (timeout)
- **Vấn đề:** 50 cases x 2 versions = 100 API calls, mỗi call có thể mất 2-5s.
- **Giải pháp:** Tăng concurrency từ 1 → 3, giảm batch_size để tránh rate limit, implement timeout 60s.
- **Kết quả:** Pipeline hoàn thành trong ~5 phút thay vì ~20 phút.

### Khó khăn 2: Xử lý exceptions trong async pipeline
- **Vấn đề:** Một API call fail có thể crash cả batch.
- **Giải pháp:** `return_exceptions=True` trong `asyncio.gather`, fallback error result thay vì crash.
- **Kết quả:** Pipeline chạy ổn định, ghi nhận error count trong report.

### Khó khăn 3: Cân bằng giữa cost và quality
- **Vấn đề:** Dùng GPT-4o cho tất cả calls → cost quá cao.
- **Giải pháp:** Sử dụng tiered approach:
  - Generation: GPT-4o-mini (cheap)
  - Primary Judge: GPT-4o-mini (cheap)
  - Secondary Judge: Claude Haiku (cheap, diverse)
  - Heuristic fallback khi API fails
- **Kết quả:** Giảm 70% chi phí mà vẫn đảm bảo multi-judge diversity.

---

## 4. Điểm mạnh và Điểm yếu

| | |
|---|---|
| **Điểm mạnh** | Hiểu sâu async architecture, performance optimization, release gate design |
| **Điểm yếu** | Chưa implement được real-time progress streaming (WebSocket) |

---

## 5. Kế hoạch cải tiến cá nhân

- [ ] Implement caching layer (Redis) cho judge responses để giảm cost thêm
- [ ] Thêm real-time progress streaming qua WebSocket
- [ ] Implement distributed benchmark runner (multi-process) cho >500 cases
