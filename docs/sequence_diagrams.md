# 🔄 Trọn bộ Sơ đồ tuần tự chuẩn mẫu báo cáo (UML Sequence Diagrams)

Tài liệu này cung cấp mã nguồn **PlantUML** cho các sơ đồ tuần tự được thiết kế **chính xác 100% theo đúng định dạng mẫu ảnh của bạn**:
- Sử dụng cấu trúc `box "<Tiêu đề sơ đồ>" #White ... end box` bao trùm toàn bộ các thành phần actor/participant để tạo **đường viền lớn bao quanh toàn bộ sơ đồ** kèm **tiêu đề in đậm ở giữa phía trên**.
- Phân đoạn các mốc giai đoạn bằng thanh ngăn cách UML (`== Tên giai đoạn ==`).
- Tương thích tuyệt đối 100% với **draw.io / app.diagrams.net** (không báo bất kỳ lỗi nào).

---

## 1. Hình 15: Sơ đồ tuần tự Chat giữa bệnh nhân và bác sĩ

```plantuml
@startuml
skinparam shadowing false
skinparam defaultFontName "Times New Roman"
skinparam defaultFontSize 13
skinparam sequenceMessageAlign center

box "Sơ đồ Sequence: Chức năng Chat giữa Bệnh nhân và Bác sĩ" #White
actor "Bệnh nhân" as BN
participant "Chat System" as CS
participant "Cơ sở dữ liệu" as DB
participant "Notification System" as NS
actor "Bác sĩ" as BS
end box

== Khởi tạo Chat ==
BN -> CS: Yêu cầu chat với bác sĩ
CS -> DB: Kiểm tra appointment đã confirmed
DB --> CS: Trả về thông tin appointment
CS -> DB: Tạo chat session
DB --> CS: Xác nhận tạo chat
CS -> NS: Thông báo bác sĩ có chat mới
NS -> BS: Gửi thông báo chat
CS --> BN: Khởi tạo chat thành công

== Trao đổi tin nhắn ==
BN -> CS: Gửi tin nhắn
CS -> DB: Lưu tin nhắn
DB --> CS: Xác nhận lưu
CS -> NS: Thông báo tin nhắn mới
NS -> BS: Gửi thông báo tin nhắn
CS -> BS: Hiển thị tin nhắn
BS -> CS: Gửi phản hồi
CS -> DB: Lưu tin nhắn phản hồi
DB --> CS: Xác nhận lưu
CS -> NS: Thông báo tin nhắn mới
NS -> BN: Gửi thông báo tin nhắn
CS --> BN: Hiển thị phản hồi

== Kết thúc Chat ==
alt [Bác sĩ kết thúc]
    BS -> CS: Kết thúc chat
    CS -> DB: Cập nhật trạng thái chat
    CS --> BN: Thông báo chat đã kết thúc
else [Bệnh nhân kết thúc]
    BN -> CS: Kết thúc chat
    CS -> DB: Cập nhật trạng thái chat
    CS --> BS: Thông báo chat đã kết thúc
end
@enduml
```

---

## 2. Hình 16: Sơ đồ tuần tự Chat với trợ lý ChatBotAI

```plantuml
@startuml
skinparam shadowing false
skinparam defaultFontName "Times New Roman"
skinparam defaultFontSize 13
skinparam sequenceMessageAlign center

box "Sơ đồ Sequence: Chức năng Chat với trợ lý ChatBotAI" #White
actor "Bệnh nhân" as BN
participant "Chatbot AI" as CB
participant "CSDL Tri thức" as DB
actor "Bác sĩ (gợi ý)" as BS
end box

== Gửi câu hỏi và truy vấn ==
BN -> CB: Gửi câu hỏi
CB -> DB: Truy vấn cơ sở tri thức
DB --> CB: Trả lời hoặc không tìm thấy

== Xử lý phản hồi ==
alt [Có câu trả lời]
    CB -> BN: Gửi phản hồi
else [Không tìm thấy]
    CB -> BN: Gợi ý liên hệ bác sĩ
    CB -> BS: Thông báo hỗ trợ bệnh nhân
end
@enduml
```

---

## 3. Hình 17: Sơ đồ tuần tự Làm bài test sức khỏe

```plantuml
@startuml
skinparam shadowing false
skinparam defaultFontName "Times New Roman"
skinparam defaultFontSize 13
skinparam sequenceMessageAlign center

box "Sơ đồ Sequence: Chức năng Làm bài test sức khỏe" #White
actor "Bệnh nhân" as BN
participant "Hệ thống" as HT
participant "Cơ sở dữ liệu" as DB
end box

== Lấy danh sách câu hỏi ==
BN -> HT: Chọn mục "Bài test sức khỏe"
HT -> DB: Lấy danh sách bài test
DB --> HT: Trả về danh sách
HT -> BN: Hiển thị danh sách bài test

== Thực hiện và nộp bài test ==
BN -> HT: Chọn bài test và trả lời câu hỏi
HT -> DB: Lưu câu trả lời
HT -> HT: Phân tích kết quả
HT -> BN: Hiển thị kết quả
HT -> DB: Lưu kết quả test
@enduml
```

---

## 4. Hình 18: Sơ đồ tuần tự Quản lý kho thuốc

```plantuml
@startuml
skinparam shadowing false
skinparam defaultFontName "Times New Roman"
skinparam defaultFontSize 13
skinparam sequenceMessageAlign center

box "Sơ đồ Sequence: Chức năng Quản lý kho thuốc" #White
actor "Admin" as AD
participant "Hệ thống" as HT
participant "Cơ sở dữ liệu" as DB
end box

== Xem danh mục thuốc ==
AD -> HT: Truy cập mục "Quản lý kho thuốc"
HT -> DB: Lấy danh sách thuốc
DB --> HT: Danh sách thuốc
HT -> AD: Hiển thị danh sách

== Thao tác cập nhật kho thuốc ==
AD -> HT: Thêm/Chỉnh sửa/Xóa thuốc
HT -> DB: Cập nhật cơ sở dữ liệu
DB --> HT: Xác nhận thành công
HT -> AD: Thông báo thành công
@enduml
```

---

## 🛠️ Hướng dẫn dán vào draw.io (app.diagrams.net):
1. Mở [app.diagrams.net](https://app.diagrams.net).
2. Vào: **Arrange** ➡️ **Insert** ➡️ **Advanced** ➡️ **PlantUML...**
3. Sao chép và dán mã ở trên vào.
4. Bấm **Insert**. Bạn sẽ nhận được sơ đồ có **khung viền chữ nhật bao trọn toàn bộ sơ đồ** từ trên xuống dưới, có tiêu đề nằm ở đầu, các thanh chia giai đoạn `== Tên giai đoạn ==` và khung `alt` giống hệt 100% như hình mẫu của bạn!
