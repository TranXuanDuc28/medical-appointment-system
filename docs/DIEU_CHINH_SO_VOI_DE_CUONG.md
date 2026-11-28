# ĐIỀU CHỈNH SO VỚI ĐỀ CƯƠNG (NGUỒN DUY NHẤT CHO CÁC CHỖ KHÁC ĐỀ CƯƠNG)

> Cập nhật: 27/11/2026. Đề cương đã ký (`Decuongchitiet.md` và 2 file PDF) **giữ nguyên làm bản gốc**; file này ghi rõ chỗ nào hệ thống thực tế **khác** đề cương, vì sao, và con số thật. Khi viết báo cáo hoặc trả lời hội đồng, **dùng số liệu ở đây**, không dùng số trong đề cương.
> Mỗi chỗ lệch đều đi cùng một lý do kỹ thuật và vẫn đúng hướng đề tài (đặt lịch + hàng đợi + ML dự đoán thời gian). Số liệu ML lấy từ `medical-appointment-system/ai-service/reports/`.

## 1. Thống nhất các mâu thuẫn giữa các tài liệu

| # | Nội dung | Các chỗ từng nói khác nhau | **Chốt (dùng cái này)** |
|---|---|---|---|
| 1 | Số bản ghi dataset | "10.000" (đề cương) / "hơn 100.000" (kế hoạch, mục 2-7 và bản nháp cũ) | **10.000 dòng, 26 cột** (đã đếm trên file `smart_hospital_appointment_dataset.csv`) |
| 2 | Dataset là "thực tế"? | "tập dữ liệu y tế thực nghiệm / ca khám thực tế" | **Dataset công khai trên Kaggle, có dấu hiệu tổng hợp** (thời gian chờ gần như chỉ phụ thuộc mức độ nặng + nhiễu). Không gọi là dữ liệu thực tế. |
| 3 | Mục tiêu sai số | "MAE ≤ 2.5 phút" (đề cương) / "dưới 2–3 phút" (kế hoạch) | Xem mục 2: **mục tiêu mới là "giảm sai số so với baseline"**, vì mục tiêu cũ không đạt được với đặc trưng hợp lệ |
| 4 | Công nghệ backend | "Spring Boot / NestJS", "PostgreSQL/MySQL", "gRPC", "Redis Pub-Sub" | **Node.js + Express, Sequelize, MySQL, Socket.io, BullMQ + Redis** (Redis tuỳ chọn, có chế độ dự phòng không Redis). Không dùng Spring Boot, NestJS, gRPC, PostgreSQL. |
| 5 | Framework dịch vụ Python | "FastAPI" cho cả hai | **AI Service (dự đoán + phân loại triệu chứng): FastAPI. Chatbot tư vấn (có sẵn từ trước): Flask.** |
| 6 | "Không phụ thuộc API thương mại (OpenAI/Gemini)" | Đề cương mục 3b | Phạm vi lại câu: **các module cốt lõi (dự đoán thời gian, phân loại triệu chứng, hàng đợi, ETA) tự huấn luyện/tự xây, không gọi API ngoài.** Chatbot tư vấn là **module phụ có sẵn từ trước**, dùng Gemini; hệ thống vẫn chạy đủ chức năng đặt lịch + hàng đợi khi tắt chatbot. |
| 7 | Ca làm việc | "07:30–11:30" / "07:00–11:30" | Theo khung giờ trong DB: **sáng 08:00–12:00 (T1–T4), chiều 13:00–17:00 (T5–T8)**, mỗi khung 1 giờ |
| 8 | Hồ sơ lịch sử khám | `histories` | Bảng `medical_records` (1 hồ sơ/lịch hẹn). DB chuẩn mới ở `DB_ThietKe_Moi.md` (**schema v2**) — `medical-appointment-system/docs/database_schema.md` mô tả schema cũ, không dùng nữa |
| 9 | Timeline | Bản nháp cũ 10 tuần (từ 20/10) vs bản chính 12 mốc | **Bản chính 12 mốc (28/09–20/12)**; bản nháp cũ đã chuyển vào `_luu_tru/` và đánh dấu DEPRECATED |

## 2. Mục tiêu ML: đề cương vs thực tế

Đề cương cam kết một mô hình dự đoán thời lượng khám đạt MAE ≤ 2.5 phút và R² ≥ 0.85. Khi thực hiện, phát hiện:

1. **Dataset Kaggle không có cột thời lượng khám**, chỉ có `waiting_time_minutes` (thời gian chờ).
2. Trên bài toán thời gian chờ, **chỉ `severity_level` dự đoán được**; tuổi, giới, bệnh nền, tỉnh, bảo hiểm, tháng, thứ… tương quan ≈ 0 (nhiễu). Trần hiệu năng với đặc trưng hợp lệ: **MAE ≈ 7.7 phút, R² ≈ 0.64**.
3. Có thể đạt R² 0.90 / MAE 3.4 nếu dùng thêm các cột "sau khám", nhưng đó là **rò rỉ dữ liệu** (những cột đó chưa tồn tại lúc cần dự đoán) nên **bị loại**.

→ Mục tiêu "MAE ≤ 2.5 và R² ≥ 0.85" **không đạt được một cách hợp lệ** trên dataset này. Thay bằng mục tiêu đo được, có khoảng tin cậy:

| Thành phần | Dữ liệu | Kết quả (tập test độc lập) |
|---|---|---|
| Thời gian chờ (nghiên cứu trên Kaggle) | Kaggle, 10.000 dòng | MAE **7.7 phút** vs 12.8 của "đoán trung bình": **giảm 39.7%** (95% CI 7.53–7.94). Mô hình chọn: *trung bình theo mức nặng* — XGBoost/Random Forest **không hơn đáng kể** |
| **Thời lượng khám (dùng cho ETA hàng đợi)** | **Mô phỏng có kiểm soát** (giả định ghi trong `reports/duration_model.md`) | Chọn bằng CV 5-fold theo nhóm: **XGBoost (log)**. MAE từng ca **3.1 phút** vs 6.5 (cố định 15'), R² 0.68; **sai số ETA giảm 65.7%** (22.7 → 7.8 phút); khoảng dự đoán p10–p90 phủ 80.4% |
| Phân loại triệu chứng → chuyên khoa | **Tự xây** bộ triệu chứng tiếng Việt (chưa bác sĩ kiểm định) | Top-1/Top-3: **71% / 86%** trên test chia theo nhóm (bi quan); **94% / 97%** trên tập ngoài do chính nhóm viết (lạc quan). Luật cấp cứu chạy **trước** mô hình. Chỉ **gợi ý**, không chẩn đoán |

Hệ quả cần nói thật khi bảo vệ:
- Mô hình thời lượng khám hiện huấn luyện trên **dữ liệu mô phỏng**, nên con số 3.1 phút / −65.7% là **kết quả trên mô phỏng**, chưa phải trên bệnh viện thật.
- Hệ thống **tự ghi log thật** (`queue_events`, `ai_predictions`). Khi có **≥ 200 ca thật**: `python -m ai_service export-real` rồi `train-duration --source real`, so sánh lại với bản mô phỏng.
- Cơ chế **dự phòng nhiều tầng**: AI lỗi/chậm → ngắt mạch → ETA dùng trung bình lịch sử của bác sĩ → mặc định 15 phút. Mỗi ETA ghi rõ `basis` = `ml` / `history` / `default`.
- Ngoài ra có **đối sánh dự đoán và thực tế** (`GET /api/ai/metrics`): MAE của AI so với baseline trên các ca thật đã khám xong.

## 3. Trạng thái thực hiện (27/11/2026)

> Toàn bộ code nằm trên các Pull Request đang mở (chưa merge vào `main`). Tình trạng cập nhật theo PR, xem GitHub.

| Hạng mục trong đề cương | Trạng thái | Ghi chú |
|---|---|---|
| Xác thực, RBAC, bảo mật, nhật ký audit, refresh token | **Xong** | Phân quyền theo permission, cấu hình trong DB; default-deny |
| CSDL schema v2 | **Xong** | `DB_ThietKe_Moi.md` |
| Đặt lịch, chống đặt trùng slot | **Xong** | Transaction + khoá dòng; có test đặt đồng thời |
| Lõi hàng đợi (check-in, gọi số, khẩn cấp, dời lượt, vắng mặt, realtime) | **Xong (backend)** | `backend/QUEUE_ENGINE.md`; số thứ tự không trùng khi check-in song song |
| ETA bằng ML + dự phòng + đối sánh AI | **Xong** | `backend/AI_INTEGRATION.md` |
| Phân loại triệu chứng gợi ý chuyên khoa | **Xong (backend/AI)** | Chưa có ô nhập trên giao diện |
| Nhắc hẹn 24h/2h, cảnh báo sắp đến lượt, API thông báo | **Xong (backend)** | `backend/REMINDERS.md`; chưa có email/SMS, mới INAPP + push + socket |
| Cân bằng tải cho bệnh nhân vãng lai | **Xong một phần** | Tự chọn bác sĩ chờ ngắn nhất; **chưa có** chuyển vé giữa các phòng khi quá tải |
| Bản đồ nhiệt phòng khám (Heatmap), thống kê Admin | **Chưa làm** | Cần API tổng hợp + giao diện |
| Giao diện: e-Ticket QR, Live Queue Tracker, Cổng bác sĩ, TV sảnh, quản lý phòng, quản trị RBAC | **Chưa làm** (phần Lành) | Frontend mới có bản sửa tương thích backend v2 |
| TV sảnh phát loa gọi số tiếng Việt (Text-to-Speech) | **Chưa làm** | Backend đã phát sự kiện `TICKET_CALLED` kèm câu đọc tiếng Việt; còn trình phát phía frontend |
| Docker compose, triển khai | **Chưa làm** | |
| Đo độ trễ WebSocket, kiểm thử 100–200 ca | **Chưa làm** | Hiện có test tự động (backend ~65 test, AI 107 test) và script smoke |

## 4. Việc tài liệu còn lại
- Viết lại `README.md` gốc theo hiện trạng (hiện còn mô tả kiểu BookingCare).
- Cập nhật hoặc đánh dấu cũ `medical-appointment-system/docs/*.md` (viết trước khi đổi sang schema v2).
- Xoá cột/mô tả lỗi thời trong báo cáo khoá luận khi viết chương 4–5 theo số liệu ở mục 2.
