# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Hoàng Anh Tú
- **MSSV:** 2A202602643
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/ttien0181/K4-L3-DAY13-HoangAnhTu-2A202602643-Monitoring-LLMOps.git
- **Commit SHA cuối:** làm sao mà điền được
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602643`

---

## CP0 — Baseline (ghi trước khi sửa code)

Thời điểm chạy baseline: 2026-09-30

| Chỉ tiêu | Giá trị baseline |
|---|---|
| Health check (`/health`) | `ok: true`, `tracing_enabled: true` |
| `data/logs.jsonl` — tổng số bản ghi | 21 records |
| `validate_logs.py` — điểm tổng | **30/100** |
| Missing required fields (`ts`, `level`, …) | 20/21 records |
| Missing enrichment (`user_id_hash`, …) | 20/21 records |
| Correlation ID propagation (unique IDs) | 0 |
| PII scrubbing | PASSED (0 leaks) |
| `validate_dashboard.py` — panels hợp lệ | 6/6 |
| `pytest` | 22 passed |
| Langfuse traces | Có trace (status `MISSING` trong `load_test.py`) |

Ghi chú thêm:
- `load_test.py` trả về status `MISSING` cho tất cả request — do Langfuse prompt `day13-chat` / label `production` chưa được tạo trong project, API fallback về prompt mặc định nên trace không đánh dấu được là `HIT`.
- Baseline 30/100 được lấy trực tiếp từ output `validate_logs.py`, là điểm tham chiếu cho các bước CP1 trở đi.

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Từ 20/21 records thiếu field → 0 |
| `validate_dashboard.py` | 6/6 | 6/6 | Panel hợp lệ không đổi |
| `pytest` | 22 passed | 24 passed | Thêm 2 test PII (CCCD, credit card) |
| Số traces hợp lệ | 0 | ≥10 | Cấu trúc day13-agent-request → lab-agent-run → retrieval + generation |
| Số PII leak | 0 | 0 | Email, SĐT VN, CCCD, thẻ tín dụng đều được redact |
| Latency P95 / TTFT P95 | ~570ms / ~50ms | ~570ms / ~50ms | Baseline ổn định, challenge đẩy P95 lên ~2900ms |
| Retrieval success rate | 100% | 100% | Baseline không có lỗi retrieval |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware `CorrelationIdMiddleware` kiểm tra header `x-request-id`; nếu không có, sinh ID dạng `req-<8-hex>` bằng `uuid.uuid4().hex[:8]`. Bind vào `structlog` contextvars qua `bind_contextvars(correlation_id=...)` và lưu vào `request.state.correlation_id`. Tất cả các log sau đó trong request đều tự động có `correlation_id`.
- **Các metadata được ghi vào structured log:** `user_id_hash` (SHA-256 rút gọn 12 ký tự), `session_id`, `feature`, `model`, `env`, `ts`, `level`, `service`, `event`. Response log thêm `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` chạy sau `TimeStamper` và trước `JsonlFileProcessor`. Redact pattern: email, SĐT VN (`+84`/`0` + 9 chữ số), CCCD (12 chữ số liên tiếp), thẻ tín dụng (16 chữ số, có thể có dấu `-` hoặc space).
- **Cách kiểm chứng kết quả:** `python scripts/validate_logs.py` cho điểm 100/100, PII leaks = 0. Chụp `data/logs.jsonl` thấy `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]`, `[REDACTED_CREDIT_CARD]`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Mở Langfuse → Tracing → project `day13-k4-l3b-2A202602643`, lọc theo time range, thấy ≥10 trace tên `day13-agent-request` với correlation_id tôi đã gửi (`req-xxxxxxxx`).
- **Cấu trúc root/retrieval/generation observations:** Root trace `day13-agent-request` → agent `lab-agent-run` → retriever `retrieval` (tìm tài liệu) + generation `generation` (gọi LLM). Mỗi observation dùng decorator `@observe` với `capture_input=False`, `capture_output=False` để tránh PII.
- **Cách nối trace với log:** Cả trace và log đều có `correlation_id` (ví dụ `req-test01`). Log có `ts` UTC, Langfuse hiển thị giờ Việt Nam (+7h).
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1 với labels `baseline` + `production` + `latest`
- **Version/label candidate:** v2 với labels `candidate` + `latest`
- **Trace ID của mỗi version:** (ghi từ Langfuse — trace của `req-baseline01` dùng v1, trace của `req-candidate01` dùng v2)
- **Cách promote và rollback `production`:** Promote: trên Langfuse Prompts → v2 → Promote → chọn label `production`. Rollback: v1 → Promote → chọn label `production`. Mỗi lần đổi label restart API.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** (1) Latency: P50/P95/P99 + TTFT P95, ngưỡng 3000ms; (2) Traffic: requests/min; (3) Errors: error rate % + retrieval success %, ngưỡng 2% và 90%; (4) Cost: USD/min, ngưỡng 2.5 USD; (5) Tokens: input/output tokens, ngưỡng 50000; (6) Quality: avg quality score, ngưỡng 0.75.
- **SLO và lý do chọn:** SLO `fast_successful_requests`: 99.5% request thành công với latency ≤ 3000ms trong 28 ngày. Baseline P95 ~570ms, P99 ~1250ms, nên ngưỡng 3000ms hợp lý.
- **Cách tính error budget:** Error budget = 100% - 99.5% = 0.5%. Với ~200 request trong buổi lab, 0.5% ≈ **1 request**. Tối đa 1 request được phép chậm >3000ms hoặc lỗi trong 28 ngày.
- **Ba alert và runbook tương ứng:**
  1. `HighLatencyP95` — p95(latency_ms) > 3000ms trong 5m → warning → runbook `docs/alerts.md#alert-1`
  2. `HighErrorRate` — error_rate_pct > 2 trong 5m → critical → runbook `docs/alerts.md#alert-2`
  3. `LowRetrievalSuccess` — retrieval_success_rate_pct < 90 trong 5m → warning → runbook `docs/alerts.md#alert-3`

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-30 04:53–04:55 UTC
- **Triệu chứng từ metrics:** Dashboard latency panel cho thấy P95 tăng lên ~2900ms (sát ngưỡng SLO 3000ms), P99 vượt ngưỡng ~3200ms. Traffic giảm dần từ 10 req/min xuống ~3 req/min. Error rate vẫn 0%, retrieval success 100%.
- **Log line và correlation ID liên quan:** 
  - `req-6e31315d` — latency 3415ms, session `k4-l3b-challenge-s01`
  - `req-8f55c8ac` — latency 2653ms, session `k4-l3b-challenge-s05`
- **Trace ID và span gây ảnh hưởng:** Trace `545807187918b904340889a52298d923` — span `retrieval` chạm 2.50s, span `generation` chỉ 151ms. Root span `lab-agent-run` tổng 3.42s.
- **Root cause:** Incident `rag_slow` được kích hoạt, làm RAG retrieval chậm 2.5s (thay vì gần như tức thời như baseline). Request có `feature=monitoring` bị ảnh hưởng vì corpus của feature này có kết quả khớp từ khóa "monitoring" nhưng incident đã chèn `time.sleep(2.5)` vào hàm `retrieve()`.
- **Fix action:** `python scripts/inject_incident.py --scenario rag_slow --disable` để tắt incident, sau đó restart API. Latency trở về ~400ms.
- **Preventive measure:** 
  1. Đã thêm alert `HighLatencyP95` (p95(latency_ms) > 3000ms trong 5m) để phát hiện sớm khi retrieval chậm.
  2. Giám sát span `retrieval` trên Langfuse, đặt threshold 2000ms cho span này.
  3. Trong runbook, kiểm tra dashboard latency → lọc log theo correlation_id → mở trace xem span retrieval có bất thường không.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Dùng `@observe` decorator trên `retrieve()` và `FakeLLM.generate()` để tạo child observation, thay vì quản lý thủ công span. Lý do: cách này tự động nhận context từ parent trace, ít lỗi hơn và test `test_agent_prompt_trace.py` yêu cầu API v4.
- **Một lỗi/blocker đã gặp:** `Langfuse.update_current_generation()` không nhận keyword `usage` và `cost`. Giải quyết: chuyển tất cả vào `metadata`.
- **Cách tìm nguyên nhân và xử lý:** Xem dashboard → phát hiện latency tăng → lọc log → tìm correlation_id → mở trace trên Langfuse → thấy span retrieval chạm 2.5s → xác định root cause là incident `rag_slow`.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics cho biết triệu chứng (latency tăng), logs giúp tìm request cụ thể (correlation_id), traces chỉ ra bước gây lỗi (retrieval span chậm).
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version cho phép thử nghiệm prompt mới mà không ảnh hưởng production. Token/cost giúp theo dõi chi phí mô hình. SLO đặt ngưỡng chất lượng, rollback nhanh khi prompt mới gây regression.
- **Điều quan trọng nhất đã học:** Một hệ thống LLM production cần monitoring đầy đủ: log có cấu trúc + correlation ID để debug, trace để xem từng bước, dashboard để có cái nhìn tổng quan, và alert để phản ứng nhanh.
- **Hạn chế hoặc phần chưa hoàn thành:** Chưa thực sự deploy production (chỉ chạy local), challenge chưa có nếu coach chưa mở.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
