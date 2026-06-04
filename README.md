# Medical Appointment System

Hệ thống đặt lịch khám bệnh trực tuyến toàn diện, bao gồm Backend (Node.js & Express), Frontend (React) và Chatbot hỗ trợ.

## 🌟 Tổng quan dự án

Dự án này được thiết kế để quản lý việc đặt lịch khám, hồ sơ bệnh nhân, và hỗ trợ tư vấn qua chatbot. Hệ thống cung cấp giao diện cho cả Bệnh nhân, Bác sĩ và Quản trị viên.

---

## 🗺️ Sơ đồ kiến trúc & Luồng hoạt động

### 1. Sơ đồ kiến trúc hệ thống (System Architecture)
Sự tương tác giữa Client, Backend Services, AI Service và các dịch vụ bên thứ ba (Third-party APIs):

```mermaid
graph TD
  %% Client Layer
  ReactJS["React.js SPA (Frontend)"]

  %% Backend Layer
  subgraph Backend_Services["Backend Services"]
    NodeJS["Node.js & Express (API)"]
    SocketIO["Socket.io (Realtime Sync)"]
    MySQL["MySQL Database"]
  end

  %% AI Layer
  subgraph AI_Service["AI Chatbot Microservice"]
    Flask["Flask API Server"]
    PhoBERT["PhoBERT (Local Intent Classifier)"]
    FAISS["FAISS Vector DB (RAG)"]
  end

  %% External APIs
  Gemini["Google Gemini API (LLM)"]
  VietQR["VietQR API (MBBank Payment)"]
  Gmail["Gmail SMTP (Email Notifications)"]

  %% Interactions
  ReactJS <-->|"HTTP REST API"| NodeJS
  ReactJS <-->|"WebSockets"| SocketIO
  ReactJS <-->|"HTTP REST (Chat)"| Flask

  NodeJS <-->|"Sequelize ORM"| MySQL
  NodeJS -->|"Gọi API sinh QR Code"| VietQR
  NodeJS -->|"Gửi email kích hoạt & đơn thuốc"| Gmail

  Flask -->|"Phân loại ý đồ câu hỏi"| PhoBERT
  Flask -->|"Tìm tài liệu liên quan"| FAISS
  Flask <-->|"Gửi Context + Prompt"| Gemini
```

### 2. Luồng xử lý của Chatbot AI (RAG & Classification Pipeline)
Quy trình lọc câu hỏi không liên quan đến y tế và xử lý RAG trước khi gửi tới Gemini:

```mermaid
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

---

Để xem chi tiết và đầy đủ **10 luồng nghiệp vụ toàn hệ thống** (bao gồm luồng Đăng nhập JWT, đặt lịch, xác thực email, thanh toán VietQR, chat realtime Socket.io, đồng bộ Vector DB FAISS, khảo sát sức khỏe...), vui lòng truy cập tài liệu:

👉 **[Sơ đồ 10 luồng nghiệp vụ hệ thống (System Workflows)](docs/workflows.md)**

---

## 🏗️ Cấu trúc thư mục

Dự án được cấu trúc theo mô hình Microservices/Monorepo phân tách rõ ràng các thành phần Client, Backend API và AI Service:

```text
medical-appointment-system/
├── backend/                  # Node.js Backend API (Express & Sequelize)
│   ├── src/
│   │   ├── config/           # Cấu hình Database & App
│   │   ├── controllers/      # Hàm xử lý request (User, Doctor, Patient...)
│   │   ├── middleware/       # Middleware xác thực JWT, phân quyền RBAC
│   │   ├── models/           # Định nghĩa các Model Sequelize (Booking, Doctor...)
│   │   ├── services/         # Logic nghiệp vụ (Gửi email, thanh toán VietQR...)
│   │   ├── socket/           # Xử lý đặt lịch thời gian thực (Socket.io)
│   │   └── route/            # Định nghĩa các đầu Endpoint API
│   └── package.json
├── frontend/                 # React.js Client SPA
│   ├── src/
│   │   ├── components/       # Các Component dùng chung (Header, Footer...)
│   │   ├── containers/       # Các trang quản trị & người dùng (System, Patient, Doctor)
│   │   ├── store/            # Quản lý State toàn cục bằng Redux (Actions, Reducers)
│   │   └── utils/            # Các hàm tiện ích & Hằng số
│   └── package.json
└── chatbot/                  # Python Flask Service (AI Chatbot RAG)
    ├── app/                  # Chứa các Route API của Chatbot
    ├── core/                 # Pipeline xử lý RAG & Phân loại câu hỏi
    │   ├── classifier/       # Bộ lọc PhoBERT nhận diện câu hỏi y khoa
    │   ├── data/             # WebDataManager đồng bộ dữ liệu từ Node.js sang FAISS
    │   ├── llm/              # Kết nối với Gemini API
    │   └── vector_store/     # Quản lý Vector DB FAISS & Embeddings
    ├── finetune_phobert.py   # Script huấn luyện PhoBERT (Colab/Local GPU)
    ├── medical_dataset.csv   # Dữ liệu 2.800 mẫu tiếng Việt dùng để train PhoBERT
    ├── main.py               # Điểm khởi chạy của Flask Server
    └── requirements.txt      # Danh sách thư viện Python cần thiết
```

## 🚀 Hướng dẫn nhanh

Để chạy toàn bộ hệ thống, bạn cần khởi động cả Backend NodeJS, Frontend và Chatbot:

### 1. Khởi động Backend (Node.js & Express)
Vào thư mục `backend` và làm theo các bước:
- Cần cài đặt: Node.js, MySQL.
- Lệnh: `npm install` && `npm run dev`.
- Chạy tại: `http://localhost:6969`.

### 2. Khởi động Frontend (React.js)
Vào thư mục `frontend` và làm theo các bước:
- Cần cài đặt: Node.js, npm/yarn.
- Lệnh: `npm install` && `npm start`.
- Chạy tại: `http://localhost:3000`.

### 3. Khởi động Chatbot (Python Flask)
Vào thư mục `chatbot` và làm theo các bước:
- Cần cài đặt: Python 3.8+, PyTorch, FAISS.
- Lệnh: `pip install -r requirements.txt` && `python main.py`.
- Chạy tại: `http://localhost:5002`.

## 🛠️ Công nghệ sử dụng

- **Frontend**: React.js, Redux, SCSS, Bootstrap.
- **Backend**: Node.js, Express.js, Sequelize ORM.
- **Database**: MySQL.
- **AI & Chatbot**: Python Flask, PhoBERT, FAISS Vector DB, Gemini API.
- **Khác**: Socket.io (Đồng bộ thời gian thực), Nodemailer (Gửi email đơn thuốc PDF), VietQR API (Tạo mã QR thanh toán).

---
*Developed with ❤️ by TranXuanDucIT*