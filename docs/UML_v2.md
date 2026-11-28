# SƠ ĐỒ UML HỆ THỐNG (BẢN v2 – ĐỐI CHIẾU VỚI MÃ NGUỒN)

> **Đây là bộ sơ đồ chính thức, thay thế** `usecase_diagram.md`, `class_diagram.md`, `sequence_diagrams.md`, `activity_diagrams.md` (vẽ cho hệ thống trước khi có hàng đợi, AI, nhắc hẹn và schema v2; các tệp đó giữ lại để tham khảo).
> Cập nhật 28/11/2026 theo mã nguồn: schema `backend/src/migrations/20261201000000-baseline-schema.js`, máy trạng thái `backend/src/services/queue/queueRules.js`, phân quyền `backend/src/config/permissions.js`, `accessRules.js`.
> Viết bằng **Mermaid** (GitHub, VS Code và draw.io đều hiển thị được: draw.io chọn *Arrange → Insert → Advanced → Mermaid*).
> Những điểm **chưa làm** được ghi rõ ở từng sơ đồ, không vẽ như thể đã có.

Mục lục: [1. Kiến trúc](#1-kiến-trúc-tổng-thể) · [2. Use case](#2-use-case-theo-vai-trò) · [3. ERD](#3-erd-schema-v2) · [4. Lớp nghiệp vụ](#4-sơ-đồ-lớp-lớp-nghiệp-vụ-chính) · [5. Máy trạng thái](#5-máy-trạng-thái) · [6. Tuần tự](#6-sơ-đồ-tuần-tự) · [7. Hoạt động](#7-sơ-đồ-hoạt-động)

---

## 1. Kiến trúc tổng thể

```mermaid
flowchart LR
  subgraph Client["Trình duyệt / thiết bị"]
    WEB["Web React<br/>(bệnh nhân, nhân viên, bác sĩ, admin)"]
    TV["Màn hình TV sảnh<br/>(tài khoản R8)"]
  end
  subgraph Server["Backend Node.js / Express 5"]
    API["REST API + RBAC<br/>(accessRules, default-deny)"]
    SIO["Socket.io<br/>(xác thực JWT)"]
    QE["Queue Engine<br/>queueService / queueRules / queueEta<br/>queueBalance / queueAnalytics"]
    BK["bookingService<br/>(giữ chỗ, khoá dòng)"]
    SCH["Bộ lập lịch nền<br/>nhắc hẹn · quét giữ chỗ · tự đánh vắng mặt"]
    AIC["aiClient<br/>(timeout + ngắt mạch)"]
  end
  DB[("MySQL 8<br/>37 bảng")]
  RD[("Redis<br/>BullMQ – tuỳ chọn")]
  AI["AI Service<br/>Python / FastAPI<br/>thời lượng khám · phân loại triệu chứng"]
  CB["Chatbot Flask<br/>RAG + Gemini<br/>(module phụ)"]
  EXT["Email (SMTP) · FCM · PayOS/Casso"]

  WEB -->|HTTP| API
  WEB <-->|realtime| SIO
  TV <-->|realtime| SIO
  WEB -->|HTTP| CB
  API --> QE
  API --> BK
  QE --> DB
  BK --> DB
  QE -->|sự kiện sau COMMIT| SIO
  SCH --> QE
  SCH --> RD
  SCH --> EXT
  QE --> AIC
  API --> AIC
  AIC -->|HTTP, có token| AI
  API --> EXT
  CB -->|đồng bộ dữ liệu| API
```

Nguyên tắc: **AI Service và Redis chỉ là phần tăng cường** – chết thì hệ thống vẫn chạy (ETA quay về trung bình lịch sử hoặc 15 phút; nhắc hẹn chạy bằng `setInterval`). Chatbot độc lập, dùng Gemini nên không thuộc phần "tự huấn luyện" của đề cương.

---

## 2. Use case theo vai trò

Tám vai trò (`reference_codes` nhóm `ROLE`): R1 Admin, R2 Bác sĩ, R3 Bệnh nhân, R4 Thu ngân, R5 Lễ tân, R6 Điều dưỡng, R7 Điều phối viên, R8 Thiết bị TV. Quyền thật nằm trong `rbac_role_permissions`, admin chỉnh được; sơ đồ dưới ứng với cấu hình mặc định.

### 2.1 Bệnh nhân (R3) và khách

```mermaid
flowchart LR
  P(["Bệnh nhân"])
  G(["Khách chưa đăng nhập"])
  subgraph UC["Hệ thống đặt lịch và hàng đợi"]
    U1(["Đăng ký / Đăng nhập"])
    U2(["Tìm bác sĩ, chuyên khoa, gói khám, cơ sở, cẩm nang"])
    U3(["Gợi ý chuyên khoa từ triệu chứng (AI)"])
    U4(["Đặt lịch khám"])
    U5(["Xác nhận lịch qua email"])
    U6(["Huỷ lịch của mình"])
    U7(["Check-in khi đến khám"])
    U8(["Xem số thứ tự, vị trí, thời gian chờ"])
    U9(["Xin dời lượt"])
    U10(["Nhận nhắc hẹn và cảnh báo sắp đến lượt"])
    U11(["Xem lịch sử khám và đơn thuốc"])
    U12(["Chat với bác sĩ"])
    U13(["Hỏi chatbot tư vấn"])
    U14(["Làm bài đánh giá sức khoẻ"])
    U15(["Đánh giá sau khám"])
  end
  G --- U2
  G --- U3
  G --- U4
  P --- U1
  P --- U6
  P --- U7
  P --- U8
  P --- U9
  P --- U10
  P --- U11
  P --- U12
  P --- U13
  P --- U14
  U4 -. "include" .-> U5
  U3 -. "extend" .-> U4
  U7 -. "include" .-> U8
  U13 -. "extend: có dấu hiệu cấp cứu" .-> U8
```

Ghi chú: đặt lịch cho phép khách (cần email để xác nhận); `<<extend>>` trỏ **từ** use case mở rộng **về** use case cơ sở. *Đánh giá sau khám (U15)*: bảng `feedbacks` đã có nhưng **chưa có API/giao diện** – không tính là đã làm.

### 2.2 Nhân viên y tế và vận hành

```mermaid
flowchart LR
  D(["Bác sĩ R2"])
  L(["Lễ tân R5"])
  N(["Điều dưỡng R6"])
  C(["Điều phối viên R7"])
  T(["Thu ngân R4"])
  A(["Admin R1"])
  TV(["Thiết bị TV R8"])
  subgraph UC["Hệ thống đặt lịch và hàng đợi"]
    D1(["Quản lý lịch làm việc, hồ sơ bác sĩ"])
    D2(["Gọi số tiếp theo / gọi lại"])
    D3(["Bắt đầu khám / kết thúc khám"])
    D4(["Đánh vắng mặt"])
    D5(["Kê đơn, gửi kết quả"])
    D6(["Xem hồ sơ bệnh nhân mình điều trị"])
    L1(["Check-in hộ bệnh nhân"])
    L2(["Đăng ký bệnh nhân vãng lai"])
    L3(["Đặt ưu tiên khẩn cấp (bắt buộc nêu lý do)"])
    L4(["Xem và huỷ mọi lịch hẹn"])
    C1(["Xem heatmap tải các phòng"])
    C2(["Chuyển vé vãng lai sang phòng khác"])
    C3(["Xem thống kê hàng đợi"])
    T1(["Xác nhận thanh toán, tạo link PayOS"])
    A1(["Quản lý người dùng và vai trò"])
    A2(["Quản lý phòng, gán phòng cho bác sĩ"])
    A3(["Quản lý nội dung: chuyên khoa, cơ sở, gói khám, cẩm nang"])
    A4(["Xem nhật ký truy cập và chỉ số AI"])
    V1(["Hiển thị số đang gọi và 5 số kế tiếp"])
    SYS(["Hệ thống (bộ lập lịch)"])
    S1(["Tự đánh vắng mặt sau thời gian chờ"])
    S2(["Gửi nhắc hẹn 24h và 2h"])
    S3(["Nhả chỗ giữ quá hạn xác nhận"])
  end
  D --- D1
  D --- D2
  D --- D3
  D --- D4
  D --- D5
  D --- D6
  D --- L3
  L --- L1
  L --- L2
  L --- L3
  L --- L4
  N --- L1
  N --- L3
  C --- C1
  C --- C2
  C --- C3
  T --- T1
  A --- A1
  A --- A2
  A --- A3
  A --- A4
  A --- C1
  A --- C3
  TV --- V1
  SYS --- S1
  SYS --- S2
  SYS --- S3
  L2 -. "include" .-> L1
  D3 -. "include" .-> D2
```

Ghi chú: L2 tự chọn bác sĩ trực chờ ngắn nhất khi bệnh nhân không chỉ định (cân bằng tải). C2 chỉ áp dụng cho vé **vãng lai** đang chờ; vé đã đặt theo bác sĩ không tự ý chuyển. *Chưa làm:* tự động chuyển khi phòng "đỏ" và chuyển vé đã đặt có sự đồng ý của bệnh nhân.

---

## 3. ERD (schema v2)

37 bảng, 50 khoá ngoại. So với `database_schema_v2.md` bản này **bổ sung** các quan hệ còn thiếu (đối chiếu tự động với DDL baseline) và bảng `medicines` (không có khoá ngoại). Các cột tham chiếu `reference_codes` (giới tính, trạng thái, khung giờ, vai trò...) chỉ vẽ một số quan hệ chính để hình khỏi rối.

```mermaid
erDiagram
  reference_codes ||--o{ users : "gender, position"
  reference_codes ||--o{ patient_profiles : "gender"
  reference_codes ||--o{ doctor_profiles : "giá, thanh toán, tỉnh"
  reference_codes ||--o{ schedules : "time_code"
  reference_codes ||--o{ bookings : "status_code, time_code"
  rbac_roles ||--o{ users : role_code
  rbac_roles ||--o{ rbac_role_permissions : has
  rbac_permissions ||--o{ rbac_role_permissions : in
  users ||--o{ refresh_tokens : owns
  users ||--o{ device_tokens : owns
  users ||--o{ access_audit_logs : acts
  users ||--o{ patient_profiles : "chủ hồ sơ"
  users ||--o| doctor_profiles : "bác sĩ"
  users ||--o{ schedules : doctor_id
  users ||--o{ bookings : patient_id
  users ||--o{ notifications : receives
  users ||--o{ messages : "gửi/nhận"
  users ||--o{ health_assessments : makes
  users ||--o{ medical_records : "bác sĩ lập"
  users ||--o{ queue_tickets : "bác sĩ phụ trách"
  users ||--o{ queue_events : "người thao tác"
  users ||--o{ symptom_intakes : "người khai"
  specialties ||--o{ specialty_translations : i18n
  specialties ||--o{ doctor_profiles : ""
  specialties ||--o{ rooms : ""
  specialties ||--o{ packages : ""
  specialties ||--o{ symptom_intakes : "gợi ý"
  clinics ||--o{ clinic_translations : i18n
  clinics ||--o{ rooms : has
  clinics ||--o{ doctor_profiles : ""
  doctor_profiles ||--o{ doctor_profile_translations : i18n
  rooms ||--o{ schedules : room_id
  rooms ||--o{ queue_tickets : ""
  schedules ||--o{ bookings : "doctor_id, work_date, time_code"
  patient_profiles ||--o{ bookings : "người được khám"
  patient_profiles ||--o{ medical_records : ""
  patient_profiles ||--o{ queue_tickets : ""
  bookings ||--o| medical_records : ""
  bookings ||--o| payments : ""
  bookings ||--o| feedbacks : ""
  bookings ||--o| queue_tickets : "NULL = vãng lai"
  bookings ||--o{ symptom_intakes : triage
  queue_tickets ||--o{ queue_events : "nhật ký"
  queue_tickets ||--o{ ai_predictions : "dự đoán và thực tế"
  ml_model_versions ||--o{ ai_predictions : ""
  ml_model_versions ||--o{ symptom_intakes : ""
  facilities ||--o{ packages : offers
  handbooks ||--o{ handbook_translations : i18n
  category_questions ||--o{ questions : ""
  questions ||--o{ question_options : ""
```

Bảng độc lập (không khoá ngoại): `medicines`. Ràng buộc nghiệp vụ quan trọng đặt trong DB: `UNIQUE(room_id, ticket_date, shift, seq)` (số thứ tự không trùng), `UNIQUE(booking_id)` (một lịch hẹn một vé), `UNIQUE(patient_id, work_date, time_code, holder_flag)` (một người không giữ hai lịch cùng giờ), `CHECK(booking_id IS NOT NULL OR walk_in_name IS NOT NULL)`.

---

## 4. Sơ đồ lớp (lớp nghiệp vụ chính)

Vẽ các **thực thể cốt lõi** (khớp bảng) và các **dịch vụ** của lõi hàng đợi. Không vẽ lại toàn bộ 37 bảng (xem ERD) và không vẽ controller/route vì chỉ là lớp mỏng.

```mermaid
classDiagram
  direction LR
  class User {
    +id
    +email
    +roleCode
    +isActive
    +tokenVersion
  }
  class PatientProfile {
    +id
    +relationship SELF|CHILD|PARENT...
    +fullName
    +dateOfBirth
  }
  class DoctorProfile {
    +doctorId
    +specialtyId
    +clinicId
  }
  class Schedule {
    +doctorId
    +workDate
    +timeCode
    +maxPatients
    +currentPatients
    +roomId
  }
  class Booking {
    +code
    +statusCode S1..S6
    +source ONLINE|WALK_IN
    +holdExpiresAt
    +symptoms
  }
  class Room {
    +name
    +clinicId
    +specialtyId
    +isActive
  }
  class QueueTicket {
    +displayNo
    +seq
    +shift
    +priority NORMAL|ELDERLY|EMERGENCY
    +status
    +sortAt
    +callCount
    +postponedCount
    +walkInName
  }
  class QueueEvent {
    +eventType
    +actorUserId
    +payload JSON
  }
  class AiPrediction {
    +predictedDurationMin
    +predictedWaitMin
    +actualDurationMin
    +actualWaitMin
  }
  class SymptomIntake {
    +rawText
    +severity
    +urgency
    +suggestedSpecialtyId
    +confidence
  }
  class Notification {
    +type
    +channel
    +dedupeKey
    +readAt
  }
  User "1" --> "0..1" DoctorProfile
  User "1" --> "*" PatientProfile
  User "1" --> "*" Booking : patient
  Schedule "1" --> "*" Booking : khung giờ
  Booking "1" --> "0..1" QueueTicket
  Room "1" --> "*" QueueTicket
  QueueTicket "1" --> "*" QueueEvent
  QueueTicket "1" --> "*" AiPrediction
  Booking "1" --> "*" SymptomIntake
  User "1" --> "*" Notification

  class QueueRules {
    <<pure functions>>
    +canTransition(event, status)
    +sortTickets(tickets)
    +priorityBonus(age)
  }
  class QueueService {
    +checkIn(bookingId)
    +createWalkIn(data)
    +callNext(doctorId)
    +start(ticketId)
    +finish(ticketId)
    +markNoShow(ticketId)
    +autoNoShow()
    +postpone(ticketId)
    +setEmergency(ticketId, reason)
    +transferTicket(ticketId, toDoctorId)
  }
  class QueueEta {
    +estimateForDoctor(tickets, avg, now, durations)
  }
  class QueueBalance {
    +rankCandidates(candidates)
  }
  class QueueAnalytics {
    +heatmap(date, clinicId)
    +stats(from, to)
  }
  class BookingService {
    +createBooking()
    +confirmByToken()
    +cancelBookingById()
    +releaseExpiredHolds()
  }
  class AiClient {
    +predictDurations(batch)
    +triage(text)
    -circuit closed|open|half_open
  }
  class ReminderService {
    +scanAppointmentReminders()
    +handleQueueChange()
  }
  QueueService ..> QueueRules : dùng
  QueueService ..> QueueEta : ETA
  QueueService ..> QueueBalance : chọn bác sĩ
  QueueEta ..> AiClient : thời lượng ML (tuỳ chọn)
  QueueAnalytics ..> QueueBalance
  QueueService ..> QueueTicket
  BookingService ..> Booking
  ReminderService ..> Notification
  ReminderService ..> QueueService : sự kiện hàng đợi
```

---

## 5. Máy trạng thái

### 5.1 Vé hàng đợi (`queue_tickets.status`)

Vé chỉ được tạo **khi bệnh nhân đến** (check-in hoặc vãng lai) nên bắt đầu ở `WAITING`. `BOOKED`, `CHECKED_IN`, `POSTPONED` có trong ENUM của DB nhưng **chưa dùng**.

```mermaid
stateDiagram-v2
  [*] --> WAITING : check-in / vãng lai
  WAITING --> CALLED : gọi số
  CALLED --> CALLED : gọi lại (tối đa 3 lần)
  CALLED --> IN_PROGRESS : bắt đầu khám
  IN_PROGRESS --> DONE : kết thúc khám
  WAITING --> WAITING : xin dời lượt (≤ 2 lần) / khẩn cấp / chuyển phòng
  WAITING --> CANCELLED : huỷ
  CANCELLED --> WAITING : đến lại (hồi sinh đúng vé cũ)
  CALLED --> WAITING : vắng mặt lần 1 (xếp lại cuối hàng)
  CALLED --> NO_SHOW : vắng mặt lần 2 (huỷ lịch, nhả khung giờ)
  DONE --> [*]
  NO_SHOW --> [*]
```

Vắng mặt do bác sĩ bấm cần đã gọi đủ 3 lần; **tự động** sau `NOSHOW_TIMEOUT_MIN` (mặc định 10 phút) kể từ lần gọi gần nhất thì không cần đủ 3 lần (`actor = NULL`, payload `auto: true`).

### 5.2 Lịch hẹn (`bookings.status_code`)

```mermaid
stateDiagram-v2
  [*] --> S1 : đặt lịch (giữ chỗ 15 phút)
  S1 --> S2 : bấm link xác nhận email
  S1 --> S4 : quá hạn giữ chỗ
  S2 --> S4 : bệnh nhân/lễ tân/bác sĩ huỷ, hoặc vắng mặt lần 2
  S2 --> S3 : bác sĩ gửi đơn/kết quả
  S3 --> S6 : tạo hoá đơn chờ thu ngân
  S6 --> S5 : thu ngân xác nhận / PayOS / Casso
  S5 --> [*]
  S4 --> [*]
```

S1 chiếm chỗ **chỉ khi còn trong hạn**. Một lịch hẹn có tối đa một vé hàng đợi; hoàn tất khám ở hàng đợi (`DONE`) và gửi đơn (`S3`) là hai bước độc lập.

---

## 6. Sơ đồ tuần tự

### 6.1 Đặt lịch và xác nhận

```mermaid
sequenceDiagram
  actor BN as Bệnh nhân
  participant FE as Web React
  participant API as Backend
  participant AI as AI Service
  participant DB as MySQL
  participant Mail as SMTP
  opt Có mô tả triệu chứng
    FE->>API: POST /api/ai/triage {text}
    API->>AI: phân loại (timeout, ngắt mạch)
    AI-->>API: chuyên khoa gợi ý
    API-->>FE: available true/false (lỗi thì chọn tay)
  end
  BN->>FE: chọn bác sĩ, khung giờ
  FE->>API: POST /api/patient-book-appointment
  API->>DB: BEGIN, khoá dòng schedule (FOR UPDATE)
  alt còn chỗ và không trùng giờ
    API->>DB: INSERT booking S1 (hold_expires_at), current+1
    API->>DB: COMMIT
    API->>Mail: gửi link xác nhận (token băm sha256)
    API-->>FE: errCode 0, holdMinutes
    BN->>API: mở link /verify-book-appointment
    API->>DB: S1 → S2 (còn hạn)
  else hết chỗ hoặc trùng giờ
    API->>DB: ROLLBACK
    API-->>FE: lỗi nghiệp vụ
  end
  Note over API,DB: Bộ quét mỗi 60s: S1 quá hạn → S4, nhả chỗ
```

### 6.2 Check-in, gọi số, khám xong (luồng lõi)

```mermaid
sequenceDiagram
  actor BN as Bệnh nhân
  actor BS as Bác sĩ
  participant API as Backend
  participant Q as Queue Engine
  participant AI as AI Service
  participant DB as MySQL
  participant WS as Socket.io
  participant TV as Màn hình TV
  BN->>API: POST /api/queue/check-in {bookingId}
  API->>Q: checkIn
  Q->>DB: BEGIN, khoá phòng, cấp seq = MAX+1, INSERT vé WAITING
  Q->>DB: INSERT queue_events CHECK_IN, COMMIT
  Q->>AI: dự đoán thời lượng cả hàng (1 lô, lỗi thì dùng trung bình lịch sử)
  Q->>DB: ghi ai_predictions (dự đoán + baseline)
  Q-->>WS: sau COMMIT: QUEUE_UPDATED, QUEUE_TICKET_UPDATED
  WS-->>TV: số đang gọi + 5 số kế tiếp
  WS-->>BN: vị trí và thời gian chờ mới
  BS->>API: POST /api/queue/doctor/call-next
  Q->>DB: khoá bác sĩ, chọn đầu hàng (khẩn cấp trước, rồi sort_at)
  Q->>DB: WAITING → CALLED, call_count+1, event CALL
  Q-->>WS: TICKET_CALLED {announce}
  WS-->>TV: đọc loa "Xin mời bệnh nhân số ..."
  BS->>API: /tickets/:id/start rồi /finish
  Q->>DB: CALLED → IN_PROGRESS → DONE, event START/FINISH
  Q->>DB: điền thời lượng và thời gian chờ thực tế vào ai_predictions
  Q-->>WS: cập nhật mọi người phía sau (ETA đổi)
```

### 6.3 Vãng lai tự chọn bác sĩ và chuyển vé giữa phòng

```mermaid
sequenceDiagram
  actor LT as Lễ tân
  actor DP as Điều phối viên
  participant API as Backend
  participant Q as Queue Engine
  participant DB as MySQL
  participant WS as Socket.io
  LT->>API: POST /api/queue/walk-in {specialtyId, fullName, priority}
  Q->>DB: lấy bác sĩ trực ca hiện tại (cùng chuyên khoa)
  Q->>Q: ETA vé giả của từng bác sĩ, xếp: chờ ngắn nhất, ít người, id nhỏ
  Q->>DB: tạo vé, event WALK_IN {assignedBy AUTO, considered[]}
  Q-->>LT: displayNo + phòng + ETA
  DP->>API: GET /api/queue/heatmap
  API-->>DP: phòng GREEN/YELLOW/RED + số liệu trong ngày
  DP->>API: POST /api/queue/tickets/:id/transfer {toDoctorId?, reason}
  alt vé WAITING, vãng lai, đích cùng chuyên khoa và đang trực
    Q->>DB: khoá vé, đổi phòng/bác sĩ, cấp số mới (giữ sort_at, ưu tiên)
    Q->>DB: event TRANSFER {lý do, số cũ/mới, chờ trước/sau} + audit_logs
    Q-->>WS: QUEUE_UPDATED cho phòng cũ và phòng mới
  else không hợp lệ
    API-->>DP: NOT_ALLOWED / TARGET_UNAVAILABLE / NO_BETTER_ROOM
  end
```

### 6.4 Tự đánh vắng mặt và nhắc hẹn (tác vụ nền)

```mermaid
sequenceDiagram
  participant SCH as Bộ lập lịch
  participant Q as Queue Engine
  participant R as ReminderService
  participant DB as MySQL
  participant N as Email / FCM / thông báo trong ứng dụng
  loop mỗi 60 giây
    SCH->>Q: autoNoShow()
    Q->>DB: vé CALLED có called_at cũ hơn 10 phút
    Q->>DB: khoá vé, kiểm tra lại, lần 1 xếp lại cuối hàng / lần 2 NO_SHOW + huỷ lịch
  end
  loop mỗi 300 giây (BullMQ nếu có Redis, không thì setInterval)
    SCH->>R: quét lịch hẹn đã xác nhận
    R->>DB: lịch còn khoảng 24h và 2h, chưa gửi (dedupeKey)
    R->>N: gửi nhắc hẹn
  end
  Note over Q,R: Mỗi lần hàng đợi đổi (sau COMMIT), nếu còn 3 hoặc 1 người phía trước thì R gửi QUEUE_NEARING
```

---

## 7. Sơ đồ hoạt động

### 7.1 Hành trình bệnh nhân trong ngày khám

```mermaid
flowchart TD
  A([Bắt đầu]) --> B{Đã đặt lịch?}
  B -- Có --> C[Nhận nhắc hẹn 24h và 2h]
  C --> D[Đến cơ sở, check-in tại quầy hoặc trên điện thoại]
  B -- Không --> E[Đăng ký vãng lai tại quầy]
  E --> F{Chỉ định bác sĩ?}
  F -- Có --> G[Xếp đúng bác sĩ]
  F -- Không --> H[Hệ thống chọn bác sĩ chờ ngắn nhất]
  D --> I[Nhận vé và số thứ tự]
  G --> I
  H --> I
  I --> J[Theo dõi vị trí và thời gian chờ]
  J --> K{Còn 3 người phía trước?}
  K -- Có --> L[Nhận cảnh báo sắp đến lượt]
  K -- Không --> J
  L --> M[Số được gọi, TV đọc loa]
  M --> N{Có mặt trong thời gian chờ?}
  N -- Không --> O{Lần vắng mặt thứ mấy?}
  O -- Lần 1 --> I
  O -- Lần 2 --> P[Huỷ lịch, kết thúc]
  N -- Có --> Q[Khám]
  Q --> R[Nhận đơn thuốc, kết quả]
  R --> S[Thanh toán tại quầy hoặc online]
  S --> T([Kết thúc])
  P --> T
```

### 7.2 Bác sĩ xử lý hàng đợi

```mermaid
flowchart TD
  A([Đăng nhập, mở bảng bác sĩ]) --> B{Có người đang CALLED hoặc IN_PROGRESS?}
  B -- Có --> C[Chờ hoàn tất ca hiện tại]
  B -- Không --> D[Gọi số tiếp theo]
  D --> E{Hàng chờ rỗng?}
  E -- Có --> F([Chờ bệnh nhân mới])
  E -- Không --> G[Vé lên CALLED, phát TV]
  G --> H{Bệnh nhân có mặt?}
  H -- Không --> I{Đã gọi đủ 3 lần hoặc quá 10 phút?}
  I -- Chưa --> J[Gọi lại]
  J --> H
  I -- Rồi --> K[Đánh vắng mặt]
  H -- Có --> L[Bắt đầu khám]
  L --> M[Khám, kê đơn]
  M --> N[Kết thúc khám]
  N --> O[Ghi thời lượng thực tế cho AI]
  K --> B
  O --> B
```

---

## 8. Đối chiếu với sơ đồ cũ

| Sơ đồ cũ | Vấn đề | Trong bản này |
|---|---|---|
| `usecase_diagram.md` | Chỉ có bệnh nhân và bác sĩ; thiếu check-in, hàng đợi, vãng lai, điều phối, TV, tác vụ nền; phân quyền theo nhóm vai trò | §2 theo 8 vai trò + tác nhân hệ thống |
| `class_diagram.md` | Tên bảng/quan hệ theo schema cũ (`Allcodes`, `Doctor_Infor`...) | §3 ERD v2 + §4 lớp nghiệp vụ |
| `sequence_diagrams.md`, `activity_diagrams.md` | Không có check-in, gọi số, ETA, AI, nhắc hẹn, cân bằng tải, chuyển vé; chat, kho thuốc vẫn đúng ý tưởng | §6, §7 cho luồng mới. **Chat bác sĩ, kho thuốc, bài test sức khoẻ không đổi nên chưa vẽ lại** – dùng bản cũ |

**Chưa vẽ vì chưa có trong mã:** đánh giá sau khi khám (bảng `feedbacks` chưa có API), tự động chuyển phòng khi heatmap đỏ, chuyển vé đã đặt lịch.
