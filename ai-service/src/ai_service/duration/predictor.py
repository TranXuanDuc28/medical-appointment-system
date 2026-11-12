"""Lớp suy luận thời lượng khám: kiểm tra đầu vào, điền mặc định, trả về dự đoán + khoảng + phiên bản mô hình."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_service.common.registry import load_current
from ai_service.duration import schema as S


class DurationPredictor:
    def __init__(self, models_dir: Path | None = None):
        self.model, self.meta = load_current("duration", models_dir)

    @property
    def version(self) -> str:
        return self.meta["version"]

    def predict(self, requests: list[dict]) -> list[dict]:
        """Mỗi phần tử: {department, severity?, visit_type?, source?, age?, ...} -> {duration_min, p10_min, p90_min, used_defaults, ...}.

        Ném ValueError (thông điệp tiếng Việt, có chỉ số phần tử) nếu một yêu cầu sai.
        """
        rows, used = [], []
        for i, raw in enumerate(requests):
            try:
                row, u = S.normalize_row(raw)
            except ValueError as e:
                raise ValueError(f"Phần tử #{i}: {e}") from None
            rows.append(row)
            used.append(u)
        out = self.model.predict_df(pd.DataFrame(rows))
        return [
            {
                "duration_min": round(float(r.duration_min), 1),
                "p10_min": round(float(r.p10_min), 1),
                "p90_min": round(float(r.p90_min), 1),
                "used_defaults": u,
                # Ít thông tin thật => độ tin cậy thấp hơn: backend có thể hiển thị khác đi
                "confidence": "high" if len([k for k in u if k in ("severity", "visit_type")]) == 0 else "medium" if len(u) <= 5 else "low",
                "model_version": self.version,
            }
            for r, u in zip(out.itertuples(), used)
        ]
