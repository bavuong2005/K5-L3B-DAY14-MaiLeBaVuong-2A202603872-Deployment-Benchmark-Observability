# Benchmark & Observability Report — Day 14

> Copy file này thành `BENCHMARK_REPORT.md` trong repo của bạn và điền đầy đủ.
> Mọi con số phải lấy từ report JSON / CSV / screenshot thật, không ước lượng.

**Họ tên:** Mai Lê Bá Vương
**Ngày chạy:** 26/11/2026
**Môi trường:** Windows, Docker Desktop chạy container Linux `python:3.12-slim`. Client và app mock chạy trong cùng container qua loopback. Đây là lượt chạy của trợ lý trên máy lab.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Giới hạn mặc định của phép đo latency. |
| Error rate `/ask` | ≤ 2% | Giới hạn mặc định của phép đo tỷ lệ request lỗi. |
| Accuracy trên golden dataset | 100% ở lượt sửa cuối | 23/23 câu đạt và không có regression so với v2 ban đầu. |

### Exercise 7.1 — Metrics

- Counter đếm số request, gauge theo dõi số request đang xử lý và histogram gom số đo vào bucket để xem phân bố.
- Gắn nhãn bằng route template hoặc `unmatched` để số chuỗi metric không tăng theo từng URL có ID khác nhau.
- `agent_question_length_chars` quan sát số ký tự mỗi câu hỏi hợp lệ. Sau eval v2, `/metrics` báo kiểu histogram, `_count=23`, `_sum=1066`, bucket `le="50.0"` có 16 quan sát.

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.31 | 187.9 | 219.6 | 1704.4 | 0.67% | PASS |
| 10 | 44.72 | 186.3 | 216.9 | 1700.4 | 1.67% | PASS |
| 50 | 106.94 | 193.0 | 226.0 | 1684.4 | 1.00% | PASS |
| 100 | 81.17 | 287.7 | 2209.2 | 2409.3 | 1.00% | FAIL |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

RPS đạt đỉnh 106,94 ở concurrency 50 rồi giảm xuống 81,17 ở 100, đồng thời p95 tăng từ 226,0 lên 2.209,2 ms. Kết quả phù hợp với hiện tượng xếp hàng khi tăng tải. Phép đo này chưa xác định tài nguyên nào bị nghẽn.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 188.4 | 215.4 | 219.0 |
| 0.03 (mặc định) | 227.9 | 218.5 | 1678.3 |
| 0.1 | 310.3 | 1685.2 | 1703.9 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

p99 phản ứng rõ từ tỷ lệ chậm 3%, còn p95 tăng mạnh ở 10%. Trung bình ở 10% vẫn chỉ 310,3 ms nên dễ che mất nhóm request chờ hơn 1,6 giây. Mỗi lượt đo gửi 300 request.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 57.8 | 108.7 | 114.0 |
| Tổng cost (USD) | 0.000414 | 0.000756 | 0.000793 |
| Cost / câu đúng (USD) | 0.00041415 | 0.00003599 | 0.00003449 |
| Quality gate | FAIL | PASS | PASS, 0 regression |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm mục JWT, giải thích claims, chữ ký và hạn dùng. |
| scaling-03 | cpu, memory, custom metrics | Thêm mục HPA, giải thích điều chỉnh replica theo CPU, RAM và custom metrics. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

V2 dùng nhiều token và có p95 cao hơn v1 (204,7 so với 187,4 ms), nhưng trả lời đúng 21 câu so với 1. Sau khi sửa knowledge base, v2 đạt 23/23 với p95 215,4 ms. Tổng chi phí mock tăng nhưng chi phí trên mỗi câu đúng giảm.

---

### Quality gate trong CI (Exercise 7.3)

Job kiểm tra pull request cài dependencies, khởi động v2 với `MOCK_ERROR_RATE=0` và chờ `/health` trả 200. Sau đó chạy `run_eval.py` với ngưỡng accuracy và baseline đã chọn. Exit code 1 làm job thất bại nếu quality gate không đạt. Đặt job làm required check để GitHub chặn merge khi job thất bại.

## 4. Observability stack (production)

Stack chạy local bằng Docker Compose. `promtool test rules` trả `SUCCESS`. `GET http://localhost:8080/metrics` qua Nginx trả `404` vì cấu hình chặn route ở proxy. Prometheus scrape trực tiếp các agent qua mạng nội bộ.

Dashboard được kiểm tra qua API Grafana và có các panel Traffic, Error rate, Latency p95 và Saturation. p95 cho thấy nhóm request chậm mà giá trị trung bình có thể che khuất. Error rate của agent đo các mã lỗi do agent trả. Nếu Nginx tự trả 504, request có thể chưa tới agent hoặc agent chưa ghi được response, nên cần theo dõi thêm mã lỗi ở proxy. Phân bố traffic theo replica có thể đối chiếu với header `X-Served-By`. V2 đưa cả câu hỏi và ngữ cảnh truy xuất vào prompt, vì vậy input tokens có thể cao hơn output tokens của câu trả lời ngắn.

### 4.1 Screenshot

- [x] [Dashboard Grafana dưới tải](screenshots/grafana-dashboard.png) với Golden Signals.
- [x] [Trace Jaeger chậm](screenshots/jaeger-slow-trace.png) thấy span LLM chiếm phần lớn thời gian.
- [x] [Trace Jaeger lỗi](screenshots/jaeger-error-trace.png) có event `exception`.
- [x] [Prometheus Alerts](screenshots/prometheus-alert-firing.png) thấy cả hai alert cùng **firing**.

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 102,4 s | Error rate (21,8% lúc quan sát) |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 152,5 s | Latency p95 (1,90 s lúc quan sát) |
| C | `LLM_MODEL=mock-llm-large` | Chưa chạy | — | LLM cost |
| D | `docker pause` 1 instance | Chưa chạy | — | Instances up |
| E | `AGENT_VERSION=v1` | Chưa chạy trên stack | — | Eval chất lượng |

A và B chạy đồng thời trên hai replica, với Locust 30 users, ramp 5/s. Bắt đầu áp dụng lúc 17:06:40 (GMT+7). Đo từ lúc bắt đầu cập nhật Compose đến lần đầu API Prometheus trả `firing`, với chu kỳ kiểm tra khoảng 5 s. Đã quan sát cả hai alert `firing` cùng lúc.

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

Chạy eval theo lịch và trước khi deploy, dùng bộ câu hỏi cố định và so kết quả theo từng ID với baseline. Phát cảnh báo khi tỷ lệ đạt quality gate giảm hoặc có regression. Latency, error rate và availability không đo độ đúng của nội dung trả lời.

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: `0e2f3d1722022d948f40ec7f9e52e682`
- Tổng thời gian của `POST /ask`: 1.711,216 ms.
- Span con chiếm phần lớn thời gian: `chat mock-llm-small` mất 1.695,839 ms (99,1% tổng thời gian).
- Dòng log tương ứng (grep theo `trace_id`):

```json
{"ts":"2026-11-26T09:59:50.306284+00:00","level":"INFO","service":"observable-agent","instance":"1f85a207e02d","event":"llm_call","trace_id":"0e2f3d1722022d948f40ec7f9e52e682","span_id":"3b08248b396e0252","request_id":"22f80ec78edc","model":"mock-llm-small","agent_version":"v2","input_tokens":83,"output_tokens":44,"cost_usd":0.000039,"llm_ms":1695.2}
```

Trace lỗi `8fb00236e1a9de4b5b9c268e05962d04` trả HTTP 503. Jaeger ghi event `exception` trên span `chat mock-llm-small` (80,119 ms) và `agent.run`. Log agent cùng trace ID ghi `llm_error` với lỗi upstream 503 mô phỏng.

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 60.21 | 190 | 220 | 1700 | 82 / 7159 |
| 3 | 60.29 | 190 | 220 | 1700 | 65 / 7177 |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

Các số lấy từ dòng `POST /ask` của hai file CSV trong `benchmark-results/`. Cả hai lần chạy 100 users, ramp 10/s trong 2 phút. Prometheus thấy đúng 1 hoặc 3 target `UP` trước mỗi lượt. Locust chạy với `--no-deps` để giữ nguyên số replica. p95 giữ ở 220 ms và RPS gần như không đổi. Trace chậm cho thấy lời gọi mock LLM chiếm 99,1% thời gian của request đó. Kết quả phù hợp với workload bị chi phối bởi thời gian chờ và mức tải cố định, chưa cho biết thông lượng tối đa của từng cấu hình.

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. Concurrency cao hơn có thể làm p95 tăng và RPS giảm khi hệ thống bắt đầu xếp hàng.
  2. Tăng replica có thể giữ nguyên latency nếu phần lớn thời gian nằm ở downstream.
  3. Metrics cho biết lúc nào có vấn đề, trace và log cùng ID giúp xác định nó xảy ra ở bước nào.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

Thêm tỷ lệ 502/504 ở proxy, độ trễ upstream và quality gate định kỳ trên bộ eval cố định.
