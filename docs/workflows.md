# 🔄 Các luồng nghiệp vụ chi tiết (System Workflows)

Tài liệu này mô tả chi tiết tất cả các luồng nghiệp vụ và luồng dữ liệu (Data & Logic flows) trong **Hệ thống đặt lịch khám bệnh trực tuyến (Medical Appointment System)**.

---

## 👥 I. Nhóm Bệnh nhân (Patient Workflows)

### 1. Đăng ký & Đăng nhập (Authentication & Authorization)
Mô tả quy trình đăng ký tài khoản bệnh nhân mới và đăng nhập nhận JWT để phân quyền truy cập.

```mermaid
sequenceDiagram
  actor User as Người dùng
  participant Client as ReactJS Frontend
  participant Server as NodeJS Backend
  participant DB as MySQL Database

  %% Đăng ký
  Note over User, Client: Quy trình Đăng ký
  User->>Client: Nhập thông tin Đăng ký (Họ tên, Email, Mật khẩu...)
  Client->>Server: Gửi POST /api/register
  Server->>DB: Kiểm tra trùng lặp Email -> Hash mật khẩu & Lưu User
  DB-->>Server: Thành công
  Server-->>Client: Trả về đăng ký thành công (errCode: 0)

  %% Đăng nhập
  Note over User, Client: Quy trình Đăng nhập
  User->>Client: Nhập Email & Mật khẩu
  Client->>Server: Gửi POST /api/login
  Server->>DB: Kiểm tra Email tồn tại & So sánh Hash mật khẩu
  DB-->>Server: Trả về thông tin User
  Server-->>Server: Tạo JWT Access Token & Refresh Token
  Server-->>Client: Trả về JWT token & Thông tin Role (Bệnh nhân/Bác sĩ/Admin)
  Client->>Client: Lưu JWT vào Cookie/LocalStorage & phân quyền Router
```

### 2. Tìm kiếm & Đặt lịch khám (Search & Booking)
Mô tả cách bệnh nhân tìm kiếm/lọc chuyên khoa, bác sĩ, gói dịch vụ và chọn khung giờ đặt lịch.

```mermaid
sequenceDiagram
  actor Patient as Bệnh nhân
  participant Client as ReactJS Frontend
  participant Server as NodeJS Backend
  participant DB as MySQL Database

  Patient->>Client: Tìm kiếm / Lọc (theo Chuyên khoa, Bác sĩ, Gói khám, Cơ sở)
  Client->>Server: Gửi GET /api/get_all_doctor (hoặc /api/packages/search...)
  Server->>DB: Query các bản ghi thỏa mãn điều kiện lọc
  DB-->>Server: Trả về danh sách kết quả
  Server-->>Client: Render danh sách kết quả
  Patient->>Client: Chọn một Bác sĩ / Gói khám & Ngày cần khám
  Client->>Server: Gửi GET /api/get_schedule_doctor_by_date?date=...
  Server->>DB: Query danh sách khung giờ khám (Schedule) trống của Bác sĩ
  DB-->>Server: Trả về danh sách Time slots
  Server-->>Client: Hiển thị các ô thời gian (ví dụ: 8:00 - 9:00, ...)
```

### 3. Luồng Đặt lịch & Xác thực qua Email (Booking Verification)
Quy trình gửi email kích hoạt lịch hẹn để tránh tình trạng đặt lịch ảo.

```mermaid
sequenceDiagram
  actor Patient as Bệnh nhân
  participant Client as ReactJS Frontend
  participant Server as NodeJS Backend
  participant DB as MySQL Database
  participant Mail as Gmail SMTP Service

  Patient->>Client: Điền thông tin đặt lịch & xác nhận đặt
  Client->>Server: Gọi POST /api/patient-book-appointment
  Server->>DB: Tạo bản ghi Booking (Trạng thái: PENDING) & Sinh token xác thực
  Server->>Mail: Gửi email chứa Link xác thực (kèm token)
  Mail-->>Patient: Nhận email và click Link xác thực
  Patient->>Server: Gọi GET /api/verify-book-appointment?token=...
  Server->>DB: Xác thực token & Cập nhật Booking (Trạng thái: CONFIRMED)
  Server-->>Patient: Hiển thị trang xác thực thành công
```

### 4. Tự động hóa Thanh toán VietQR & Casso Webhook (VietQR Payment Flow)
Luồng thanh toán tự động, nhận dữ liệu giao dịch thời gian thực và đồng bộ Socket.io lên màn hình Client.

```mermaid
sequenceDiagram
  actor Patient as Bệnh nhân
  participant Client as ReactJS Frontend
  participant Server as NodeJS Backend
  participant DB as MySQL Database
  participant VietQR as VietQR API
  participant Casso as Casso Gateway
  participant Bank as Ngân hàng (MBBank...)

  Patient->>Client: Chọn thanh toán lịch khám
  Client->>Server: Yêu cầu thông tin thanh toán
  Server->>VietQR: Gọi API sinh QR Code tự động (kèm số tiền & cú pháp chuyển khoản)
  VietQR-->>Server: Trả về hình ảnh mã QR
  Server-->>Client: Hiển thị QR Code cho bệnh nhân
  Patient->>Bank: Quét QR & Thực hiện chuyển khoản trên App Mobile Banking
  Bank->>Casso: Thông báo biến động số dư (qua SMS/API)
  Casso->>Server: Gọi Webhook POST /api/casso/webhook (Gửi thông tin giao dịch)
  Server->>DB: Đối chiếu cú pháp giao dịch -> Cập nhật trạng thái Booking (Trạng thái: PAID)
  Server-->>Client: Realtime đồng bộ giao diện qua Socket.io (Đã Thanh Toán)
```

### 5. Khảo sát & Đánh giá sức khỏe (Health Assessment Flow)
Bệnh nhân trả lời bộ câu hỏi trắc nghiệm để nhận đánh giá rủi ro tim mạch/tiêu hóa sơ bộ và gợi ý chuyên khoa phù hợp.

```mermaid
sequenceDiagram
  actor Patient as Bệnh nhân
  participant Client as ReactJS Frontend
  participant Server as NodeJS Backend
  participant DB as MySQL Database

  Patient->>Client: Vào mục "Đánh giá sức khỏe"
  Client->>Server: Gọi GET /api/get_all_questions
  Server->>DB: Query danh sách câu hỏi trắc nghiệm
  DB-->>Server: Trả về bộ câu hỏi & đáp án (kèm điểm số tương ứng)
  Server-->>Client: Hiển thị giao diện khảo sát
  Patient->>Client: Chọn các đáp án trả lời & Nhấn "Nộp kết quả"
  Client->>Server: Gọi POST /api/submit-assessment (Gửi mảng câu trả lời)
  Server-->>Server: Tính toán tổng điểm & phân loại mức độ rủi ro sức khỏe
  Server->>DB: Lưu lịch sử đánh giá (userId, tổng điểm, phân loại)
  Server-->>Client: Trả về kết quả phân loại & Gợi ý chuyên khoa thích hợp
```

---

## 🩺 II. Nhóm Bác sĩ (Doctor Workflows)

### 6. Đăng ký Ca trực hàng loạt (Bulk Schedule Creation)
Bác sĩ hoặc Admin đăng tải lịch làm việc của bác sĩ theo ngày và các ca trực.

```mermaid
sequenceDiagram
  actor Doctor as Bác sĩ (hoặc Admin)
  participant Client as ReactJS Frontend
  participant Server as NodeJS Backend
  participant DB as MySQL Database

  Doctor->>Client: Chọn ngày & Chọn các ca trực (Ví dụ: 8:00, 9:00, 10:00)
  Client->>Server: Gọi POST /api/bulk_create_schedule (doctor_id, date, list_time_slots)
  Server-->>Server: Kiểm tra trùng lặp lịch khám của bác sĩ trong database
  Server->>DB: BULK INSERT/UPDATE vào bảng Schedule
  DB-->>Server: Lưu thành công
  Server-->>Client: Thông báo tạo lịch trực thành công
```

### 7. Khám bệnh & Gửi đơn thuốc điện tử (Prescription / Remedy Flow)
Bác sĩ hoàn tất khám và tải lên đơn thuốc/hóa đơn để gửi tự động cho bệnh nhân qua email.

```mermaid
sequenceDiagram
  actor Doctor as Bác sĩ
  participant Client as ReactJS Frontend
  participant Server as NodeJS Backend
  participant DB as MySQL Database
  participant Mail as Gmail SMTP Service
  actor Patient as Bệnh nhân

  Doctor->>Client: Chọn bệnh nhân khám -> Nhập kết quả & Kê đơn thuốc
  Client->>Server: Gửi POST /api/send-remedy (kèm file đơn thuốc PDF/ảnh)
  Server->>DB: Cập nhật trạng thái Booking (Trạng thái: DONE)
  Server->>Mail: Gửi Email kèm file đính kèm đơn thuốc (Nodemailer)
  Mail-->>Patient: Nhận Email thông báo kết quả & đơn thuốc (PDF)
```

---

## 💬 III. Nhóm Giao tiếp Realtime (Real-time Messaging)

### 8. Chat Real-time giữa Bệnh nhân và Bác sĩ/Tư vấn viên (Socket.io Chat)
Quy trình trao đổi trực tuyến và lưu trữ lịch sử tin nhắn.

```mermaid
sequenceDiagram
  actor Patient as Bệnh nhân
  actor Doctor as Bác sĩ/Tư vấn viên
  participant ClientP as Client Bệnh nhân
  participant Socket as Socket.io Server (NodeJS)
  participant ClientD as Client Bác sĩ
  participant Server as NodeJS Backend
  participant DB as MySQL Database

  Patient->>ClientP: Nhập tin nhắn & Nhấn gửi
  ClientP->>Socket: Emit sự kiện "send_message" (senderId, receiverId, content)
  Socket->>ClientD: Emit realtime "receive_message" nếu Bác sĩ online
  ClientP->>Server: Gọi POST /api/save-msg (Lưu lịch sử tin nhắn)
  Server->>DB: INSERT bản ghi tin nhắn mới vào database
  Doctor->>ClientD: Nhập phản hồi & Nhấn gửi
  ClientD->>Socket: Emit sự kiện "send_message"
  Socket->>ClientP: Emit realtime "receive_message"
```

---

## 🤖 IV. Nhóm Trí tuệ nhân tạo (AI Chatbot Flows)

### 9. Luồng xử lý Chatbot AI (PhoBERT Classifier + FAISS + Gemini RAG)
Cách hệ thống lọc ý định câu hỏi y học và truy xuất tài liệu trước khi trả lời.

```mermaid
mermaid
graph TD
  Start(["Người dùng nhập câu hỏi"]) --> PhoBERT{"Bộ lọc PhoBERT<br>(Medical Intent Classifier)"}
  
  %% Lộ trình không liên quan y tế
  PhoBERT -->|Nhãn 0: Ngoài lề| Suggest["Suggestion Engine (Gemini)"]
  Suggest -->|Đề xuất 1 câu hỏi y tế tương tự| Output0["Hiện câu trả lời & Gợi ý câu hỏi y khoa"]

  %% Lộ trình y tế
  PhoBERT -->|Nhãn 1: Y tế| VectorSearch["Tìm kiếm Vector (FAISS DB)"]
  VectorSearch -->|"Lấy thông tin ngữ cảnh<br>(Bác sĩ, Chuyên khoa, Lịch khám)"| Context["Tạo Prompt tích hợp Context"]
  Context --> GeminiLLM["Gemini 2.5 Flash API"]
  GeminiLLM -->|"Sinh câu trả lời y khoa chuẩn xác"| Output1["Phản hồi câu trả lời cho người dùng"]

  Output0 --> End(["Kết thúc lượt chat"])
  Output1 --> End
```

### 10. Luồng Đồng bộ dữ liệu Y tế sang FAISS Vector DB (AI Data Sync Flow)
Tự động đồng bộ các thay đổi nghiệp vụ (Bác sĩ mới, Gói khám mới...) sang Vector DB để làm giàu tri thức Chatbot.

```mermaid
sequenceDiagram
  actor Admin as Quản trị viên
  participant Client as ReactJS Frontend
  participant Server as NodeJS Backend
  participant DB as MySQL Database
  participant Chatbot as Flask AI Microservice
  participant FAISS as FAISS Vector DB

  Admin->>Client: Tạo mới/Cập nhật thông tin (Bác sĩ, Chuyên khoa, Gói khám)
  Client->>Server: Gửi request lưu thay đổi
  Server->>DB: Lưu cập nhật vào cơ sở dữ liệu MySQL
  Note over Server, Chatbot: Bộ đồng bộ chạy định kỳ hoặc trigger thủ công
  Server->>Chatbot: Đồng bộ dữ liệu y khoa qua API `/api/sync-data`
  Chatbot->>Chatbot: Khởi chạy Embedding các trường dữ liệu y khoa mới
  Chatbot->>FAISS: Lưu/Cập nhật các Vector Embeddings vào Vector DB FAISS
```
