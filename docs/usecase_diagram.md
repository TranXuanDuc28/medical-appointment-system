# 🎯 Tuyển tập Sơ đồ Use Case Hệ thống Y tế (UML Use Case Diagrams)

Tài liệu này phân tích, đánh giá tính chuẩn xác theo UML và mã nguồn thực tế, đồng thời cung cấp mã nguồn **PlantUML** hoàn chỉnh cho các sơ đồ Use Case của hệ thống:
1. **Sơ đồ Use Case của Bệnh nhân**
2. **Sơ đồ Use Case của Bác sĩ**

---

# PHẦN 1: SƠ ĐỒ USE CASE CỦA BỆNH NHÂN

## 🔍 I. Nhận xét sơ đồ Use Case Bệnh nhân (ảnh cũ)
1. **Sai chiều mũi tên `<<extend>>`**: Trong ảnh, mũi tên đi từ `Nhận đơn thuốc/kết quả` trỏ sang `Thanh toán chi phí online`. Quy tắc chuẩn UML: Mũi tên `<<extend>>` **bắt buộc phải trỏ từ Use Case mở rộng (Extension) VỀ Use Case cơ sở (Base)**.
2. **Lỗi phân rã chức năng (Functional Decomposition) ở `Đặt lịch khám`**: Tách `Đặt lịch khám` ra thành `Chọn bác sĩ`, `Chọn khung giờ`, `Xác nhận lịch khám` rồi nối `<<include>>` là sai bản chất của Use Case (vốn phải là mục tiêu trọn vẹn).
3. **Use Case thụ động**: `Nhận đơn thuốc/kết quả` là hành động bị động, nên chuẩn hóa thành `Xem lịch sử khám & Đơn thuốc`.
4. **Gộp `Đăng nhập/Đăng kí` trong một hình Oval**: Cần tách riêng thành 2 Use Case độc lập.
5. **Thiếu các tính năng cốt lõi**: Thiếu *Chatbot AI (RAG Gemini)*, *Bài test đánh giá sức khỏe*, *Gói khám tổng quát* và *Cẩm nang y tế*.

## 💻 Mã PlantUML Use Case Bệnh nhân

```plantuml
@startuml
skinparam shadowing false
skinparam defaultFontName "Times New Roman"
skinparam defaultFontSize 12
skinparam sequenceMessageAlign center

skinparam usecase {
    BackgroundColor #FFFFFF
    BorderColor #2C3E50
    ArrowColor #2C3E50
}

left to right direction

actor "Bệnh nhân" as Patient

rectangle "Phân hệ Bệnh nhân (Patient Portal)" {
    
    ' ====== 1. NHÓM TRA CỨU THÔNG TIN ======
    usecase "Xem thông tin Bác sĩ" as UC_Doctor
    usecase "Xem thông tin Cơ sở y tế" as UC_Clinic
    usecase "Xem Chuyên khoa y tế" as UC_Specialty
    usecase "Xem Gói khám tổng quát" as UC_Package
    usecase "Xem Cẩm nang y tế" as UC_Handbook

    ' ====== 2. NHÓM ĐẶT LỊCH & THANH TOÁN ======
    usecase "Đặt lịch khám bệnh" as UC_Book
    usecase "Xác thực lịch hẹn qua Email" as UC_Verify
    usecase "Thanh toán viện phí trực tuyến" as UC_Pay

    ' ====== 3. NHÓM TƯ VẤN & SỨC KHỎE ======
    usecase "Chat tư vấn với Trợ lý AI" as UC_AIChat
    usecase "Chat trực tuyến với Bác sĩ" as UC_DoctorChat
    usecase "Làm bài test đánh giá sức khỏe" as UC_Test

    ' ====== 4. NHÓM TÀI KHOẢN & BỆNH ÁN ======
    usecase "Xem lịch sử khám & Đơn thuốc" as UC_History
    usecase "Đăng nhập" as UC_Login
    usecase "Đăng ký tài khoản" as UC_Register

    ' ====== LIÊN KẾT TỪ BỆNH NHÂN ĐẾN USE CASE ======
    Patient --> UC_Doctor
    Patient --> UC_Clinic
    Patient --> UC_Specialty
    Patient --> UC_Package
    Patient --> UC_Handbook

    Patient --> UC_Book
    Patient --> UC_AIChat
    Patient --> UC_DoctorChat
    Patient --> UC_Test

    Patient --> UC_History
    Patient --> UC_Login
    Patient --> UC_Register

    ' ====== QUAN HỆ INCLUDE & EXTEND CHUẨN UML ======
    UC_Book ..> UC_Verify : <<include>>
    UC_Pay ..> UC_Book : <<extend>>
    UC_DoctorChat ..> UC_Login : <<include>>
    UC_History ..> UC_Login : <<include>>
}
@enduml
```

---

# PHẦN 2: SƠ ĐỒ USE CASE CỦA BÁC SĨ

## 🔍 I. Nhận xét sơ đồ Use Case Bác sĩ (ảnh của bạn)

Sơ đồ cũ trong ảnh có **4 lỗi sai rất nặng về cả chuẩn UML lẫn logic nghiệp vụ thực tế**:

### 1. Lỗi nghiệp vụ: Bác sĩ KHÔNG có Use Case "Đăng ký"
- Trong ảnh vẽ: `Đăng nhập/Đăng ký`.
- **Thực tế hệ thống**: Bác sĩ là nhân sự y tế chất lượng cao, **bác sĩ KHÔNG BAO GIỜ tự đăng ký tài khoản tự do trên trang web**. Tài khoản của Bác sĩ bắt buộc phải do **Quản trị viên (Admin) tạo trong hệ thống** và cấp chức danh (`positionId`: Bác sĩ CK1, Giáo sư,...), gán chuyên khoa (`specialtyId`), phòng khám (`clinicId`). Việc để use case "Đăng ký" cho Bác sĩ là sai hoàn toàn logic nghiệp vụ thực tế. Bác sĩ chỉ có **Đăng nhập hệ thống**.

### 2. Lỗi sai chuẩn UML: Chiều mũi tên `<<extend>>` bị ngược hoàn toàn
Trong ảnh có 2 mũi tên `<<extend>>` và **cả 2 đều bị vẽ ngược chiều**:
- `Chat với bệnh nhân` --<<extend>>--> `Tư vấn trực tuyến`: Mũi tên lại trỏ sang `Tư vấn trực tuyến`?! Thực chất 2 use case này là một, và chiều của `<<extend>>` trong UML luôn là: `Use Case mở rộng ..> Use Case cơ sở`.
- `Khám bệnh` --<<extend>>--> `Xem hồ sơ bệnh án`: Mũi tên lại trỏ từ `Khám bệnh` sang `Xem hồ sơ bệnh án`?! Đúng chuẩn UML phải là việc xem lại hồ sơ bệnh án cũ mở rộng hỗ trợ cho quá trình khám bệnh: `Xem hồ sơ bệnh án cũ` ..> `Khám bệnh` : `<<extend>>`.

### 3. Lỗi phân rã chức năng (Functional Decomposition) ở `Khám bệnh`:
- Tách `Khám bệnh` thành 3 use case con: `Ghi đơn thuốc`, `Ghi kết quả khám`, `Gửi đơn thuốc và chi phí` rồi nối `<<include>>` là bị vụn vặt và lặp lại thao tác.
- Trong mã nguồn thực tế ([`doctorServices.js:sendRemedyService`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/doctorServices.js#L705)), khi khám xong bác sĩ thực hiện một hành động trọn vẹn: **`Kê đơn & Gửi kết quả khám (Send Remedy)`** (ghi chẩn đoán, đính kèm đơn thuốc/hóa đơn gửi thẳng qua email bệnh nhân).

### 4. Lỗi sai chính tả và thuật ngữ:
- `Cập nhập lịch trống`: Sai chính tả tiếng Việt ("Cập nhập" -> phải là **"Thiết lập kế hoạch lịch khám"** hoặc **"Cập nhật lịch khám"**).
- `Xác nhận lịch hẹn`: Lịch hẹn do Bệnh nhân tự kích hoạt qua link Email token. Bác sĩ chỉ cần **Xem danh sách bệnh nhân đã được xác nhận (Status: S2) để tiến hành khám**.
- **Tính năng bị thiếu**: Thiếu Use Case **Tra cứu danh mục kho thuốc** (khi kê đơn cho bệnh nhân).

---

## 💻 II. Mã PlantUML Sơ đồ Use Case Bác sĩ chuẩn hóa 100%

*Sơ đồ nằm gọn trong **1 khung viền chữ nhật bao quanh toàn hệ thống**, đúng chiều mũi tên `<<include>>` và `<<extend>>`, chuẩn font Times New Roman, sẵn sàng dán trực tiếp vào draw.io:*

```plantuml
@startuml
skinparam shadowing false
skinparam defaultFontName "Times New Roman"
skinparam defaultFontSize 12
skinparam sequenceMessageAlign center

skinparam usecase {
    BackgroundColor #FFFFFF
    BorderColor #2C3E50
    ArrowColor #2C3E50
}

left to right direction

actor "Bác sĩ" as Doctor

rectangle "Phân hệ Bác sĩ (Doctor System)" {
    
    ' ====== 1. QUẢN LÝ LỊCH KHÁM ======
    usecase "Thiết lập kế hoạch lịch khám" as UC_Schedule
    usecase "Xem lịch khám bệnh" as UC_ViewSchedule

    ' ====== 2. KHÁM CHỮA BỆNH ======
    usecase "Xem danh sách bệnh nhân khám" as UC_ViewPatients
    usecase "Thực hiện khám bệnh" as UC_Exam
    usecase "Xem hồ sơ bệnh án cũ" as UC_History
    usecase "Kê đơn & Gửi kết quả khám" as UC_Remedy
    usecase "Tra cứu danh mục thuốc" as UC_Medicine

    ' ====== 3. TƯ VẤN & HỒ SƠ ======
    usecase "Chat trực tuyến với Bệnh nhân" as UC_Chat
    usecase "Xem thông tin chuyên môn cá nhân" as UC_Profile

    ' ====== 4. HỆ THỐNG ======
    usecase "Đăng nhập hệ thống" as UC_Login

    ' ====== LIÊN KẾT BÁC SĨ ĐẾN CÁC USE CASE ======
    Doctor --> UC_Schedule
    Doctor --> UC_ViewSchedule
    Doctor --> UC_ViewPatients
    Doctor --> UC_Exam
    Doctor --> UC_Chat
    Doctor --> UC_Profile
    Doctor --> UC_Login

    ' ====== QUAN HỆ INCLUDE & EXTEND CHUẨN UML ======
    ' Trong khi khám bệnh, bác sĩ kê đơn và gửi hóa đơn kết quả (bắt buộc)
    UC_Exam ..> UC_Remedy : <<include>>

    ' Bác sĩ có thể tùy chọn tra cứu kho thuốc khi kê đơn
    UC_Medicine ..> UC_Remedy : <<extend>>

    ' Bác sĩ có thể tùy chọn xem lại lịch sử bệnh án cũ của bệnh nhân
    UC_History ..> UC_Exam : <<extend>>

    ' Bác sĩ phải đăng nhập để thiết lập lịch, khám bệnh và chat
    UC_Schedule ..> UC_Login : <<include>>
    UC_Exam ..> UC_Login : <<include>>
    UC_Chat ..> UC_Login : <<include>>
}
@enduml
```

---

## 🛠️ Hướng dẫn dán vào draw.io (app.diagrams.net):
1. Mở [app.diagrams.net](https://app.diagrams.net).
2. Vào: **Arrange** ➡️ **Insert** ➡️ **Advanced** ➡️ **PlantUML...**
3. Sao chép và dán mã ở trên vào.
4. Bấm **Insert** để nhận ngay sơ đồ Use Case chuẩn chỉnh, không có lỗi, sẵn sàng đưa vào báo cáo đồ án tốt nghiệp.
