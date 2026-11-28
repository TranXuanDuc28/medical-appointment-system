"""Kiểm chứng GIÁ TRỊ CỦA ĐỀ TÀI ở mức hệ thống: ETA (thời gian chờ) của bệnh nhân thứ n sai bao nhiêu phút nếu ước
tính thời lượng từng ca bằng (a) cố định 15 phút như bốc số truyền thống, (b) trung bình khoa, (c) lịch sử bác sĩ, (d) mô hình ML.

Với mỗi buổi khám trong tập test:  Chờ(Pₙ) = Σ thời lượng của các bệnh nhân đứng trước.
  - thực tế = tổng thời lượng THẬT của họ
  - dự đoán = tổng thời lượng DỰ ĐOÁN của họ (đặc trưng chỉ gồm thông tin biết lúc check-in)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ai_service.common.metrics import improvement_pct


def wait_errors(test: pd.DataFrame, per_visit_pred: np.ndarray) -> pd.DataFrame:
    """Sai số ETA từng bệnh nhân (từ bệnh nhân thứ 2 trở đi, vì người đầu tiên chờ 0 phút)."""
    df = test.reset_index(drop=True).copy()
    df["pred"] = per_visit_pred
    out = []
    for _, g in df.sort_values(["session_id", "position"]).groupby("session_id"):
        actual_cum = g["duration_min"].cumsum().shift(fill_value=0.0)
        pred_cum = g["pred"].cumsum().shift(fill_value=0.0)
        out.append(pd.DataFrame({"position": g["position"].to_numpy(), "actual_wait": actual_cum.to_numpy(),
                                 "pred_wait": pred_cum.to_numpy()}))
    res = pd.concat(out, ignore_index=True)
    res = res[res["position"] >= 1].copy()
    res["abs_err"] = (res["actual_wait"] - res["pred_wait"]).abs()
    return res


def compare(test: pd.DataFrame, strategies: dict[str, np.ndarray], reference: str) -> dict:
    """MAE ETA theo từng chiến lược, theo nhóm vị trí hàng đợi, và % cải thiện so với `reference`."""
    table = {}
    for name, pred in strategies.items():
        e = wait_errors(test, pred)
        bucket = pd.cut(e["position"], [0, 3, 7, 100], labels=["vị trí 2–4", "vị trí 5–8", "vị trí ≥9"])
        table[name] = {
            "mae_overall": round(float(e["abs_err"].mean()), 2),
            "p90": round(float(np.percentile(e["abs_err"], 90)), 2),
            "within_10": round(float((e["abs_err"] <= 10).mean()), 3),
            "by_position": {str(k): round(float(v), 2) for k, v in e.groupby(bucket, observed=True)["abs_err"].mean().items()},
            "n": int(len(e)),
        }
    ref = table[reference]["mae_overall"]
    for name in table:
        table[name]["improvement_vs_reference_pct"] = improvement_pct(ref, table[name]["mae_overall"])
    return table
