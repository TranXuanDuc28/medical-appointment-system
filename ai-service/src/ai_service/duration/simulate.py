"""MÔ PHỎNG thời lượng khám có kiểm soát – bám đúng cấu trúc hệ thống (bác sĩ, buổi khám, hàng đợi).

⚠️ Đây là DỮ LIỆU MÔ PHỎNG: các hệ số dưới đây là GIẢ ĐỊNH ghi rõ, lấy từ kinh nghiệm chung (ca khám mới lâu hơn tái khám,
người cao tuổi/trẻ nhỏ và ca nặng lâu hơn, bác sĩ nhiều kinh nghiệm nhanh hơn, hàng đợi dài thì bác sĩ khám nhanh hơn, càng cuối
buổi càng mệt...), KHÔNG phải số liệu bệnh viện thật. Mục đích: (1) có dữ liệu đúng hình dạng để huấn luyện và tích hợp vào hàng đợi,
(2) kiểm chứng quy trình ML. Khi hệ thống chạy thật, mô hình được tái huấn luyện từ log thật (`python -m ai_service export-real`).

Cấu trúc: buổi khám (session) = 1 bác sĩ × 1 ca (sáng/chiều) × 6–14 bệnh nhân khám tuần tự.
Thời lượng thật của bệnh nhân i:
    thời_lượng = nền[khoa] × mức_nặng × loại_khám × nguồn × tuổi × (1 + 0.08·bệnh_nền) × tốc_độ_bác_sĩ
                 × kinh_nghiệm × mệt_mỏi(giờ) × áp_lực_hàng_đợi × nhiễu_lognormal   (kẹp trong [3, 90] phút)
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ai_service.config import DATA_DIR, SEED
from ai_service.duration import schema as S

# ------------------------------- CÁC GIẢ ĐỊNH (nguồn sự thật duy nhất, báo cáo in lại từ đây) -------------------------------
BASE_MINUTES = {  # thời lượng nền (phút) của ca TB: khám mới, nặng vừa, người lớn
    "musculoskeletal": 14, "neurology": 22, "digestive": 15, "cardiology": 18,
    "ent": 10, "spine": 16, "respiratory": 14, "dentistry": 20,
}
SEVERITY_MULT = {"MILD": 0.82, "MODERATE": 1.0, "SEVERE": 1.40}
VISIT_MULT = {"NEW": 1.0, "FOLLOW_UP": 0.65}
SOURCE_MULT = {"BOOKED": 1.0, "WALK_IN": 1.12}  # vãng lai chưa có thông tin trước nên lâu hơn
AGE_MULT = {"child(≤6)": 1.15, "adult": 1.0, "elderly(≥65)": 1.25}
CHRONIC_PER_DISEASE = 0.08  # mỗi bệnh nền thêm 8%
EXPERIENCE_COEF = (1.12, 0.006, 30)  # 1.12 − 0.006·min(năm, 30): mới ra trường chậm hơn 12%, 30 năm nhanh hơn 6%
FATIGUE_PER_HOUR = 0.012  # mỗi giờ trong buổi khám chậm thêm 1.2%
PRESSURE = (4, 0.015, 0.85)  # hàng đợi > 4 người: nhanh thêm 1.5%/người, tối đa nhanh 15%
DOCTOR_SPEED_SIGMA = 0.08  # mỗi bác sĩ có hệ số tốc độ riêng (lognormal)
NOISE_SIGMA = 0.20  # nhiễu lognormal của từng ca
COMPLEX_CASE = (0.03, 1.6, 2.4)  # 3% ca phức tạp bất ngờ: nhân 1.6–2.4
DOCTORS_PER_DEPARTMENT = 6
SESSION_SIZE = (6, 14)
HIST_AVG_MISSING_RATE = 0.2  # 20% bác sĩ chưa có lịch sử đủ dài => thiếu `doctor_hist_avg_min`
HIST_AVG_NOISE = 0.08


def age_mult(age: float) -> float:
    return AGE_MULT["child(≤6)"] if age <= 6 else AGE_MULT["elderly(≥65)"] if age >= 65 else AGE_MULT["adult"]


def expected_minutes(row: dict, doctor_speed: float = 1.0) -> float:
    """Thời lượng KỲ VỌNG (chưa có nhiễu) theo các giả định – dùng cho mô phỏng và kiểm thử tính đơn điệu."""
    base, per_year, cap = EXPERIENCE_COEF
    start_hour = 8.0 if row["hour_of_day"] < 12.5 else 13.0
    pressure_free, per_person, floor = PRESSURE
    return (
        BASE_MINUTES[row["department"]]
        * SEVERITY_MULT[row["severity"]]
        * VISIT_MULT[row["visit_type"]]
        * SOURCE_MULT[row["source"]]
        * age_mult(row["age"])
        * (1 + CHRONIC_PER_DISEASE * row["chronic_count"])
        * doctor_speed
        * (base - per_year * min(row["doctor_experience_years"], cap))
        * (1 + FATIGUE_PER_HOUR * max(row["hour_of_day"] - start_hour, 0))
        * max(floor, 1 - per_person * max(row["queue_length"] - pressure_free, 0))
    )


def assumptions_markdown() -> str:
    """Bảng giả định (in vào báo cáo) lấy trực tiếp từ hằng số ở trên để không bao giờ lệch."""
    rows = [
        ("Thời lượng nền theo khoa (phút)", ", ".join(f"{S.DEPARTMENT_LABEL_VI[k]} {v}" for k, v in BASE_MINUTES.items())),
        ("Mức nặng", ", ".join(f"{k} ×{v}" for k, v in SEVERITY_MULT.items())),
        ("Loại khám", ", ".join(f"{k} ×{v}" for k, v in VISIT_MULT.items())),
        ("Nguồn", ", ".join(f"{k} ×{v}" for k, v in SOURCE_MULT.items())),
        ("Tuổi", ", ".join(f"{k} ×{v}" for k, v in AGE_MULT.items())),
        ("Bệnh nền", f"mỗi bệnh +{int(CHRONIC_PER_DISEASE * 100)}%"),
        ("Kinh nghiệm bác sĩ", f"{EXPERIENCE_COEF[0]} − {EXPERIENCE_COEF[1]}·min(năm, {EXPERIENCE_COEF[2]})"),
        ("Mệt mỏi trong buổi", f"+{FATIGUE_PER_HOUR * 100:.1f}% mỗi giờ"),
        ("Áp lực hàng đợi", f"hàng đợi > {PRESSURE[0]} người: nhanh thêm {PRESSURE[1] * 100:.1f}%/người, tối đa nhanh {int((1 - PRESSURE[2]) * 100)}%"),
        ("Tốc độ riêng từng bác sĩ", f"lognormal σ={DOCTOR_SPEED_SIGMA}"),
        ("Nhiễu từng ca", f"lognormal σ={NOISE_SIGMA}; {int(COMPLEX_CASE[0] * 100)}% ca phức tạp nhân {COMPLEX_CASE[1]}–{COMPLEX_CASE[2]}"),
        ("Giới hạn", f"{S.MIN_DURATION:.0f}–{S.MAX_DURATION:.0f} phút"),
    ]
    return "| Yếu tố | Giả định |\n|---|---|\n" + "\n".join(f"| {a} | {b} |" for a, b in rows)


def simulate(n_sessions: int = 3000, seed: int = SEED) -> pd.DataFrame:
    """Sinh bảng ca khám (một dòng/ca) có `session_id`, `doctor_id`, `position` và các đặc trưng + `duration_min`."""
    rng = np.random.default_rng(seed)

    # --- Đội ngũ bác sĩ ---
    doctors = []
    for dep in S.DEPARTMENTS:
        for _ in range(DOCTORS_PER_DEPARTMENT):
            exp = int(rng.integers(1, 36))
            speed = float(rng.lognormal(0, DOCTOR_SPEED_SIGMA))
            typical = BASE_MINUTES[dep] * speed * (EXPERIENCE_COEF[0] - EXPERIENCE_COEF[1] * min(exp, EXPERIENCE_COEF[2]))
            hist = typical * float(rng.lognormal(0, HIST_AVG_NOISE))
            doctors.append({"doctor_id": len(doctors) + 1, "department": dep, "exp": exp, "speed": speed,
                            "hist_avg": math.nan if rng.random() < HIST_AVG_MISSING_RATE else round(hist, 2)})

    rows = []
    for sid in range(1, n_sessions + 1):
        d = doctors[int(rng.integers(0, len(doctors)))]
        shift_start = 8.0 if rng.random() < 0.55 else 13.0
        size = int(rng.integers(SESSION_SIZE[0], SESSION_SIZE[1] + 1))
        clock = shift_start
        for pos in range(size):
            u = rng.random()
            age = int(rng.integers(1, 13)) if u < 0.15 else int(rng.integers(13, 65)) if u < 0.70 else int(rng.integers(65, 92))
            chronic = int(min(rng.poisson(age / 45), 5))
            row = {
                "department": d["department"],
                "gender": str(rng.choice(S.GENDERS, p=[0.48, 0.48, 0.04])),
                "severity": str(rng.choice(S.SEVERITIES, p=[0.45, 0.40, 0.15])),
                "visit_type": "NEW" if rng.random() < 0.6 else "FOLLOW_UP",
                "source": "WALK_IN" if rng.random() < 0.35 else "BOOKED",
                "age": age, "chronic_count": chronic, "doctor_experience_years": d["exp"],
                "hour_of_day": round(min(clock, 21.5), 2),
                "queue_length": max(size - pos - 1 + int(rng.poisson(1.0)), 0),
                "doctor_hist_avg_min": d["hist_avg"],
            }
            minutes = expected_minutes(row, d["speed"]) * float(rng.lognormal(0, NOISE_SIGMA))
            if rng.random() < COMPLEX_CASE[0]:
                minutes *= float(rng.uniform(COMPLEX_CASE[1], COMPLEX_CASE[2]))
            minutes = float(np.clip(minutes, S.MIN_DURATION, S.MAX_DURATION))
            rows.append({"session_id": sid, "doctor_id": d["doctor_id"], "position": pos, **row, "duration_min": round(minutes, 2)})
            clock += (minutes + 1.5) / 60.0  # 1.5 phút chuyển ca giữa 2 bệnh nhân
    return pd.DataFrame(rows)


def synthetic_path():
    return DATA_DIR / "synthetic" / "duration_sim.csv"


def load_or_generate(force: bool = False, n_sessions: int = 3000, seed: int = SEED) -> pd.DataFrame:
    p = synthetic_path()
    if force or not p.is_file():
        p.parent.mkdir(parents=True, exist_ok=True)
        simulate(n_sessions, seed).to_csv(p, index=False)
    return pd.read_csv(p)
