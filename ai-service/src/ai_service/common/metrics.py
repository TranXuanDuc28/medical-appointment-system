"""Chỉ số đánh giá hồi quy + khoảng tin cậy bootstrap (chỉ dùng numpy)."""
from __future__ import annotations

from typing import Callable

import numpy as np


def mae(y, p) -> float:
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.mean(np.abs(y - p)))


def rmse(y, p) -> float:
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.sqrt(np.mean((y - p) ** 2)))


def r2(y, p) -> float:
    y, p = np.asarray(y, float), np.asarray(p, float)
    ss_res = float(np.sum((y - p) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


def regression_report(y, p) -> dict:
    """Bộ chỉ số chuẩn dùng cho báo cáo: MAE, RMSE, R², MedAE, sai số P90, tỉ lệ sai ≤ 5/10 phút."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    err = np.abs(y - p)
    return {
        "mae": round(mae(y, p), 3),
        "rmse": round(rmse(y, p), 3),
        "r2": round(r2(y, p), 4),
        "median_ae": round(float(np.median(err)), 3),
        "p90_abs_error": round(float(np.percentile(err, 90)), 3),
        "within_5_min": round(float(np.mean(err <= 5)), 4),
        "within_10_min": round(float(np.mean(err <= 10)), 4),
        "n": int(len(y)),
    }


def bootstrap_ci(y, p, metric: Callable = mae, n_boot: int = 1000, alpha: float = 0.05, seed: int = 42) -> tuple[float, float]:
    """Khoảng tin cậy (1-alpha) của một chỉ số bằng bootstrap trên cặp (y, p)."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(y), size=(n_boot, len(y)))
    vals = np.array([metric(y[i], p[i]) for i in idx])
    return float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def improvement_pct(baseline: float, model: float) -> float:
    """Mô hình giảm sai số bao nhiêu % so với baseline."""
    return round(100.0 * (baseline - model) / baseline, 1) if baseline else 0.0
