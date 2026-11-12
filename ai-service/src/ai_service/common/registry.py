"""Kho mô hình có phiên bản: models/<kind>/<version>/{model.joblib, metadata.json} + models/<kind>/current.json."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from ai_service.config import MODELS_DIR


def file_sha256(path: Path, n: int = 12) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def make_version(*parts: str) -> str:
    """Phiên bản dạng `YYYYMMDD-<hash>`; hash tính từ dữ liệu + tham số nên cùng đầu vào => cùng phiên bản."""
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()[:8]
    return f"{datetime.now(timezone.utc):%Y%m%d}-{h}"


def save_model(kind: str, version: str, model: Any, metadata: dict, make_current: bool = True) -> Path:
    d = MODELS_DIR / kind / version
    d.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, d / "model.joblib", compress=3)
    meta = {"kind": kind, "version": version, "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **metadata}
    (d / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if make_current:
        (MODELS_DIR / kind / "current.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    return d


def load_current(kind: str, models_dir: Path | None = None) -> tuple[Any, dict]:
    base = (models_dir or MODELS_DIR) / kind
    cur = base / "current.json"
    if not cur.is_file():
        raise FileNotFoundError(f"Chưa có mô hình '{kind}'. Hãy huấn luyện trước (xem README).")
    version = json.loads(cur.read_text(encoding="utf-8"))["version"]
    d = base / version
    return joblib.load(d / "model.joblib"), json.loads((d / "metadata.json").read_text(encoding="utf-8"))
