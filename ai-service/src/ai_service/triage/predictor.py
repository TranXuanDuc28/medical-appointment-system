"""Lớp suy luận phân loại triệu chứng: luật an toàn chạy trước, mô hình gợi ý chuyên khoa sau."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ai_service.common.registry import load_current
from ai_service.duration.schema import DEPARTMENT_LABEL_VI
from ai_service.triage.rules import EMERGENCY, ROUTINE, URGENT, assess_urgency, normalize_text

DISCLAIMER = "Kết quả chỉ mang tính gợi ý chuyên khoa, không phải chẩn đoán y khoa. Nếu có dấu hiệu nguy hiểm hãy đến cơ sở y tế ngay."
ADVICE = {
    EMERGENCY: "Có dấu hiệu nguy hiểm: hãy gọi cấp cứu 115 hoặc đến cơ sở y tế gần nhất NGAY, không chờ đặt lịch.",
    URGENT: "Nên được khám trong ngày. Hãy ưu tiên khung giờ sớm nhất hoặc đến trực tiếp.",
    ROUTINE: "Bạn có thể đặt lịch khám theo chuyên khoa gợi ý.",
}
MIN_CHARS, MAX_CHARS = 3, 1000


class TriagePredictor:
    def __init__(self, models_dir: Path | None = None):
        self.model, self.meta = load_current("triage", models_dir)
        self.threshold = float(self.meta.get("uncertain_threshold", 0.6))

    @property
    def version(self) -> str:
        return self.meta["version"]

    def predict(self, text: str, top_k: int = 3) -> dict:
        if not isinstance(text, str) or not (MIN_CHARS <= len(text.strip()) <= MAX_CHARS):
            raise ValueError(f"Mô tả triệu chứng phải dài {MIN_CHARS}–{MAX_CHARS} ký tự")
        urgency, reasons = assess_urgency(text)
        proba = self.model.predict_proba([normalize_text(text)])[0]
        order = np.argsort(-proba)[:top_k]
        classes = self.model.classes_
        preds = [{"specialty_key": str(classes[i]), "specialty_vi": DEPARTMENT_LABEL_VI[str(classes[i])], "probability": round(float(proba[i]), 3)} for i in order]
        uncertain = bool(proba[order[0]] < self.threshold)
        recommendation = "CALL_EMERGENCY" if urgency == EMERGENCY else "SAME_DAY" if urgency == URGENT else "BOOK"
        return {
            "urgency": urgency, "urgency_reasons": reasons, "recommendation": recommendation, "advice": ADVICE[urgency],
            "predictions": preds, "uncertain": uncertain, "uncertain_threshold": self.threshold,
            "uncertain_hint": "Chưa đủ thông tin để chắc chắn. Hãy mô tả thêm (vị trí, thời gian, mức độ) hoặc chọn chuyên khoa thủ công." if uncertain else None,
            "model_version": self.version, "disclaimer": DISCLAIMER,
        }
