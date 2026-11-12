"""Cấu hình đường dẫn, hạt giống ngẫu nhiên và hằng số dùng chung."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # thư mục ai-service
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

SEED = 42  # mọi bước ngẫu nhiên đều dùng hạt giống này để kết quả tái lập được

KAGGLE_FILENAME = "smart_hospital_appointment_dataset.csv"


def kaggle_csv_path() -> Path:
    """Tìm file Kaggle: biến môi trường -> data/raw -> thư mục gốc dự án (cha của cha của medical-appointment-system)."""
    env = os.getenv("AI_KAGGLE_CSV")
    candidates = [Path(env)] if env else []
    candidates += [DATA_DIR / "raw" / KAGGLE_FILENAME, ROOT.parents[1] / KAGGLE_FILENAME]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(
        f"Không tìm thấy {KAGGLE_FILENAME}. Đặt vào {DATA_DIR / 'raw'} hoặc đặt AI_KAGGLE_CSV. Đã thử: "
        + ", ".join(str(c) for c in candidates)
    )


def ensure_dirs() -> None:
    for d in (DATA_DIR / "synthetic", DATA_DIR / "real", MODELS_DIR, FIGURES_DIR):
        d.mkdir(parents=True, exist_ok=True)
