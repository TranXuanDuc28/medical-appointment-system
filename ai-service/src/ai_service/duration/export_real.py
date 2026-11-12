"""Xuất dữ liệu THẬT từ hàng đợi (queue_tickets đã DONE) thành bảng huấn luyện đúng hợp đồng đặc trưng (schema.py).

Chạy khi hệ thống đã có đủ ca khám thật:  python -m ai_service export-real   ->  data/real/duration_from_queue.csv
rồi:                                      python -m ai_service train-duration --source real

Phần dựng đặc trưng (`build_frame`) là hàm thuần để kiểm thử không cần DB.
"""
from __future__ import annotations

import os
import re

import numpy as np
import pandas as pd

from ai_service.config import DATA_DIR
from ai_service.duration import schema as S

QUERY = """
SELECT t.id AS ticket_id, t.doctor_id, t.ticket_date, t.shift, t.source, t.check_in_at, t.started_at, t.finished_at,
       dp.years_of_experience, st.name AS specialty_vi,
       pp.date_of_birth, pp.gender_code, pp.chronic_conditions, si.severity
FROM queue_tickets t
JOIN doctor_profiles dp ON dp.doctor_id = t.doctor_id
JOIN specialty_translations st ON st.specialty_id = dp.specialty_id AND st.lang = 'vi'
LEFT JOIN patient_profiles pp ON pp.id = t.patient_profile_id
LEFT JOIN symptom_intakes si ON si.booking_id = t.booking_id
WHERE t.status = 'DONE' AND t.started_at IS NOT NULL AND t.finished_at IS NOT NULL
"""

SEVERITY_MAP = {"MILD": "MILD", "MODERATE": "MODERATE", "SEVERE": "SEVERE"}
MIN_REAL_MINUTES, MAX_REAL_MINUTES = 1.0, 180.0  # loại ca bấm nhầm / quên bấm "hoàn thành"


def _chronic_count(text) -> int:
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return 0
    return min(len([p for p in re.split(r"[,;\n]", str(text)) if p.strip()]), 10)


def build_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Biến các dòng vé DONE (kết quả QUERY) thành bảng đặc trưng + nhãn `duration_min` + `session_id`, `position`."""
    df = raw.copy()
    for c in ("check_in_at", "started_at", "finished_at"):
        df[c] = pd.to_datetime(df[c])
    df["ticket_date"] = pd.to_datetime(df["ticket_date"])
    df["duration_min"] = (df["finished_at"] - df["started_at"]).dt.total_seconds() / 60.0
    df = df[(df["duration_min"] >= MIN_REAL_MINUTES) & (df["duration_min"] <= MAX_REAL_MINUTES)].copy()
    df["department"] = df["specialty_vi"].map(S.normalize_department)
    df = df[df["department"].notna()].copy()
    if df.empty:
        return pd.DataFrame(columns=S.FEATURES + [S.TARGET, "session_id", "position"])

    dob = pd.to_datetime(df["date_of_birth"], errors="coerce")
    df["age"] = ((df["ticket_date"] - dob).dt.days / 365.25).round().clip(0, 120).fillna(S.DEFAULTS["age"]).astype(int)
    df["gender"] = df["gender_code"].where(df["gender_code"].isin(S.GENDERS), S.DEFAULTS["gender"])
    df["severity"] = df["severity"].map(SEVERITY_MAP).fillna(S.DEFAULTS["severity"])
    df["visit_type"] = "NEW"  # chưa có dữ liệu tái khám trong schema hiện tại
    df["source"] = df["source"].where(df["source"].isin(S.SOURCES), "BOOKED")
    df["chronic_count"] = df["chronic_conditions"].map(_chronic_count)
    df["doctor_experience_years"] = pd.to_numeric(df["years_of_experience"], errors="coerce").fillna(S.DEFAULTS["doctor_experience_years"]).astype(int)
    df["hour_of_day"] = (df["started_at"].dt.hour + df["started_at"].dt.minute / 60.0).round(2)

    # Buổi khám = bác sĩ × ngày × ca; vị trí = thứ tự bắt đầu khám trong buổi
    df = df.sort_values(["doctor_id", "ticket_date", "shift", "started_at"])
    keys = ["doctor_id", "ticket_date", "shift"]
    df["session_id"] = df.groupby(keys).ngroup() + 1
    df["position"] = df.groupby(keys).cumcount()

    # queue_length = số bệnh nhân của cùng bác sĩ/ngày đã check-in nhưng chưa được khám tại thời điểm bắt đầu ca này
    ql = []
    for _, g in df.groupby(["doctor_id", "ticket_date"]):
        starts, checkins = g["started_at"].to_numpy(), g["check_in_at"].to_numpy()
        ql.extend((int(np.sum((checkins <= s) & (starts > s)))) for s in starts)
    order = df.groupby(["doctor_id", "ticket_date"]).ngroup().to_numpy()
    tmp = pd.DataFrame({"g": order, "ql": ql}, index=df.sort_values(["doctor_id", "ticket_date"]).index)
    df["queue_length"] = tmp["ql"].reindex(df.index).to_numpy()

    # Lịch sử trung bình của bác sĩ: chỉ dùng các ca TRƯỚC ca hiện tại (tránh rò rỉ nhãn)
    df = df.sort_values(["doctor_id", "started_at"])
    prior = df.groupby("doctor_id")["duration_min"].transform(lambda s: s.shift(1).expanding(min_periods=5).mean())
    df["doctor_hist_avg_min"] = prior.round(2)

    cols = S.FEATURES + [S.TARGET, "session_id", "position", "doctor_id"]
    return df[cols].sort_values(["session_id", "position"]).reset_index(drop=True)


def export(path=None) -> tuple[pd.DataFrame, str]:
    import pymysql  # chỉ cần khi xuất từ DB

    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")), user=os.getenv("DB_USERNAME", ""),
        password=os.getenv("DB_PASSWORD", ""), database=os.getenv("DB_DATABASE_NAME", "webhealthcare_v2"), charset="utf8mb4",
    )
    try:
        raw = pd.read_sql(QUERY, conn)
    finally:
        conn.close()
    frame = build_frame(raw)
    out = path or (DATA_DIR / "real" / "duration_from_queue.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    return frame, str(out)
