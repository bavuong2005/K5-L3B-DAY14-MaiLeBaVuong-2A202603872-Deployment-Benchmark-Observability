# MISSION ANSWERS — Day 14 (K5)

> Chỉ ghi kết quả và số liệu đã tự chạy, tự kiểm chứng. Không đưa secret, email hoặc số điện thoại vào file này.

## CP0 — Chuẩn bị môi trường

- Repo: `K5-L3B-DAY14-MaiLeBaVuong-2A202603872-Deployment-Benchmark-Observability`
- Remote: `https://github.com/bavuong2005/K5-L3B-DAY14-MaiLeBaVuong-2A202603872-Deployment-Benchmark-Observability`
- Trạng thái public: xác nhận remote đọc được ẩn danh bằng `git ls-remote --symref origin HEAD`.
- `git status --short`: `?? PLAN_DAY14.md`
- WSL2: Ubuntu đã được cài trong lần hỗ trợ trước. Đề K5 yêu cầu WSL2 trên Windows và không chỉ định distro.
- Kết quả kiểm tra Windows hiện tại: Python 3.11.9; `os.name` là `nt`; Docker Compose v5.2.0.
- `docker run --rm hello-world`: lần chạy lại của học viên trong PowerShell tải image thành công và in `Hello from Docker!`.
- Kết quả kiểm tra Docker Engine bằng image có sẵn: `python:3.12-slim` chạy thành công, Python 3.12.16.
- Kết quả kiểm tra CP0 trong WSL2 (điền sau khi hoàn tất):
  - `python3 --version`: `Python 3.14.4`. Lệnh `python` trong venv chưa sẵn sàng vì `venv` báo thiếu `ensurepip`.
  - `python3 -c 'import os; print(os.name)'`: `posix`.
  - `docker compose version`:
  - `docker run --rm hello-world`:

## Part 1 — Localhost vs Production

### Exercise 1.1 — Anti-patterns

| Anti-pattern | Vị trí trong code | Tác động |
| --- | --- | --- |
| Ghi credential trực tiếp trong mã nguồn | `develop/app.py:17–18` | Nếu dùng credential thật, người có quyền đọc repo hoặc lịch sử Git có thể lấy được chúng. |
| Đặt cấu hình ứng dụng cố định | `develop/app.py:21–22` | Muốn đổi chế độ debug hoặc giới hạn token trong mã mẫu phải sửa nguồn. |
| In API key ra log | `develop/app.py:34` | Credential thật có thể bị lộ cho người đọc log, kể cả khi repo là private. |
| Thiếu endpoint kiểm tra sức khỏe | `develop/app.py:25–43` | Nền tảng triển khai không có probe riêng để kiểm tra ứng dụng còn hoạt động và sẵn sàng nhận traffic. |
| Cố định host và port | `develop/app.py:49–52` | Bind localhost giới hạn truy cập ngoài container. Port cố định có thể khác cổng nền tảng cấp. |
| Luôn bật tự nạp lại mã nguồn | `develop/app.py:53` | Thay đổi file có thể khởi động lại tiến trình phục vụ và làm gián đoạn request. |

### Exercise 1.2 — Chạy app develop

- Chạy `python app.py` trong `01-localhost-vs-production/develop/` bằng container Linux tạm `python:3.12-slim` với các dependency của mẫu. Gửi `POST /ask?question=Hello` bằng Python urllib từ trong container.
- HTTP 200. Body từ lần chạy kiểm tra của trợ lý. Học viên đã báo chạy xong trong PowerShell; output PowerShell chưa được cung cấp để điền vào đây.

```json
{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

### Exercise 1.3 — So sánh develop và production

Chạy `python app.py` trong `01-localhost-vs-production/production/` sau khi dừng bản develop. Bản production mẫu chạy với cấu hình mặc định và mock LLM.

| Request | HTTP | Body thực tế |
| --- | --- | --- |
| `GET /health` | 200 | `{"status":"ok","uptime_seconds":1.8,"version":"1.0.0","environment":"development","timestamp":"2026-11-26T08:16:13.488604+00:00"}` |
| `GET /ready` | 200 | `{"ready":true}` |
| `POST /ask` với `{"question":"Hello"}` | 200 | `{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","model":"gpt-4o-mini"}` |

Sau khi gửi SIGTERM cho bản production, Uvicorn ghi `Application shutdown complete.`

| Khía cạnh | Develop | Production | Vì sao khác biệt quan trọng |
| --- | --- | --- | --- |
| Cấu hình | Host, port và reload cố định (`develop/app.py:51–53`). | Đọc `HOST`, `PORT` và `DEBUG` từ biến môi trường (`production/config.py:17–19`) rồi truyền vào Uvicorn (`production/app.py:194–198`). | Dùng cùng mã nguồn cho nhiều môi trường và nhận đúng cổng nền tảng cấp. |
| Health check | Chỉ có trang gốc và endpoint hỏi đáp (`develop/app.py:25–39`). | `/health` báo trạng thái tiến trình. `/ready` trả 503 nếu chưa sẵn sàng (`production/app.py:135–161`). | Nền tảng có thể phân biệt app đang sống với app đã sẵn sàng nhận traffic. |
| Logging | Dùng `print` và in cả key mẫu (`develop/app.py:33–38`). | Dùng `logging` và ghi sự kiện request dưới dạng JSON (`production/app.py:28–32`, `111–125`). | Log có cấu trúc dễ lọc theo sự kiện và tránh đưa key vào hệ thống thu thập log. |
| Graceful shutdown | Không có lifespan riêng cho ứng dụng. | Lifespan chuyển cờ readiness về false khi chạy phần shutdown (`production/app.py:40–67`). | App có chỗ để chạy logic dọn dẹp khi server dừng. |

## Part 2 — Docker

### Exercise 2.1 — Câu trả lời

1. `02-docker/develop/Dockerfile` dùng base image `python:3.11`.
2. `WORKDIR /app` đặt thư mục làm việc trong container. Các đường dẫn tương đối sau đó, kể cả khi chạy `python app.py`, được tính từ đây.
3. Chép riêng `requirements.txt` rồi cài dependency trước khi chép code. Khi chỉ đổi code, Docker có thể dùng lại lớp cài dependency.
4. `CMD ["python", "app.py"]` là lệnh mặc định của image này và có thể thay bằng đối số sau tên image trong `docker run`. Nếu image có `ENTRYPOINT` dạng exec, đối số sau tên image thay `CMD` và được truyền cho `ENTRYPOINT`. Dùng `--entrypoint` để thay entrypoint.

### Exercise 2.2–2.3 — Container và kích thước image

- Kết quả lần chạy của trợ lý trên máy này: `POST /ask?question=What%20is%20Docker%3F` trả `HTTP/1.1 200 OK` và `{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}`.
- `docker images my-agent`, cột Content Size: develop **426 MB**, advanced **57,4 MB**.
- `docker image inspect`, số byte lần lượt là `426320063` và `57409065`. Mức giảm `(426320063 − 57409065) / 426320063 × 100` = **86.53%**.
- Stage builder cài compiler, thư viện build và Python dependencies. Stage runtime dùng `python:3.11-slim`, chỉ chép Python dependencies đã cài và mã chạy app. Công cụ build nằm ngoài image cuối.

### Exercise 2.4 — Compose và Nginx

- Sơ đồ service:

```text
Client → Nginx :80 → agent :8000
                     ├── Redis :6379  (cache / rate limiting)
                     └── Qdrant :6333 (vector database)
```

Compose cấu hình địa chỉ Redis và Qdrant cho agent trên mạng bridge. Hai dòng nhánh biểu diễn cấu hình stack. Handler `/ask` trong `02-docker/production/main.py:58–64` gọi mock LLM.
- Windows từ chối bind host port 80. Lần kiểm tra dùng override tạm `127.0.0.1:18080:80`, giữ nguyên file Compose của đề.
- `docker compose -p k5-day14-docker ps` liệt kê Nginx, agent, Redis và Qdrant. Agent, Redis và Qdrant đều healthy.
- `GET http://127.0.0.1:18080/health` → `200 OK`, `Server: nginx`, body `{"status":"ok","uptime_seconds":18.9,"version":"2.0.0","timestamp":"2026-11-26T08:31:38.826882"}`.
- `POST http://127.0.0.1:18080/ask` với `{"question":"Explain microservices"}` → `200 OK`, `Server: nginx`, body `{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}`.
- Đã dừng container demo và dọn project Compose CP2 bằng `down -v`.

## Part 3 — Cloud Deployment

- Deploy trên Render tại https://k5-day14-agent-enmo.onrender.com. Học viên xác nhận `200 / 200 / 401 / 200` cho `/health`, `/ready`, `POST /ask` thiếu key và `POST /ask` có key. Xem [DEPLOYMENT.md](DEPLOYMENT.md) và ảnh [dashboard](screenshots/dashboard.png), [running](screenshots/running.png), [test](screenshots/test.png).
- **So sánh mẫu Railway và Render.** Mẫu Railway đặt builder `NIXPACKS` trong TOML. Mẫu Render đặt `runtime: python` cho web service trong YAML. Cả hai chạy Uvicorn theo `$PORT` và khai báo health check `/health`. Render mô tả biến môi trường và secret ngay trong Blueprint qua `sync: false` hoặc `generateValue: true`, đồng thời có khai báo Redis riêng. Mẫu Railway quản lý biến và Redis qua project. Agent Part 6 dùng một cấu hình Railway riêng với builder `DOCKERFILE`.
- **Cloud Run.**
  1. Cloud Build cài dependency và chạy pytest trước khi build.
  2. Docker build tạo tag theo commit SHA và tag `latest`, rồi đẩy image lên registry.
  3. Bước deploy dùng tag SHA để Cloud Run chạy đúng image từ commit đã kiểm tra.
  4. `service.yaml` mô tả cấu hình service, secret, giới hạn autoscaling và probe khởi động/liveness.

## Part 4 — API Security

- **Exercise 4.1.** Lần chạy của trợ lý trong container Linux tạm: `POST /ask` thiếu `X-API-Key` trả `401` với thông báo `Missing API key`. Thêm header với key demo hợp lệ thì trả `200`, JSON có `question: "Hello"` và `answer`.
- **Exercise 4.2.** `POST /auth/token` với tài khoản demo `student` trả `200`. Mẫu cấp JWT sau khi xác thực thông tin đăng nhập. Endpoint được bảo vệ đọc Bearer token, xác minh chữ ký và thông tin hết hạn, rồi dùng danh tính và role trong token. JWT không được ghi vào hồ sơ.
- **Exercise 4.3.** HTTP quan sát bằng urllib trên app local: request 1–10 trả `200`, request 11–20 trả `429`. Body request 11: `{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}`. Bộ giới hạn của mẫu giữ timestamp theo tài khoản trong bộ nhớ tiến trình và loại timestamp nằm ngoài cửa sổ 60 giây.
- **Exercise 4.4.** `GET /me/usage` trả `200`: 10 request, 20 input tokens, 312 output tokens, chi phí ước tính 0.00019 USD, ngân sách 1 USD và còn 0.99981 USD. Đây là số từ mock. App ước lượng token bằng hai lần số từ, nhân từng nhóm token với đơn giá input/output tương ứng rồi cộng. Mẫu kiểm ngân sách trước khi gọi mock và ghi usage sau khi có kết quả. Khi hết ngân sách theo người dùng, code trả `402`; lần chạy này chưa kích hoạt mã đó. Ở Part 6 có thể lưu bộ đếm theo key và kỳ trong Redis, đặt TTL đến hết kỳ và cập nhật nguyên tử để các worker dùng chung ngân sách.
- Rate limit chặn gọi quá dồn dập. Cost guard giới hạn chi phí tích lũy, kể cả khi từng request đều nằm trong quota tốc độ.

## Part 5 — Scaling & Reliability

- **Exercise 5.1.** Bản develop trả `GET /health → 200` với `status: "ok"` và `GET /ready → 200` với `ready: true`. Liveness cho biết tiến trình còn phục vụ probe. Readiness cho biết có thể chuyển traffic vào instance lúc này hay không.
- **Exercise 5.2.** Lần chạy của trợ lý dùng `python app.py` trong container Linux. Gửi SIGTERM khoảng 0,5 giây sau khi bắt đầu `POST /ask?question=Long%20task`. Log ghi `Shutting down`, request đang chạy vẫn trả `200 OK`, sau đó `Application shutdown complete` và tiến trình thoát mã `0`. Chờ request hoàn tất giúp người gọi nhận được response khi server đang dừng.
- **Exercise 5.3.** Client giữ `session_id`. Agent đọc và ghi history theo key `session:<id>` trong Redis. `save_session` đặt TTL 3.600 giây mỗi lần ghi. Nhiều replica đọc chung Redis; nếu chỉ lưu trong RAM, mỗi tiến trình giữ một bản riêng.
- **Exercise 5.4.** Compose chạy ba replica agent cùng Nginx và Redis. Cả ba replica healthy. Luồng thử là client → Nginx qua host :8080 → một trong ba agent :8000 → Redis. Log của cả ba replica xác nhận dùng Redis.
- **Exercise 5.5.** Script `test_stateless.py` chạy trong container Python, dùng `host.docker.internal:8080` thay `localhost:8080` trong bản truyền qua stdin. File gốc giữ nguyên. Cùng một session có **5 request** qua **3 instance** theo thứ tự `328c6c → 4ef133 → ee295f → 328c6c → 4ef133` (hậu tố của `served_by`). Endpoint history trả `200` với **10 message**, gồm 5 cặp câu hỏi và câu trả lời. Đã dừng stack sau khi lấy log.

## Part 6 — Kết quả script production readiness

Chạy trong `06-lab-complete/` và giữ nguyên output thật của `python check_production_ready.py`:

Output của lần trợ lý chạy đầy đủ `python check_production_ready.py` trên máy lab trong Ubuntu WSL2, Python 3.11.18 và Docker 29.6.1. Image được grader báo **56 MB**. `docker stop` hoàn thành trong **0,7 giây**, exit code **0**.

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
================================================================
```

## AI log

Ghi lại mỗi lần dùng AI cho code Part 6 hoặc câu trả lời; gồm câu hỏi, gợi ý nhận được, phần tự sửa và cách tự kiểm tra. Ghi cả việc dùng plan này nếu dựa vào nội dung plan để làm bài.

| Ngày | Câu hỏi / việc nhờ AI | Gợi ý nhận được | Phần tôi tự sửa / quyết định | Cách tôi tự kiểm tra |
| --- | --- | --- | --- | --- |
| 2026-11-26 | Triển khai và kiểm tra CP5 | AI sửa các TODO Part 6, chạy grader đầy đủ trong WSL2 có Docker và ghi output thật | Học viên bổ sung sau khi rà code | Grader báo PASS 12/12 và 43/43 checks passed trong lần trợ lý chạy trên máy lab |
| 2026-11-26 | Chạy CP4 và ghi kết quả | AI kiểm tra SIGTERM và session trên ba replica, rồi ghi bản nháp Part 5 | Học viên đối chiếu với mã nguồn | Số liệu trên lấy từ lần trợ lý chạy; học viên tự chạy lại để lấy output nộp |
| 2026-11-26 | Chạy kiểm tra CP3 và giải thích kết quả | AI chạy app mẫu local và soạn bản nháp về xác thực, quota, chi phí | Học viên đối chiếu bản nháp với mã nguồn | Số liệu ở Part 4 lấy từ lần trợ lý chạy; học viên tự chạy lại để lấy output nộp |
| 2026-11-26 | Chạy và ghi kết quả CP2 | AI điền bản nháp Exercise 2.1, build hai image và kiểm tra Nginx qua cổng 18080 | Học viên rà lại bản nháp | Số đo và HTTP ở trên là output lần trợ lý chạy trên máy này |
| 2026-11-26 | Điền CP1 sau khi chạy hai app mẫu | AI soạn bản nháp bảng anti-pattern và bảng so sánh, kèm số dòng để đối chiếu | Học viên bổ sung sau khi rà bản nháp | Học viên đã báo chạy CP1 trong PowerShell; cần đối chiếu và dán output của lần chạy đó |
| 2026-11-26 | Lập plan hoàn thành Day 14 theo yêu cầu lớp K5 | Tạo thứ tự CP0–CP8 và hướng dẫn lệnh / đầu ra theo checkpoint | Tôi sẽ đối chiếu với README và tự chạy từng lệnh; chưa dùng AI để viết câu trả lời hay tạo số đo | Đối chiếu checklist K5; ghi output thật khi chạy |
