"""Hợp đồng dữ liệu của mô hình THỜI LƯỢNG KHÁM: đặc trưng, giá trị hợp lệ, giá trị mặc định, chuẩn hoá đầu vào.

Đây là giao diện chung giữa dữ liệu mô phỏng, dữ liệu thật xuất từ hàng đợi và request từ backend Node,
nên đặc trưng chỉ gồm thông tin BIẾT ĐƯỢC TẠI THỜI ĐIỂM bệnh nhân vào khám.
"""
from __future__ import annotations

import math
import unicodedata

# 8 chuyên khoa của hệ thống (khoá ASCII ổn định; tên hiển thị lấy từ DB)
DEPARTMENTS = ["musculoskeletal", "neurology", "digestive", "cardiology", "ent", "spine", "respiratory", "dentistry"]
DEPARTMENT_LABEL_VI = {
    "musculoskeletal": "Cơ xương khớp", "neurology": "Thần kinh", "digestive": "Tiêu hóa", "cardiology": "Tim mạch",
    "ent": "Tai mũi họng", "spine": "Cột sống", "respiratory": "Hô hấp - Phổi", "dentistry": "Nha khoa",
}


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", str(text).replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower().strip()


# Tên chuyên khoa trong DB (vi/en, không dấu, chữ thường) -> khoá
_ALIASES = {
    "co xuong khop": "musculoskeletal", "musculoskeletal": "musculoskeletal",
    "than kinh": "neurology", "nerve": "neurology", "neurology": "neurology",
    "tieu hoa": "digestive", "digest": "digestive", "digestive": "digestive", "gastroenterology": "digestive",
    "tim mach": "cardiology", "cardiovascular": "cardiology", "cardiology": "cardiology",
    "tai mui hong": "ent", "ent": "ent",
    "cot song": "spine", "spine": "spine",
    "ho hap - phoi": "respiratory", "ho hap": "respiratory", "respiratory - lungs": "respiratory", "respiratory": "respiratory", "pulmonology": "respiratory",
    "nha khoa": "dentistry", "dentistry": "dentistry", "dental": "dentistry",
}


def normalize_department(name) -> str | None:
    """Tên/khoá chuyên khoa bất kỳ -> khoá chuẩn; không nhận ra -> None."""
    if name is None:
        return None
    n = _norm(name)
    return n if n in DEPARTMENTS else _ALIASES.get(n)


SEVERITIES = ["MILD", "MODERATE", "SEVERE"]
VISIT_TYPES = ["NEW", "FOLLOW_UP"]
SOURCES = ["BOOKED", "WALK_IN"]
GENDERS = ["M", "F", "O"]

CATEGORICAL = ["department", "gender", "severity", "visit_type", "source"]
NUMERIC = ["age", "chronic_count", "doctor_experience_years", "hour_of_day", "queue_length", "doctor_hist_avg_min"]
FEATURES = CATEGORICAL + NUMERIC
TARGET = "duration_min"

# Giá trị dùng khi backend không có thông tin (và được báo lại trong `used_defaults`)
DEFAULTS = {
    "gender": "O", "severity": "MODERATE", "visit_type": "NEW", "source": "BOOKED", "age": 35, "chronic_count": 0,
    "doctor_experience_years": 8, "hour_of_day": 9.0, "queue_length": 0, "doctor_hist_avg_min": math.nan,
}
REQUIRED = ["department"]

_GENDER_ALIASES = {"m": "M", "male": "M", "nam": "M", "f": "F", "female": "F", "nu": "F", "nữ": "F", "o": "O", "other": "O", "khac": "O", "khác": "O"}

MIN_DURATION, MAX_DURATION = 3.0, 90.0  # phút – giới hạn hợp lý của một ca khám


def _num(raw: dict, key: str, lo: float, hi: float, as_int: bool = False):
    v = raw[key]
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' phải là số") from None
    if math.isnan(x) or not (lo <= x <= hi):
        raise ValueError(f"'{key}' phải nằm trong [{lo}, {hi}]")
    return int(round(x)) if as_int else x


def normalize_row(raw: dict) -> tuple[dict, list[str]]:
    """Kiểm tra + chuẩn hoá một yêu cầu dự đoán. Trả về (dòng đặc trưng đầy đủ, danh sách trường phải dùng giá trị mặc định).

    Ném ValueError (thông điệp tiếng Việt) khi dữ liệu sai; thiếu trường tuỳ chọn thì dùng DEFAULTS.
    """
    if not isinstance(raw, dict):
        raise ValueError("Yêu cầu phải là một đối tượng JSON")
    dep = normalize_department(raw.get("department"))
    if dep is None:
        raise ValueError(f"Không nhận ra chuyên khoa '{raw.get('department')}'. Hợp lệ: {', '.join(DEPARTMENTS)} (hoặc tên tiếng Việt trong hệ thống)")
    row: dict = {"department": dep}
    used: list[str] = []

    def present(k: str) -> bool:
        return k in raw and raw[k] is not None and raw[k] != ""

    for k in ("gender", "severity", "visit_type", "source"):
        if present(k):
            val = str(raw[k]).strip()
            if k == "gender":
                val = _GENDER_ALIASES.get(val.lower(), val.upper())
            else:
                val = val.upper().replace(" ", "_").replace("-", "_")
            allowed = {"gender": GENDERS, "severity": SEVERITIES, "visit_type": VISIT_TYPES, "source": SOURCES}[k]
            if val not in allowed:
                raise ValueError(f"'{k}' không hợp lệ: '{raw[k]}'. Hợp lệ: {', '.join(allowed)}")
            row[k] = val
        else:
            row[k] = DEFAULTS[k]
            used.append(k)

    bounds = {"age": (0, 120, True), "chronic_count": (0, 10, True), "doctor_experience_years": (0, 60, True),
              "hour_of_day": (5, 22, False), "queue_length": (0, 200, True), "doctor_hist_avg_min": (1, 120, False)}
    for k, (lo, hi, as_int) in bounds.items():
        if present(k):
            row[k] = _num(raw, k, lo, hi, as_int)
        else:
            row[k] = DEFAULTS[k]
            used.append(k)
    return row, used
