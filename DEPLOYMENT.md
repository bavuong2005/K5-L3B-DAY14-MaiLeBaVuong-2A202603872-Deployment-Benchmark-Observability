# Deployment — CP6

- Nền tảng: Render.
- Service: agent trong `06-lab-complete/`, build bằng Dockerfile, health check `/health`.
- URL public: https://k5-day14-agent-enmo.onrender.com
- Trạng thái: agent đã deploy và phản hồi trên Render.

## Thiết lập

Deploy dùng Render Blueprint `06-lab-complete/render.yaml` với Docker context `06-lab-complete/`. Blueprint tự sinh `AGENT_API_KEY`, đặt `REDIS_URL` từ kết nối nội bộ của Key Value và đặt `ENVIRONMENT=production`. App đọc `PORT` do Render cấp.

## Kiểm tra public URL

Trong PowerShell, nhập URL và API key, rồi ghi lại bốn mã HTTP theo thứ tự:

```powershell
$base = (Read-Host 'URL public').TrimEnd('/')
$key = Read-Host 'API key' -AsSecureString
$headers = @{ 'X-API-Key' = [System.Net.NetworkCredential]::new('', $key).Password }
curl.exe -sS -o NUL -w "%{http_code}\n" "$base/health"
curl.exe -sS -o NUL -w "%{http_code}\n" "$base/ready"
'{"question":"Hello"}' | curl.exe -sS -o NUL -w "%{http_code}\n" "$base/ask" -H "Content-Type: application/json" --data-binary "@-"
(Invoke-WebRequest -UseBasicParsing -Uri "$base/ask" -Method Post -ContentType 'application/json' -Body '{"question":"Hello"}' -Headers $headers).StatusCode
Remove-Variable key,headers
```

Tôi chạy các lệnh trên trong PowerShell ngày 26/11/2026:

| Request | HTTP |
| --- | --- |
| `GET /health` | 200 |
| `GET /ready` | 200 |
| `POST /ask` thiếu API key | 401 |
| `POST /ask` có API key hợp lệ | 200 |

## Bằng chứng

- [Dashboard và sự kiện deploy thành công](screenshots/dashboard.png).
- [Log agent đang chạy](screenshots/running.png).
- [Bốn mã HTTP trong PowerShell, API key đã che](screenshots/test.png).
