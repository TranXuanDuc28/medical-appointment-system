"""Sinh bộ dữ liệu huấn luyện phân loại triệu chứng tiếng Việt từ từ vựng tự xây (lexicon.py).

Mỗi triệu chứng gốc được biến thành nhiều câu nói tự nhiên: thêm chủ ngữ ("tôi bị", "con tôi bị"...), thời gian ("đã 3 ngày"),
mức độ ("rất", "hơi"), và nhiễu bề mặt (viết thường, KHÔNG DẤU, gõ sai chính tả). Mỗi câu mang `group` = id triệu chứng gốc để lúc
đánh giá chia theo nhóm (các biến thể của cùng một triệu chứng không bao giờ nằm ở cả train lẫn test => không rò rỉ).
"""
from __future__ import annotations

import random

import pandas as pd

from ai_service.config import DATA_DIR, SEED
from ai_service.triage import lexicon as L
from ai_service.triage.rules import strip_accents

SUBJECTS = ["", "tôi bị ", "em bị ", "mình bị ", "bố tôi bị ", "mẹ tôi bị ", "con tôi bị ", "dạo này hay bị ", "mấy hôm nay bị ", "tôi thấy ", "bị "]
DURATIONS = ["", "", " khoảng 2 ngày nay", " đã 1 tuần", " từ hôm qua", " vài tháng nay", " từ sáng nay", " kéo dài 3 ngày", " mấy ngày rồi", " đã lâu"]
INTENSITY = ["", "", "", "rất ", "hơi ", "khá ", "thỉnh thoảng "]
ENDINGS = ["", "", "", ".", " ạ", " bác sĩ ơi", " không biết là bệnh gì"]

PER_PHRASE = 14  # số câu sinh cho mỗi triệu chứng gốc


def _typo(text: str, rng: random.Random) -> str:
    """Gõ sai: bỏ một ký tự hoặc đổi chỗ hai ký tự liền kề trong một từ dài."""
    words = text.split(" ")
    idx = [i for i, w in enumerate(words) if len(w) >= 4]
    if not idx:
        return text
    i = rng.choice(idx)
    w = words[i]
    j = rng.randrange(1, len(w) - 1)
    words[i] = w[:j] + w[j + 1:] if rng.random() < 0.5 else w[:j] + w[j + 1] + w[j] + w[j + 2:]
    return " ".join(words)


def make_variants(phrase: str, rng: random.Random, n: int = PER_PHRASE) -> list[str]:
    out: set[str] = set()
    tries = 0
    while len(out) < n and tries < n * 20:
        tries += 1
        text = f"{rng.choice(SUBJECTS)}{rng.choice(INTENSITY)}{phrase}{rng.choice(DURATIONS)}{rng.choice(ENDINGS)}".strip()
        if rng.random() < 0.3:
            text = strip_accents(text)  # người dùng gõ không dấu
        if rng.random() < 0.12:
            text = _typo(text, rng)
        if rng.random() < 0.15:
            text = text.upper() if rng.random() < 0.3 else text.capitalize()
        out.add(text)
    return sorted(out)


def build(seed: int = SEED) -> pd.DataFrame:
    rng = random.Random(seed)
    rows, gid = [], 0
    for label, phrases in L.SYMPTOMS.items():
        for phrase in phrases:
            gid += 1
            for text in make_variants(phrase, rng):
                rows.append({"text": text, "label": label, "group": gid, "base_phrase": phrase})
    return pd.DataFrame(rows)


def dataset_path():
    return DATA_DIR / "triage" / "symptoms_vi.csv"


def write(seed: int = SEED) -> pd.DataFrame:
    df = build(seed)
    p = dataset_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8")
    return df
