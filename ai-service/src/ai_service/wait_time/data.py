"""Nạp và làm sạch dataset Kaggle *Smart Healthcare Patient Appointment & Waiting Time*.

Quy tắc CHỐNG RÒ RỈ DỮ LIỆU (data leakage): chỉ dùng đặc trưng biết được TẠI THỜI ĐIỂM ĐẶT LỊCH / ĐẾN KHÁM.
Các cột phát sinh SAU khi khám (hoá đơn, điểm hài lòng, kết quả lịch hẹn) bị loại, nếu không mô hình "gian lận"
(ví dụ điểm hài lòng có tương quan −0,82 với thời gian chờ chỉ vì bệnh nhân chờ lâu thì chấm điểm thấp).
"""
from __future__ import annotations

import pandas as pd

from ai_service.common.registry import file_sha256
from ai_service.config import kaggle_csv_path

TARGET = "waiting_time_minutes"
ID_COLUMN = "patient_id"

# Phát sinh sau khi khám -> không được đưa vào đặc trưng
LEAKY_COLUMNS = [
    "patient_satisfaction_score",  # chấm điểm sau khi khám (phụ thuộc chính thời gian chờ)
    "total_bill",
    "medicine_cost",
    "test_cost",  # hoá đơn chỉ có sau khám
    "appointment_status",  # Completed / No Show / Cancelled: kết quả sau cùng
]
# `symptoms` ánh xạ 1-1 với `department` (10 giá trị <-> 10 khoa) nên là cột dư thừa
REDUNDANT_COLUMNS = ["symptoms"]

CATEGORICAL = [
    "gender", "city", "chronic_disease", "appointment_type", "department",
    "severity_level", "insurance", "appointment_day", "appointment_month",
]
NUMERIC = [
    "age", "bmi", "doctor_experience_years", "consultation_fee", "booking_to_appointment_days",
    "previous_appointments", "missed_previous_appointments", "hospital_rating", "emergency_case",
]
FEATURES = CATEGORICAL + NUMERIC


def load_raw() -> pd.DataFrame:
    # keep_default_na=False: pandas mặc định coi chuỗi "None" là giá trị thiếu, nhưng ở cột `chronic_disease`
    # "None" nghĩa là "không có bệnh nền" (một giá trị hợp lệ, chiếm ~45% dòng).
    df = pd.read_csv(kaggle_csv_path(), keep_default_na=False, na_values=[""])
    if df[ID_COLUMN].duplicated().any():
        raise ValueError("patient_id bị trùng – dataset không đúng định dạng mong đợi")
    return df


def dataset_fingerprint() -> str:
    """Băm nội dung file để báo cáo/mô hình ghi lại đã huấn luyện trên đúng dữ liệu nào."""
    return file_sha256(kaggle_csv_path())


def split_xy(df: pd.DataFrame, include_leaky: bool = False) -> tuple[pd.DataFrame, pd.Series]:
    """Trả về (X, y). `include_leaky=True` chỉ dùng để MINH HOẠ rò rỉ trong báo cáo, không dùng để triển khai."""
    cols = FEATURES + (["patient_satisfaction_score", "total_bill", "medicine_cost", "test_cost"] if include_leaky else [])
    return df[cols].copy(), df[TARGET].astype(float)
