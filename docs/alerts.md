# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-2A202602643`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: SLO `fast_successful_requests` — yêu cầu `latency_ms <= 3000`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng nhận câu trả lời chậm hơn mức chấp nhận được, giảm trải nghiệm
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency panel để xác nhận P95/P99 tăng và khoảng thời gian xảy ra.
  2. Lọc `data/logs.jsonl` trong khoảng đó, tìm `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, xem span `retrieval` hay `generation` chiếm thời gian.
- Mitigation tạm thời: nếu do prompt mới → rollback prompt về production cũ; nếu do retrieval chậm → tạm tắt incident `rag_slow` hoặc giảm tải; nếu do LLM → cân nhắc giảm cường độ load test.
- Owner: `student-2A202602643`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: guardrail `error_rate_pct_max: 2`
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` trong 5 phút
- Ảnh hưởng tới người dùng: nhiều request trả về 500, người dùng không nhận được câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard errors panel để xác nhận error rate tăng và retrieval success có giảm không.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy `correlation_id` của các request `request_failed`.
  3. Mở trace cùng `correlation_id` trên Langfuse, xem span nào báo lỗi (`tool_success: false` hoặc exception).
- Mitigation tạm thời: nếu do tool fail → tạm tắt incident `tool_fail`; nếu do prompt lỗi → rollback prompt; nếu do cấu hình sai → khôi phục config và restart API.
- Owner: `student-2A202602643`

## Alert 3

- Tên: `LowRetrievalSuccess`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: guardrail `retrieval_success_rate_pct_min: 90`
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90` trong 5 phút
- Ảnh hưởng tới người dùng: RAG không trả về context phù hợp, câu trả lời thiếu thông tin hoặc chung chung
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard errors panel, xem retrieval success % có giảm xuống dưới 90 không.
  2. Lọc `data/logs.jsonl` trong khoảng đó, tìm request có `tool_success: false` hoặc `error_type: RuntimeError`.
  3. Mở trace cùng `correlation_id` trên Langfuse, xem span `retrieval` có thời gian cao hay báo lỗi.
- Mitigation tạm thời: nếu do vector store timeout → restart service hoặc tạm tắt incident `tool_fail`; nếu do rag_slow → kiểm tra network/corpus; nếu do prompt không phù hợp → rollback prompt.
- Owner: `student-2A202602643`
