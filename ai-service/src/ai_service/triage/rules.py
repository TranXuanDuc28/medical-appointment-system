"""Luật cứng nhận diện cấp cứu / khẩn – chạy TRƯỚC mô hình học máy.

Triết lý an toàn: với dấu hiệu nguy hiểm, thà cảnh báo nhầm còn hơn bỏ sót; kết quả của luật KHÔNG phụ thuộc xác suất của mô hình
và không thể bị mô hình "ghi đè". Hệ thống chỉ gợi ý hướng xử trí, không chẩn đoán.
"""
from __future__ import annotations

import re
import unicodedata

from ai_service.triage import lexicon as L

EMERGENCY, URGENT, ROUTINE = "EMERGENCY", "URGENT", "ROUTINE"


def strip_accents(text: str) -> str:
    t = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def normalize_text(text: str) -> str:
    """Bỏ dấu, chữ thường, bỏ ký tự đặc biệt, gom khoảng trắng – dùng cho cả luật lẫn mô hình."""
    t = strip_accents(str(text)).lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


_EMERGENCY = [(label, [re.compile(p) for p in pats]) for label, pats in L.EMERGENCY_PATTERNS]
_URGENT = [(label, [re.compile(p) for p in pats]) for label, pats in L.URGENT_PATTERNS]
_ACCENTED = [(label, re.compile(p)) for label, p in L.EMERGENCY_ACCENTED]


def assess_urgency(text: str) -> tuple[str, list[str]]:
    """Trả về (mức khẩn, lý do). Cấp cứu > khẩn > thường."""
    norm = normalize_text(text)
    lowered = str(text).lower()
    reasons = [label for label, pats in _EMERGENCY if any(p.search(norm) for p in pats)]
    reasons += [label for label, pat in _ACCENTED if pat.search(lowered) and label not in reasons]
    if reasons:
        return EMERGENCY, reasons
    urgent = [label for label, pats in _URGENT if any(p.search(norm) for p in pats)]
    if urgent:
        return URGENT, urgent
    return ROUTINE, []
