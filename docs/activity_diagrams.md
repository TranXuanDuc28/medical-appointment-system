# 📊 Trọn bộ Sơ đồ hoạt động Hệ thống Y tế (UML Activity Diagrams)

Tài liệu này cung cấp toàn bộ mã nguồn **PlantUML** cho 10 sơ đồ hoạt động chính của **Hệ thống đặt lịch khám bệnh trực tuyến (Medical Appointment System)**.

> [!IMPORTANT]
> **Quy chuẩn thiết kế thống nhất cho mọi sơ đồ:**
> - Khung UML bao ngoài dạng phân vùng (`partition "act <Tên quy trình>"`) kèm nhãn đầu gập ở góc trên.
> - **Chỉ duy nhất 1 điểm bắt đầu (`start`) và duy nhất 1 điểm kết thúc (`stop`)**.
> - Nhánh quyết định (Decision diamond) phân bổ đối xứng:
>   - Nhánh `Không` rẽ sang **trái** (thông báo lỗi/ngoại lệ).
>   - Nhánh `Có` rẽ sang **phải** (tiếp tục thực thi nghiệp vụ thành công).
> - Mọi nhánh rẽ đều được gom luồng bằng các hình thoi hội tụ (Merge diamond `<>`) trước khi đi đến khối `:Kết thúc quy trình;` và dừng tại `stop`.
> - Tông màu viền xám tiêu chuẩn UML (`#F2F2F2`, viền `#666666`, bo góc 15px), dán trực tiếp vào **app.diagrams.net** (draw.io) chạy hoàn hảo.

---

## Danh mục sơ đồ trong tài liệu:
1. [Sơ đồ hoạt động: Đăng nhập](#1-sơ-đồ-hoạt-động-đăng-nhập-act-đăng-nhập)
2. [Sơ đồ hoạt động: Đăng ký](#2-sơ-đồ-hoạt-động-đăng-ký-act-đăng-ký)
3. [Sơ đồ hoạt động: Thống kê & Báo cáo](#3-sơ-đồ-hoạt-động-thống-kê--báo-cáo-act-thống-kê)
4. [Sơ đồ hoạt động: Quy trình của Bác sĩ](#4-sơ-đồ-hoạt-động-quy-trình-của-bác-sĩ-act-quy-trình-bác-sĩ)
5. [Sơ đồ hoạt động: Quy trình của Quản trị viên](#5-sơ-đồ-hoạt-động-quy-trình-của-quản-trị-viên-act-quy-trình-quản-trị-viên)
6. [Sơ đồ hoạt động: Bệnh nhân Đặt lịch khám](#6-sơ-đồ-hoạt-động-bệnh-nhân-đặt-lịch-khám-act-bệnh-nhân-đặt-lịch-khám)
7. [Sơ đồ hoạt động: Chat với Bác sĩ](#7-sơ-đồ-hoạt-động-chat-với-bác-sĩ-act-chat-với-bác-sĩ)
8. [Sơ đồ hoạt động: Chat với trợ lý ChatBotAI](#8-sơ-đồ-hoạt-động-chat-với-trợ-lý-chatbotai-act-chat-với-trợ-lý-chatbotai)
9. [Sơ đồ hoạt động: Làm bài test Sức khỏe](#9-sơ-đồ-hoạt-động-làm-bài-test-sức-khỏe-act-làm-bài-test-sức-khỏe)
10. [Sơ đồ hoạt động: Quản lý Kho thuốc](#10-sơ-đồ-hoạt-động-quản-lý-kho-thuốc-act-quản-lý-kho-thuốc)

---

## 1. Sơ đồ Hoạt động: Đăng nhập (`act Đăng nhập`)
*Ánh xạ mã nguồn: [`Login.js`](file:///d:/XuanDuc/CV/medical-appointment-system/frontend/src/containers/Auth/Login.js), [`userController.js:handleLogin`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/controllers/userController.js#L30), [`userServices.js:handleUserLogin`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/userServices.js#L40).*

```plantuml
@startuml
title Sơ đồ Hoạt động: Đăng nhập

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Đăng nhập" {
  start
  :Người dùng truy cập màn hình Đăng nhập;
  :Nhập Email & Mật khẩu;
  :Bấm nút "Đăng nhập";
  :Gửi dữ liệu lên Hệ thống;
  :Truy vấn tài khoản theo Email từ Database;

  if (Tài khoản tồn tại?) then (Không)
    :Hệ thống báo lỗi;
    :Hiển thị cảnh báo "Sai Email hoặc Mật khẩu";
  else (Có)
    :Kiểm tra đối chiếu Mật khẩu (Thuật toán Bcrypt);
    if (Mật khẩu trùng khớp?) then (Không)
      :Hệ thống báo lỗi;
      :Hiển thị cảnh báo "Sai Email hoặc Mật khẩu";
    else (Có)
      :Kiểm tra biến trạng thái (Status) của tài khoản;
      if (Trạng thái == ACTIVE?) then (Không)
        :Hệ thống báo lỗi truy cập;
        :Hiển thị lỗi "Tài khoản đang bị khóa";
      else (Có)
        :Khởi tạo Access Token & Refresh Token;
        :Lưu Refresh Token vào Database để quản lý phiên;
        :Trả kết quả Thành công;
        :Lưu trữ Token vào bộ nhớ;
        :Chuyển hướng (Redirect) vào Màn hình chính;
        :Truy cập thành công vào hệ thống;
      endif
    endif
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 2. Sơ đồ Hoạt động: Đăng ký (`act Đăng ký`)
*Ánh xạ mã nguồn: [`userController.js:handleRegister`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/controllers/userController.js#L4), [`userServices.js:handleUserRegister`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/userServices.js#L7).*

```plantuml
@startuml
title Sơ đồ Hoạt động: Đăng ký

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Đăng ký" {
  start
  :Người dùng truy cập màn hình Đăng ký;
  :Nhập thông tin (Họ tên, Email, Mật khẩu, Số điện thoại);
  :Bấm nút "Đăng ký";
  :Hệ thống kiểm tra tính đầy đủ và định dạng dữ liệu đầu vào;

  if (Dữ liệu đầu vào hợp lệ?) then (Không)
    :Hệ thống báo lỗi;
    :Hiển thị cảnh báo "Vui lòng nhập đầy đủ và đúng định dạng dữ liệu";
  else (Có)
    :Gửi yêu cầu đăng ký lên Hệ thống (POST /api/register);
    :Truy vấn kiểm tra Email trong Database;
    if (Email chưa tồn tại trong hệ thống?) then (Không)
      :Hệ thống báo lỗi trùng lặp;
      :Hiển thị cảnh báo "Email này đã được đăng ký tài khoản";
    else (Có)
      :Băm mật khẩu bảo mật bằng thuật toán Bcrypt;
      :Tạo mới bản ghi người dùng trong Database (Vai trò: Bệnh nhân - R3);
      :Lưu thông tin thành công và phản hồi errCode = 0;
      :Hiển thị thông báo "Đăng ký tài khoản thành công";
      :Tự động chuyển hướng người dùng sang Màn hình Đăng nhập;
    endif
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 3. Sơ đồ Hoạt động: Thống kê & Báo cáo (`act Thống kê`)
*Ánh xạ mã nguồn: [`doctorServices.js:getListPatientForDoctor`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/doctorServices.js#L565), Bảng `Bookings`, `Cashiers`.*

```plantuml
@startuml
title Sơ đồ Hoạt động: Thống kê

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Thống kê" {
  start
  :Người dùng truy cập màn hình Thống kê;
  :Lựa chọn tiêu chí thống kê (Thời gian, Bác sĩ, Trạng thái lịch khám);
  :Bấm nút "Xem thống kê";
  :Gửi dữ liệu lên Hệ thống;
  :Kiểm tra tính hợp lệ của tham số đầu vào;

  if (Khoảng thời gian hợp lệ?) then (Không)
    :Hệ thống báo lỗi;
    :Hiển thị cảnh báo "Khoảng thời gian lọc không hợp lệ";
  else (Có)
    :Truy vấn dữ liệu từ Database (Bảng Booking, Cashier, User);
    if (Có dữ liệu thỏa mãn điều kiện?) then (Không)
      :Hệ thống thông báo;
      :Hiển thị thông báo "Không có số liệu phù hợp";
    else (Có)
      :Tổng hợp và tính toán các chỉ số (Lượt khám, Doanh thu, Tỷ lệ);
      :Kết xuất bảng số liệu & Biểu đồ thống kê trực quan;
      if (Yêu cầu xuất file báo cáo (Excel/PDF)?) then (Không)
        :Duy trì hiển thị số liệu trực tiếp trên giao diện;
      else (Có)
        :Khởi tạo và định dạng file dữ liệu báo cáo;
        :Kích hoạt tải file báo cáo về thiết bị người dùng;
        :Hiển thị thông báo "Xuất báo cáo thành công";
      endif
    endif
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 4. Sơ đồ Hoạt động: Quy trình của Bác sĩ (`act Quy trình Bác sĩ`)
*Ánh xạ mã nguồn: [`ManageSchedule.js`](file:///d:/XuanDuc/CV/medical-appointment-system/frontend/src/containers/System/Doctor/ManageSchedule.js), [`ManagePatient.js`](file:///d:/XuanDuc/CV/medical-appointment-system/frontend/src/containers/System/Doctor/ManagePatient.js), [`doctorServices.js:sendRemedyService`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/doctorServices.js#L705).*

```plantuml
@startuml
title Sơ đồ Hoạt động: Quy trình của Bác sĩ

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Quy trình Bác sĩ" {
  start
  :Bác sĩ đăng nhập vào hệ thống (Role: Bác sĩ - R2);
  :Truy cập Bảng làm việc của Bác sĩ;
  :Thiết lập kế hoạch lịch làm việc (Chọn ngày & Khung giờ khám);
  :Hệ thống lưu lịch vào bảng Schedules;
  :Bác sĩ truy cập màn hình Quản lý bệnh nhân khám bệnh;
  :Chọn ngày khám để tải danh sách bệnh nhân đã xác nhận (Status: S2);

  if (Có bệnh nhân đăng ký khám trong ngày?) then (Không)
    :Hệ thống thông báo;
    :Hiển thị "Chưa có bệnh nhân đặt lịch trong ngày đã chọn";
  else (Có)
    :Bác sĩ chọn bệnh nhân và tiến hành thăm khám;
    :Chẩn đoán bệnh và kê đơn thuốc (Danh mục Thuốc & Liều lượng);
    :Mở hộp thoại gửi kết quả khám (Ghi chú & Tải ảnh đơn thuốc);
    :Bấm nút "Gửi kết quả khám bệnh" (Send Remedy);
    if (Đơn thuốc và thông tin đính kèm đầy đủ?) then (Không)
      :Hệ thống báo lỗi;
      :Hiển thị cảnh báo "Vui lòng đính kèm hóa đơn/đơn thuốc";
    else (Có)
      :Hệ thống gửi Email kết quả khám kèm đơn thuốc tới Bệnh nhân;
      :Cập nhật trạng thái lịch hẹn trong Database sang "Đã khám" (S3);
      :Đồng bộ thông tin sang bộ phận Thu ngân & Dược;
      :Hiển thị thông báo "Gửi kết quả khám thành công";
    endif
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 5. Sơ đồ Hoạt động: Quy trình của Quản trị viên (`act Quy trình Quản trị viên`)
*Ánh xạ mã nguồn: [`UserRedux.js`](file:///d:/XuanDuc/CV/medical-appointment-system/frontend/src/containers/System/Admin/UserRedux.js), [`ManageDoctor.js`](file:///d:/XuanDuc/CV/medical-appointment-system/frontend/src/containers/System/Admin/ManageDoctor.js), [`Specialty.js`](file:///d:/XuanDuc/CV/medical-appointment-system/frontend/src/containers/HomePage/Section/Specialty.js), [`Clinic.js`](file:///d:/XuanDuc/CV/medical-appointment-system/frontend/src/containers/System/Clinic/ManageClinic.js).*

```plantuml
@startuml
title Sơ đồ Hoạt động: Quy trình của Quản trị viên

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Quy trình Quản trị viên" {
  start
  :Quản trị viên đăng nhập vào hệ thống (Role: Admin - R1);
  :Truy cập Bảng điều khiển quản trị (Admin Dashboard);
  :Chọn danh mục quản lý (Người dùng, Bác sĩ, Chuyên khoa, Phòng khám, Cẩm nang);
  :Hệ thống tải danh sách dữ liệu và hiển thị bảng thông tin;
  :Quản trị viên thực hiện thao tác (Thêm mới, Cập nhật hoặc Xóa bản ghi);
  :Bấm nút "Lưu thay đổi" / "Xác nhận";

  if (Dữ liệu biểu mẫu hợp lệ?) then (Không)
    :Hệ thống báo lỗi biểu mẫu;
    :Hiển thị cảnh báo "Dữ liệu nhập chưa đầy đủ hoặc không đúng quy cách";
  else (Có)
    :Gửi yêu cầu API đến máy chủ Backend;
    :Máy chủ xác thực quyền Admin và thực thi cập nhật Database;
    if (Cập nhật Database thành công?) then (Không)
      :Hệ thống báo lỗi Server;
      :Hiển thị cảnh báo "Lỗi xử lý cơ sở dữ liệu, thao tác thất bại";
    else (Có)
      :Xóa bộ nhớ đệm (Invalidate Redis Cache) liên quan;
      :Ghi nhận lịch sử thao tác vào hệ thống;
      :Tải lại danh sách dữ liệu mới nhất trên giao diện;
      :Hiển thị thông báo "Cập nhật dữ liệu thành công";
    endif
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 6. Sơ đồ Hoạt động: Bệnh nhân Đặt lịch khám (`act Bệnh nhân Đặt lịch khám`)
*Ánh xạ mã nguồn: [`patientServices.js:postBookAppointmentServices`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/patientServices.js#L11), [`postVerifyBookAppointment`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/patientServices.js#L103).*

```plantuml
@startuml
title Sơ đồ Hoạt động: Bệnh nhân Đặt lịch khám

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Bệnh nhân Đặt lịch khám" {
  start
  :Bệnh nhân tìm kiếm Bác sĩ / Chuyên khoa / Cơ sở y tế;
  :Xem thông tin chi tiết bác sĩ và bảng lịch khám khả dụng;
  :Chọn Ngày khám và Khung giờ khám mong muốn;
  :Điền thông tin đặt lịch (Họ tên, Email, SĐT, Giới tính, Địa chỉ, Lý do khám);
  :Bấm nút "Xác nhận đặt lịch hẹn";

  if (Thông tin nhập đầy đủ và hợp lệ?) then (Không)
    :Hệ thống báo lỗi biểu mẫu;
    :Hiển thị cảnh báo "Vui lòng nhập đầy đủ thông tin bắt buộc";
  else (Có)
    :Gửi yêu cầu POST /api/patient-book-appointment;
    :Tạo bản ghi User (Role R3) và bản ghi Booking (Status: S1 - Mới);
    :Khởi tạo mã Token xác thực bảo mật duy nhất (UUID);
    :Hệ thống gửi Email xác nhận kèm đường link chứa Token tới Bệnh nhân;
    :Bệnh nhân mở hộp thư Email và click vào link xác nhận lịch hẹn;
    :Hệ thống tiếp nhận yêu cầu xác thực qua /api/verify-book-appointment;
    if (Token hợp lệ & Lịch hẹn chưa từng kích hoạt?) then (Không)
      :Hệ thống báo lỗi xác thực;
      :Hiển thị thông báo "Lịch hẹn đã được xác nhận trước đó hoặc link hết hạn";
    else (Có)
      :Cập nhật trạng thái lịch khám trong Database sang "Đã xác nhận" (S2);
      :Cập nhật số lượng chỗ khám của Bác sĩ trong bảng Schedules;
      :Điều hướng sang cổng thanh toán viện phí (VietQR / PayOS) hoặc chọn trả sau;
      :Hiển thị thông báo "Xác nhận đặt lịch khám thành công";
    endif
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 7. Sơ đồ Hoạt động: Chat với Bác sĩ (`act Chat với Bác sĩ`)
*Ánh xạ mã nguồn: [`socket/index.js`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/socket/index.js#L30), [`chatController.js`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/controllers/chatController.js), [`chatServices.js`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/chatServices.js).*

```plantuml
@startuml
title Sơ đồ Hoạt động: Chat với Bác sĩ

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Chat với Bác sĩ" {
  start
  :Người dùng (Bệnh nhân/Bác sĩ) mở màn hình "Tin nhắn tư vấn";
  :Hệ thống khởi tạo kết nối Socket.IO đến máy chủ;
  :Chọn cuộc trò chuyện và tải lịch sử tin nhắn từ Database;
  :Soạn nội dung tin nhắn hoặc chọn file/ảnh đính kèm;
  :Bấm nút "Gửi tin nhắn";

  if (Tin nhắn hợp lệ (Không để trống / File đúng định dạng)?) then (Không)
    :Hệ thống báo lỗi;
    :Hiển thị cảnh báo "Nội dung tin nhắn hoặc file không hợp lệ";
  else (Có)
    if (Có tệp tin/hình ảnh đính kèm?) then (Không)
      :Đóng gói tin nhắn văn bản;
    else (Có)
      :Gửi tệp lên server qua API /api/upload-file;
      :Nhận đường dẫn URL của tệp và gán vào dữ liệu tin nhắn;
    endif
    :Phát sự kiện Socket "SEND_MSG" lên Socket Server;
    :Máy chủ lưu bản ghi tin nhắn vào bảng Messages trong Database;
    if (Người nhận đang Online (Đang kết nối Socket)?) then (Không)
      :Lưu tin nhắn ở trạng thái chờ người nhận truy cập;
    else (Có)
      :Máy chủ chuyển tiếp sự kiện "RECEIVED_MSG" tới Socket người nhận;
      :Màn hình người nhận hiển thị tin nhắn mới theo thời gian thực;
    endif
    :Cập nhật trạng thái tin nhắn "Đã gửi" trên màn hình người gửi;
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 8. Sơ đồ Hoạt động: Chat với trợ lý ChatBotAI (`act Chat với Trợ lý ChatBotAI`)
*Ánh xạ mã nguồn: [`chatbot/app/routes/core.py:generate_stream_chatbox`](file:///d:/XuanDuc/CV/medical-appointment-system/chatbot/app/routes/core.py#L27), [`chatbot/core/chatbot.py`](file:///d:/XuanDuc/CV/medical-appointment-system/chatbot/core/chatbot.py).*

```plantuml
@startuml
title Sơ đồ Hoạt động: Chat với trợ lý ChatBotAI

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Chat với Trợ lý ChatBotAI" {
  start
  :Bệnh nhân bấm vào biểu tượng Trợ lý AI y tế (AIAssistant Widget);
  :Khởi tạo phiên hội thoại (Session ID) và tải lịch sử trò chuyện;
  :Bệnh nhân nhập câu hỏi y tế, triệu chứng hoặc tìm kiếm bác sĩ;
  :Bấm gửi câu hỏi tới Chatbot Server (POST /generate_stream_chatbox);

  if (Nội dung câu hỏi hợp lệ?) then (Không)
    :Hệ thống báo lỗi;
    :Hiển thị thông báo "Vui lòng nhập câu hỏi hoặc triệu chứng cần tư vấn";
  else (Có)
    :Chatbot Server tiếp nhận và tải ngữ cảnh từ Session Manager;
    :Phân tích ngữ cảnh và phân loại ý định (PhoBERT Intent Classifier);
    if (Ý định cần tra cứu dữ liệu thực tế (Bác sĩ, Gói khám, Bệnh viện)?) then (Không)
      :Sử dụng tri thức y khoa cơ bản của mô hình ngôn ngữ LLM;
    else (Có)
      :Truy vấn dữ liệu từ Vector Store (ChromaDB) tìm thông tin liên quan;
      :Ghép dữ liệu trích xuất (RAG Context) vào System Prompt;
    endif
    :Gửi Prompt hoàn chỉnh tới mô hình Google Gemini;
    :Gemini sinh phản hồi dạng dòng chảy (Server-Sent Events Stream);
    :Giao diện Chatbot hiển thị phản hồi mượt mà từng ký tự kèm gợi ý đặt lịch;
    :Lưu lượt hội thoại mới vào bộ nhớ phiên làm việc;
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 9. Sơ đồ Hoạt động: Làm bài test Sức khỏe (`act Làm bài test Sức khỏe`)
*Ánh xạ mã nguồn: [`questionController.js`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/controllers/questionController.js), [`questionServices.js:submitAssessment`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/questionServices.js#L27).*

```plantuml
@startuml
title Sơ đồ Hoạt động: Làm bài test Sức khỏe

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Làm bài test Sức khỏe" {
  start
  :Bệnh nhân truy cập chuyên mục "Bài đánh giá sức khỏe";
  :Lựa chọn chuyên đề trắc nghiệm (Trầm cảm BDI-II, Răng miệng, Sức khỏe tổng quát);
  :Hệ thống tải danh sách câu hỏi và các phương án trả lời từ Database;
  :Bệnh nhân trả lời các câu hỏi trắc nghiệm;
  :Bấm nút "Nộp bài đánh giá";

  if (Đã hoàn thành đầy đủ tất cả câu hỏi bắt buộc?) then (Không)
    :Hệ thống cảnh báo;
    :Hiển thị thông báo "Vui lòng hoàn thành tất cả câu hỏi trước khi nộp bài";
  else (Có)
    :Gửi dữ liệu trả lời lên máy chủ (POST /api/submit-assessment);
    :Hệ thống tính tổng điểm bài đánh giá dựa trên trọng số cấu hình;
    :Đối chiếu điểm số với thang đo phân loại nguy cơ sức khỏe (Ranges Config);
    :Tạo đánh giá tổng quan và phân loại mức độ rủi ro y tế;
    :Lưu kết quả bài đánh giá vào Database (Bảng Assessments & Assessment_Details);
    if (Kết quả phát hiện nguy cơ sức khỏe ở mức Cảnh báo / Nghiêm trọng?) then (Không)
      :Hiển thị kết quả "Sức khỏe tốt" kèm lời khuyên dinh dưỡng và lối sống;
    else (Có)
      :Hiển thị cảnh báo rủi ro sức khỏe chi tiết;
      :Đề xuất chuyên khoa y tế và danh sách Bác sĩ chuyên môn phù hợp;
      :Cung cấp nút bấm liên kết trực tiếp để bệnh nhân đặt lịch hẹn khám ngay;
    endif
    :Lưu kết quả vào hồ sơ cá nhân để theo dõi sức khỏe định kỳ;
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 10. Sơ đồ Hoạt động: Quản lý Kho thuốc (`act Quản lý Kho thuốc`)
*Ánh xạ mã nguồn: [`medicineController.js`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/controllers/medicineController.js), [`medicineServices.js`](file:///d:/XuanDuc/CV/medical-appointment-system/backend/src/services/medicineServices.js), Bảng `Medicines`.*

```plantuml
@startuml
title Sơ đồ Hoạt động: Quản lý Kho thuốc

skinparam shadowing false
skinparam defaultFontName "Arial"
skinparam defaultFontSize 12
skinparam roundCorner 15
skinparam ArrowColor #333333
skinparam ActivityBorderColor #666666
skinparam ActivityBackgroundColor #F2F2F2
skinparam ActivityDiamondBorderColor #666666
skinparam ActivityDiamondBackgroundColor #FFFFFF

partition "act Quản lý Kho thuốc" {
  start
  :Nhân viên Dược / Bác sĩ truy cập phân hệ "Quản lý Kho thuốc";
  :Hệ thống truy vấn cơ sở dữ liệu và hiển thị danh mục thuốc (Bảng Medicines);
  :Người dùng chọn loại thao tác mong muốn;

  if (Người dùng chọn Thêm mới / Cập nhật thông tin thuốc?) then (Không)
    :Người dùng nhập từ khóa tìm kiếm (Tên thuốc, Hoạt chất, Đơn vị tính);
    :Hệ thống lọc dữ liệu và hiển thị danh sách thuốc phù hợp;
    if (Tìm thấy thuốc có sẵn trong kho?) then (Không)
      :Hệ thống thông báo;
      :Hiển thị "Không tìm thấy thuốc phù hợp trong danh mục";
    else (Có)
      :Hiển thị thông tin chi tiết (Đơn vị tính, Giá tiền, Công dụng);
      :Cho phép Bác sĩ chọn thuốc đưa vào đơn thuốc của Bệnh nhân;
    endif
  else (Có)
    :Nhập thông tin thuốc vào biểu mẫu (Tên thuốc, Đơn vị tính, Giá bán, Mô tả cách dùng);
    :Bấm nút "Lưu thông tin thuốc";
    if (Thông tin thuốc hợp lệ (Tên thuốc, Đơn vị và Giá tiền > 0)?) then (Không)
      :Hệ thống báo lỗi biểu mẫu;
      :Hiển thị cảnh báo "Vui lòng nhập đầy đủ tên thuốc và đơn giá hợp lệ";
    else (Có)
      :Ghi nhận bản ghi thuốc mới hoặc cập nhật bản ghi vào Database;
      :Làm mới danh mục kho dược trên giao diện;
      :Hiển thị thông báo "Lưu thông tin thuốc thành công";
    endif
  endif

  :Kết thúc quy trình;
  stop
}
@enduml
```

---

## 🛠️ Hướng dẫn vẽ và xuất hình trên draw.io (diagrams.net)

1. Truy cập [app.diagrams.net](https://app.diagrams.net).
2. Trên thanh menu, chọn: **Arrange** (Sắp xếp) ➡️ **Insert** (Chèn) ➡️ **Advanced** (Nâng cao) ➡️ **PlantUML...**
3. Copy toàn bộ khối mã của sơ đồ cần vẽ (từ `@startuml` đến `@enduml`) và dán vào hộp thoại.
4. Bấm **Insert**. Sơ đồ sẽ được tự động vẽ ra bảng vẽ với:
   - Khung bao góc gập `act ...`
   - Đúng duy nhất 1 điểm bắt đầu và 1 điểm kết thúc
   - Nhánh `Không` sang trái, nhánh `Có` sang phải
   - Các hình thoi hội tụ thu luồng chuẩn xác
   - Định dạng khối bo góc và màu sắc xám thanh lịch chuẩn UML.
