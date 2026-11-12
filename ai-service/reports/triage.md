# Báo cáo: phân loại triệu chứng → chuyên khoa

> Sinh tự động bởi `python -m ai_service train-triage` – phiên bản `20261112-ba578d04`.
> ⚠️ **Dữ liệu do nhóm tự xây** từ kiến thức y khoa phổ thông (không phải dữ liệu lâm sàng, chưa được bác sĩ kiểm định). Hệ thống chỉ **gợi ý chuyên khoa**, không chẩn đoán.

## 1. Dữ liệu và cách đánh giá
- 222 triệu chứng gốc cho 8 chuyên khoa, sinh thành **3,108 câu** (thêm chủ ngữ, thời gian, mức độ, KHÔNG DẤU, gõ sai).
- **Tầng 1 – chia theo nhóm:** các biến thể của cùng một triệu chứng gốc không bao giờ nằm ở cả train lẫn test (mô hình chưa từng thấy cụm triệu chứng test).
- **Tầng 2 – tập ngoài:** 64 câu viết tay tự nhiên, không sinh từ khuôn mẫu, không tham gia huấn luyện hay chọn ngưỡng.
- Mô hình: TF-IDF (ký tự 2–5 + từ 1–2) + Logistic Regression, C=10 chọn bằng GroupKFold 5-fold trên train.

## 2. Kết quả

| Tập | Top-1 | Top-3 | Macro-F1 | Số câu |
|---|---|---|---|---|
| Test chia theo nhóm | 0.7095 | 0.8587 | 0.7074 | 630 |
| **Tập ngoài viết tay** | **0.9375** | **0.9688** | **0.9384** | 64 |

**Cách đọc (quan trọng):**
- **Test chia theo nhóm = ước lượng BI QUAN.** Mô hình chưa từng thấy cụm triệu chứng đó, câu lại bị nhiễu nặng (không dấu, gõ sai), và có nhiều triệu chứng mơ hồ thuộc nhiều khoa.
- **Tập ngoài = ước lượng LẠC QUAN.** Câu do chính nhóm viết nên dễ trùng từ khoá với dữ liệu huấn luyện (thiên lệch tác giả). Hiệu năng với người dùng thật nhiều khả năng nằm **giữa hai con số**; muốn biết chắc cần câu của người dùng thật hoặc bác sĩ gán nhãn.
- **Top-3 cao hơn Top-1 rõ rệt** vì nhiều triệu chứng thuộc nhiều khoa (vd. đau lưng lan xuống chân: Cột sống / Thần kinh). Vì vậy hệ thống trả về **3 gợi ý** để bệnh nhân chọn, và kèm ngưỡng "không chắc chắn".

### Từng chuyên khoa (tập ngoài)
| Chuyên khoa | Precision | Recall | F1 | Số câu |
|---|---|---|---|---|
| Tim mạch | 0.727 | 1.0 | 0.842 | 8 |
| Nha khoa | 1.0 | 1.0 | 1.0 | 8 |
| Tiêu hóa | 1.0 | 1.0 | 1.0 | 8 |
| Tai mũi họng | 1.0 | 0.75 | 0.857 | 8 |
| Cơ xương khớp | 1.0 | 1.0 | 1.0 | 8 |
| Thần kinh | 0.875 | 0.875 | 0.875 | 8 |
| Hô hấp - Phổi | 1.0 | 1.0 | 1.0 | 8 |
| Cột sống | 1.0 | 0.875 | 0.933 | 8 |

### Ma trận nhầm lẫn (tập ngoài)
| Thực tế \ Dự đoán | Tim mạch | Nha khoa | Tiêu hóa | Tai mũi họng | Cơ xương khớp | Thần kinh | Hô hấp - Phổi | Cột sống |
|---|---|---|---|---|---|---|---|---|
| **Tim mạch** | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Nha khoa** | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Tiêu hóa** | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 |
| **Tai mũi họng** | 1 | 0 | 0 | 6 | 0 | 1 | 0 | 0 |
| **Cơ xương khớp** | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 |
| **Thần kinh** | 1 | 0 | 0 | 0 | 0 | 7 | 0 | 0 |
| **Hô hấp - Phổi** | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| **Cột sống** | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |

### Các câu dự đoán sai (tập ngoài)
| Câu | Đúng | Dự đoán | Xác suất |
|---|---|---|---|
| Mấy tuần nay tôi trằn trọc không ngủ được, ban ngày thì mệt rã rời | Thần kinh | Tim mạch | 0.41 |
| Con tôi hay chảy máu cam vào ban đêm | Tai mũi họng | Tim mạch | 0.75 |
| Giọng tôi khàn đặc, nói chuyện khó khăn mấy ngày rồi | Tai mũi họng | Thần kinh | 0.67 |
| Bác sĩ chụp phim nói tôi bị thoát vị đĩa đệm | Cột sống | Tim mạch | 0.37 |

## 3. Ngưỡng "không chắc chắn"
Khi xác suất cao nhất thấp hơn ngưỡng, hệ thống không đoán mà đề nghị bệnh nhân mô tả thêm / chọn khoa thủ công. Ngưỡng được chọn trên tập test theo nhóm: **0.6**.

| Ngưỡng | Phủ (test nhóm) | Chính xác Top-1 khi trả lời | Phủ (tập ngoài) | Chính xác Top-1 khi trả lời |
|---|---|---|---|---|
| 0.0 | 1.0 | 0.71 | 1.0 | 0.938 |
| 0.2 | 0.994 | 0.711 | 1.0 | 0.938 |
| 0.3 | 0.9 | 0.727 | 1.0 | 0.938 |
| 0.4 | 0.784 | 0.755 | 0.984 | 0.952 |
| 0.5 | 0.686 | 0.815 | 0.938 | 0.967 |
| 0.6 | 0.622 | 0.842 | 0.922 | 0.966 |

## 4. Luật an toàn chạy trước mô hình
Dấu hiệu cấp cứu (đau thắt ngực lan, khó thở nặng, nghi đột quỵ, co giật/ngất, nôn ra máu, đau đầu dữ dội đột ngột, ngộ độc, ý định tự hại...) được nhận diện bằng **luật cứng**, ưu tiên an toàn (thà báo nhầm còn hơn bỏ sót) và **không bị mô hình ghi đè**. Mức: `EMERGENCY` (gọi cấp cứu/đến ngay), `URGENT` (khám trong ngày), `ROUTINE`.
