"""Định nghĩa mô hình thời lượng khám: baseline, pipeline ứng viên và lớp bọc có khoảng dự đoán."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

from ai_service.config import SEED
from ai_service.duration import schema as S


# ------------------------------------------------ Baseline ------------------------------------------------
class ConstantMinutes(BaseEstimator, RegressorMixin):
    """Cách ước tính cố định của hàng đợi hiện tại (mặc định 15 phút/ca)."""

    def __init__(self, minutes: float = 15.0):
        self.minutes = minutes

    def fit(self, X, y=None):
        return self

    def predict(self, X):
        return np.full(len(X), float(self.minutes))


class GroupMean(BaseEstimator, RegressorMixin):
    """Trung bình theo nhóm (vd. theo khoa)."""

    def __init__(self, column: str = "department"):
        self.column = column

    def fit(self, X, y):
        y = np.asarray(y, float)
        self.global_ = float(y.mean())
        self.means_ = pd.Series(y).groupby(X[self.column].to_numpy()).mean().to_dict()
        return self

    def predict(self, X):
        return np.array([self.means_.get(v, self.global_) for v in X[self.column]])


class DoctorHistoryBaseline(BaseEstimator, RegressorMixin):
    """Đoán bằng thời lượng khám trung bình lịch sử của chính bác sĩ (nếu có), không thì trung bình khoa.
    Đây là cách ETA hiện tại của hàng đợi (`historyAvgMinutes`) đang làm."""

    def fit(self, X, y):
        self.dept_ = GroupMean("department").fit(X, y)
        return self

    def predict(self, X):
        fallback = self.dept_.predict(X)
        hist = X["doctor_hist_avg_min"].to_numpy(float)
        return np.where(np.isfinite(hist), hist, fallback)


# ------------------------------------------------ Pipeline ứng viên ------------------------------------------------
def _prep(scale: bool, impute: bool) -> ColumnTransformer:
    num_steps = []
    if impute:  # Linear/RF không chịu được NaN; XGBoost xử lý NaN tự nhiên nên bỏ qua
        num_steps.append(("impute", SimpleImputer(strategy="median", add_indicator=True)))
    if scale:
        num_steps.append(("scale", StandardScaler()))
    numeric = Pipeline(num_steps) if num_steps else "passthrough"
    return ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), S.CATEGORICAL), ("num", numeric, S.NUMERIC)]
    )


def _log_target(regressor) -> TransformedTargetRegressor:
    """Thời lượng lệch phải và nhiễu nhân tính => huấn luyện trên log(thời lượng) rồi đổi ngược về phút."""
    return TransformedTargetRegressor(regressor=regressor, func=np.log, inverse_func=np.exp)


def xgb(**params) -> XGBRegressor:
    base = dict(n_estimators=400, learning_rate=0.05, max_depth=4, subsample=0.8, colsample_bytree=0.8,
                min_child_weight=5, tree_method="hist", random_state=SEED, n_jobs=-1)
    base.update(params)
    return XGBRegressor(**base)


def build_candidates() -> dict[str, object]:
    return {
        "Baseline: cố định 15 phút (hàng đợi hiện tại)": ConstantMinutes(15.0),
        "Baseline: trung bình theo khoa": GroupMean("department"),
        "Baseline: trung bình lịch sử của bác sĩ": DoctorHistoryBaseline(),
        "Ridge (log)": _log_target(Pipeline([("prep", _prep(True, True)), ("m", Ridge(alpha=1.0))])),
        "Random Forest (log)": _log_target(Pipeline([("prep", _prep(False, True)),
                                                     ("m", RandomForestRegressor(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=SEED))])),
        "XGBoost (log)": _log_target(Pipeline([("prep", _prep(False, False)), ("m", xgb())])),
    }


# Thứ tự độ phức tạp tăng dần – dùng cho quy tắc "chọn mô hình đơn giản nhất trong ngưỡng sai số"
COMPLEXITY_ORDER = ["Ridge (log)", "Random Forest (log)", "XGBoost (log)"]


# ------------------------------------------------ Mô hình triển khai ------------------------------------------------
class DurationModel:
    """Mô hình dự đoán thời lượng kèm khoảng dự đoán p10–p90.

    Khoảng được hiệu chuẩn từ phần dư (log) trên tập hiệu chuẩn tách riêng nên `p10`/`p90` có ý nghĩa thống kê:
    khoảng 80% ca thực tế nằm trong [p10, p90] (độ phủ được kiểm tra trên tập test).
    """

    def __init__(self, estimator, q_lo: float, q_hi: float):
        self.estimator = estimator
        self.q_lo = float(q_lo)
        self.q_hi = float(q_hi)

    def predict_df(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[S.FEATURES]
        mean = np.clip(self.estimator.predict(X), S.MIN_DURATION, S.MAX_DURATION)
        return pd.DataFrame({
            "duration_min": mean,
            "p10_min": np.clip(mean * np.exp(self.q_lo), S.MIN_DURATION, S.MAX_DURATION),
            "p90_min": np.clip(mean * np.exp(self.q_hi), S.MIN_DURATION, S.MAX_DURATION),
        })
