# AI Service

Dịch vụ AI của hệ thống đặt lịch khám và quản lý hàng đợi: **dự đoán thời lượng khám** (để tính ETA hàng đợi), **gợi ý chuyên khoa từ triệu chứng tiếng Việt** kèm **luật cấp cứu**, và phần nghiên cứu **dự đoán thời gian chờ** trên dataset Kaggle.

> **Trung thực về dữ liệu** (đọc trước khi trích số liệu vào báo cáo)
> - Dataset Kaggle có dấu hiệu **tổng hợp**: thời gian chờ gần như chỉ phụ thuộc mức độ nặng + nhiễu; mục tiêu cũ của đề cương (MAE ≤ 2,5 phút, R² ≥ 0,85) **không đạt được bằng đặc trưng hợp lệ** (xem `reports/wait_time_kaggle.md`).
> - Mô hình thời lượng khám được huấn luyện trên **dữ liệu mô phỏng có kiểm soát** (giả định ghi rõ trong `reports/duration_model.md`). Khi hệ thống chạy thật phải **tái huấn luyện từ log thật** (xem [Tái huấn luyện](#tái-huấn-luyện-từ-log-thật)).
> - Bộ triệu chứng tiếng Việt do **nhóm tự xây**, chưa bác sĩ kiểm định. Dịch vụ chỉ **gợi ý**, không chẩn đoán.

## Kết quả chính

| Thành phần | Kết quả | Báo cáo |
|---|---|---|
| Thời gian chờ (Kaggle) | Giảm **39,7%** sai số so với đoán trung bình (MAE 12,8 → 7,7). Trần của dữ liệu ≈ MAE 7,7; mô hình phức tạp không hơn "đoán theo mức nặng" | [`reports/wait_time_kaggle.md`](reports/wait_time_kaggle.md) |
| Thời lượng khám (mô phỏng) | MAE từng ca **3,1 phút** vs 6,5 (cố định 15'); sai số **ETA giảm 65,7%** (22,7 → 7,8 phút); khoảng dự đoán p10–p90 phủ 80,4% | [`reports/duration_model.md`](reports/duration_model.md) |
| Phân loại triệu chứng | Top-1/Top-3: **71% / 86%** (test chia theo nhóm, ước lượng bi quan) và **94% / 97%** (tập ngoài do nhóm viết, ước lượng lạc quan); luật cấp cứu chạy trước mô hình | [`reports/triage.md`](reports/triage.md) |

## Cấu trúc

```
ai-service/
├── README.md · requirements.txt (khoảng phiên bản) · requirements.lock.txt (bản đã kiểm thử) · pyproject.toml · .env.example
├── src/ai_service/
│   ├── config.py                    đường dẫn, hạt giống (SEED=42), tìm dataset
│   ├── cli.py                       python -m ai_service <lệnh>
│   ├── common/                      metrics.py (MAE/RMSE/R²/bootstrap CI) · registry.py (kho mô hình có phiên bản) · plots.py
│   ├── wait_time/                   [Kaggle] data.py (chống rò rỉ) · train.py (so sánh mô hình + báo cáo)
│   ├── duration/                    [tích hợp hàng đợi] schema.py (hợp đồng đặc trưng) · simulate.py (giả định) · model.py ·
│   │                                train.py · eta_simulation.py · predictor.py · export_real.py (log thật → dữ liệu huấn luyện)
│   ├── triage/                      lexicon.py (từ vựng + luật cấp cứu) · build_dataset.py · rules.py · train.py · predictor.py
│   └── serve/app.py                 FastAPI
├── data/   raw/ (Kaggle, không commit) · synthetic/ (mô phỏng, không commit) · real/ (log thật, không commit) · triage/ (do nhóm xây, có commit)
├── models/ <loại>/<phiên bản>/{model.joblib, metadata.json} + <loại>/current.json   (commit để chạy ngay sau khi clone)
├── reports/ báo cáo Markdown + JSON + figures/ (sinh tự động bởi lệnh train-*)
└── tests/  107 test (chỉ số, schema, mô phỏng, suy luận, luật cấp cứu, API, dữ liệu thật)
```

## Chạy nhanh

```powershell
cd medical-appointment-system\ai-service
py -3.10 -m venv .venv
.venv\Scripts\pip install -r requirements.txt          # hoặc -r requirements.lock.txt để đúng phiên bản đã kiểm thử
$env:PYTHONPATH = "src"                                 # (hoặc: pip install -e .)

python -m ai_service train-all                          # ~5 phút: huấn luyện cả 3 mô hình + sinh báo cáo
python -m ai_service serve                              # http://127.0.0.1:8001  (docs tự động tại /docs)
python -m pytest                                        # 107 test
```

Dataset Kaggle: đặt `smart_hospital_appointment_dataset.csv` vào `data/raw/` (hoặc biến `AI_KAGGLE_CSV`). Mô hình đã huấn luyện có sẵn trong `models/`, nên **chỉ cần `serve`** nếu không muốn huấn luyện lại.

| Lệnh | Việc làm |
|---|---|
| `simulate` | sinh dữ liệu mô phỏng thời lượng khám |
| `train-wait` | pipeline Kaggle: loại cột rò rỉ → CV → so sánh mô hình → báo cáo |
| `train-duration [--source synthetic\|real] [--regenerate]` | mô hình thời lượng + khoảng p10–p90 + mô phỏng ETA |
| `build-triage` · `train-triage` | sinh dữ liệu triệu chứng · huấn luyện + đánh giá 2 tầng |
| `export-real` | xuất ca khám thật từ MySQL (`queue_tickets` đã DONE) |
| `serve [--port]` | dịch vụ HTTP |
| `triage "<câu>"` · `predict --department "Tim mạch" ...` | thử nhanh |

## Quy trình ML (áp dụng cho cả ba mô hình)

1. **Hợp đồng dữ liệu** (`duration/schema.py`): chỉ dùng đặc trưng **biết được lúc check-in**; mọi đầu vào được kiểm tra, trường thiếu dùng giá trị mặc định và được **báo lại** (`used_defaults`).
2. **Chống rò rỉ:** loại cột phát sinh sau khi khám (hoá đơn, điểm hài lòng, kết quả lịch hẹn); chia train/test **theo buổi khám** (thời lượng) hoặc **theo nhóm triệu chứng gốc** (triage); lịch sử bác sĩ chỉ dùng các ca *trước* ca hiện tại.
3. **Chọn mô hình bằng kiểm định chéo theo nhóm trên train**, tập test chạm **một lần**; luôn so với baseline; chọn **mô hình đơn giản nhất trong ngưỡng sai số** (0,5–1%).
4. **Đánh giá đầy đủ:** MAE, RMSE, R², MedAE, sai số P90, khoảng tin cậy bootstrap 95%, độ phủ của khoảng dự đoán; ở mức hệ thống còn đo **sai số ETA** so với cách cố định 15 phút.
5. **Tái lập:** hạt giống cố định, phiên bản mô hình = ngày + hash(dữ liệu, tham số), `metadata.json` ghi dataset sha256, đặc trưng, chỉ số, cảnh báo.
6. **An toàn:** luật cứng cho dấu hiệu cấp cứu chạy trước mô hình, không bị ghi đè; mô hình trả `uncertain` khi xác suất thấp; luôn kèm `disclaimer`.

## API (cho backend Node gọi nội bộ)

Đặt `AI_SERVICE_TOKEN` thì mọi endpoint (trừ `/health`) cần header `X-AI-Token`. Backend **phải có phương án dự phòng** (trung bình lịch sử của bác sĩ) khi gọi lỗi/quá hạn.

```http
GET  /health            → {"status":"ok","models":{"duration":"20261112-…","triage":"20261112-…"}}
GET  /model-info        → siêu dữ liệu 2 mô hình (chỉ số, đặc trưng, cảnh báo dữ liệu mô phỏng)

POST /predict-duration
{"items":[{"department":"Tim mạch","severity":"SEVERE","visit_type":"NEW","source":"BOOKED","age":70,
           "chronic_count":2,"doctor_experience_years":12,"hour_of_day":9.5,"queue_length":6,"doctor_hist_avg_min":17.5}]}
→ {"model_version":"…","predictions":[{"duration_min":27.5,"p10_min":20.9,"p90_min":36.3,
                                       "used_defaults":["gender"],"confidence":"high","model_version":"…"}]}
   chỉ `department` là bắt buộc (tên tiếng Việt/Anh trong hệ thống hoặc khoá: cardiology, neurology, digestive, musculoskeletal,
   spine, respiratory, ent, dentistry); tối đa 200 phần tử/lần; sai dữ liệu → 422 kèm "Phần tử #i: …"

POST /triage   {"text":"đau thắt ngực lan ra vai trái, vã mồ hôi"}
→ {"urgency":"EMERGENCY","recommendation":"CALL_EMERGENCY","advice":"…gọi cấp cứu 115…",
   "predictions":[{"specialty_key":"cardiology","specialty_vi":"Tim mạch","probability":0.80}, …3 gợi ý],
   "uncertain":false,"uncertain_hint":null,"model_version":"…","disclaimer":"…"}
   urgency: EMERGENCY (gọi 115) | URGENT (khám trong ngày) | ROUTINE;  recommendation: CALL_EMERGENCY | SAME_DAY | BOOK
```

Cắm vào hàng đợi của backend: `queueEta.setDurationPredictor(fn)` (xem `backend/QUEUE_ENGINE.md`), `fn` gọi `/predict-duration` và trả `duration_min`; lỗi/quá hạn thì trả `null` để ETA quay về trung bình lịch sử.

## Tái huấn luyện từ log thật

Khi hàng đợi đã chạy thật (mỗi ca `DONE` có giờ bắt đầu/kết thúc trong `queue_tickets`):

```powershell
python -m ai_service export-real                 # → data/real/duration_from_queue.csv (đặc trưng đúng hợp đồng, không rò rỉ nhãn)
python -m ai_service train-duration --source real # cần ≥ 200 ca; báo cáo ghi rõ nguồn dữ liệu = real
```
Mô hình mới được lưu thành phiên bản mới và đặt `current.json`; muốn quay lại bản cũ chỉ cần sửa `current.json`. So sánh MAE ETA trong báo cáo với bản mô phỏng để quyết định có triển khai hay không.

## Giới hạn đã biết
- Hiệu năng thời lượng khám trên dữ liệu thật **chưa biết**; số liệu hiện tại phản ánh khả năng học lại các giả định mô phỏng.
- Chưa có đặc trưng `visit_type` thật (schema chưa lưu tái khám) → khi xuất log thật mặc định `NEW`; `severity` lấy từ `symptom_intakes` nếu có.
- Phân loại triệu chứng: các triệu chứng đa khoa (đau lưng lan chân, đau ngực khi hít sâu...) vốn mơ hồ nên luôn trả top-3; từ vựng chỉ phủ 8 chuyên khoa hiện có.
