"""AI Service – API HTTP (FastAPI) cho backend Node gọi nội bộ.

  GET  /health             tình trạng + phiên bản mô hình (không cần token)
  GET  /model-info         siêu dữ liệu mô hình (chỉ số, đặc trưng, cảnh báo)
  POST /predict-duration   {"items":[{department, severity?, visit_type?, source?, age?, ...}]} -> thời lượng + khoảng p10–p90
  POST /triage             {"text": "..."} -> gợi ý chuyên khoa + mức khẩn

Nếu đặt AI_SERVICE_TOKEN thì mọi endpoint (trừ /health) bắt buộc header `X-AI-Token`.
Lỗi mô hình/đầu vào không bao giờ làm sập backend: backend nên có phương án dự phòng (trung bình lịch sử) khi gọi lỗi.
"""
from __future__ import annotations

import hmac
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from ai_service import __version__
from ai_service.duration.predictor import DurationPredictor
from ai_service.triage.predictor import TriagePredictor

MAX_ITEMS = 200


class DurationRequest(BaseModel):
    items: list[dict] = Field(..., min_length=1, max_length=MAX_ITEMS, description="Danh sách ca cần dự đoán thời lượng")


class TriageRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=1000, description="Mô tả triệu chứng của bệnh nhân")


def create_app(models_dir: Path | None = None) -> FastAPI:
    state: dict = {"duration": None, "triage": None, "errors": {}}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        for name, cls in (("duration", DurationPredictor), ("triage", TriagePredictor)):
            try:
                state[name] = cls(models_dir)
            except Exception as e:  # thiếu mô hình: dịch vụ vẫn chạy, endpoint tương ứng trả 503
                state["errors"][name] = str(e)
        yield

    app = FastAPI(title="AI Service – Hệ thống khám bệnh", version=__version__, lifespan=lifespan)

    def require_token(x_ai_token: str | None = Header(default=None)) -> None:
        expected = os.getenv("AI_SERVICE_TOKEN", "")
        if expected and not (x_ai_token and hmac.compare_digest(x_ai_token, expected)):
            raise HTTPException(status_code=401, detail="Thiếu hoặc sai X-AI-Token")

    def need(name: str):
        if state[name] is None:
            raise HTTPException(status_code=503, detail=f"Mô hình '{name}' chưa sẵn sàng: {state['errors'].get(name, 'chưa huấn luyện')}")
        return state[name]

    @app.get("/health")
    def health():
        return {
            "status": "ok" if all(state[k] for k in ("duration", "triage")) else "degraded", "service_version": __version__,
            "models": {k: (state[k].version if state[k] else None) for k in ("duration", "triage")}, "errors": state["errors"],
        }

    @app.get("/model-info", dependencies=[Depends(require_token)])
    def model_info():
        return {k: (state[k].meta if state[k] else None) for k in ("duration", "triage")}

    @app.post("/predict-duration", dependencies=[Depends(require_token)])
    def predict_duration(req: DurationRequest):
        predictor = need("duration")
        try:
            preds = predictor.predict(req.items)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        return {"model_version": predictor.version, "predictions": preds}

    @app.post("/triage", dependencies=[Depends(require_token)])
    def triage(req: TriageRequest):
        predictor = need("triage")
        try:
            return predictor.predict(req.text)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    return app


app = create_app()
