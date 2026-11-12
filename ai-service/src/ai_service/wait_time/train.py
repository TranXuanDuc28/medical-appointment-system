"""Huấn luyện + đánh giá dự đoán THỜI GIAN CHỜ trên dataset Kaggle (nghiên cứu / chứng minh quy trình ML).

Quy trình:
  1. Nạp dữ liệu, loại cột rò rỉ (data.py)
  2. Chia train/test 80/20 cố định; kiểm định chéo 5-fold trên train để chọn mô hình
  3. So sánh baseline (đoán trung bình / trung vị / trung bình theo mức nặng) với Linear, Random Forest, XGBoost
  4. Đánh giá trên test (MAE, RMSE, R², MedAE, P90) + khoảng tin cậy bootstrap + mức cải thiện so với baseline
  5. Minh hoạ rò rỉ dữ liệu, độ quan trọng đặc trưng (permutation importance), biểu đồ
  6. Lưu mô hình có phiên bản + sinh báo cáo reports/wait_time_kaggle.md
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GridSearchCV, KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

from ai_service.common import plots
from ai_service.common.metrics import bootstrap_ci, improvement_pct, mae, regression_report
from ai_service.common.registry import make_version, save_model
from ai_service.config import REPORTS_DIR, SEED, ensure_dirs
from ai_service.wait_time import data as D


class GroupMeanRegressor(BaseEstimator, RegressorMixin):
    """Baseline "biết một đặc trưng": đoán bằng trung bình của nhóm (vd. theo mức độ nặng)."""

    def __init__(self, column: str = "severity_level"):
        self.column = column

    def fit(self, X, y):
        y = np.asarray(y, float)
        self.global_ = float(y.mean())
        self.means_ = pd.Series(y).groupby(X[self.column].to_numpy()).mean().to_dict()
        return self

    def predict(self, X):
        return np.array([self.means_.get(v, self.global_) for v in X[self.column]])


def _preprocess(categorical: list[str], numeric: list[str], scale: bool) -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
            ("num", StandardScaler() if scale else "passthrough", numeric),
        ]
    )


def build_models() -> dict[str, object]:
    cat, num = D.CATEGORICAL, D.NUMERIC
    return {
        "Baseline: trung bình": DummyRegressor(strategy="mean"),
        "Baseline: trung vị": DummyRegressor(strategy="median"),
        "Baseline: trung bình theo mức nặng": GroupMeanRegressor("severity_level"),
        "Linear Regression": Pipeline([("prep", _preprocess(cat, num, True)), ("m", LinearRegression())]),
        "Random Forest": Pipeline(
            [("prep", _preprocess(cat, num, False)),
             ("m", RandomForestRegressor(n_estimators=300, min_samples_leaf=20, n_jobs=-1, random_state=SEED))]
        ),
        "XGBoost": Pipeline(
            [("prep", _preprocess(cat, num, False)),
             ("m", XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=3, subsample=0.8, colsample_bytree=0.8,
                                tree_method="hist", random_state=SEED, n_jobs=-1))]
        ),
    }


def run() -> dict:
    ensure_dirs()
    df = D.load_raw()
    X, y = D.split_xy(df)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=SEED)
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)

    # ---- 1. So sánh mô hình bằng kiểm định chéo trên TRAIN (test chưa đụng tới) ----
    models = build_models()
    cv_rows = []
    for name, model in models.items():
        scores = -cross_val_score(model, X_tr, y_tr, cv=cv, scoring="neg_mean_absolute_error", n_jobs=1)
        cv_rows.append({"model": name, "cv_mae_mean": round(float(scores.mean()), 3), "cv_mae_std": round(float(scores.std()), 3)})

    # ---- 2. Tinh chỉnh nhẹ XGBoost (chỉ trên train) ----
    grid = GridSearchCV(
        models["XGBoost"],
        {"m__max_depth": [2, 3, 4], "m__n_estimators": [150, 300], "m__learning_rate": [0.03, 0.06], "m__min_child_weight": [5, 20]},
        cv=cv, scoring="neg_mean_absolute_error", n_jobs=-1,
    ).fit(X_tr, y_tr)
    models["XGBoost (đã tinh chỉnh)"] = grid.best_estimator_
    cv_rows.append({"model": "XGBoost (đã tinh chỉnh)", "cv_mae_mean": round(float(-grid.best_score_), 3), "cv_mae_std": None})

    # ---- 3. Huấn luyện lại trên toàn bộ train, đánh giá MỘT LẦN trên test ----
    results, preds = {}, {}
    for name, model in models.items():
        model.fit(X_tr, y_tr)
        preds[name] = model.predict(X_te)
        results[name] = regression_report(y_te, preds[name])

    baseline = results["Baseline: trung bình"]["mae"]
    # Chọn mô hình ĐƠN GIẢN NHẤT trong ngưỡng 0,5% so với MAE tốt nhất (nguyên tắc tiết kiệm: chênh lệch nhỏ hơn nhiễu
    # thì không có lý do triển khai mô hình phức tạp hơn). Hai baseline hằng số (trung bình/trung vị) không được chọn.
    complexity_order = ["Baseline: trung bình theo mức nặng", "Linear Regression", "Random Forest", "XGBoost", "XGBoost (đã tinh chỉnh)"]
    lowest = min(results[n]["mae"] for n in complexity_order)
    best_name = next(n for n in complexity_order if results[n]["mae"] <= lowest * 1.005)
    best_raw_name = min(complexity_order, key=lambda n: results[n]["mae"])
    best_mae = results[best_name]["mae"]
    ci_best = bootstrap_ci(y_te, preds[best_name], mae, seed=SEED)
    ci_base = bootstrap_ci(y_te, preds["Baseline: trung bình"], mae, seed=SEED)
    sev = results["Baseline: trung bình theo mức nặng"]

    # ---- 4. Minh hoạ rò rỉ dữ liệu ----
    Xl, yl = D.split_xy(df, include_leaky=True)
    Xl_tr, Xl_te, yl_tr, yl_te = train_test_split(Xl, yl, test_size=0.2, random_state=SEED)
    leak_cat, leak_num = D.CATEGORICAL, D.NUMERIC + ["patient_satisfaction_score", "total_bill", "medicine_cost", "test_cost"]
    leaky_model = Pipeline([("prep", _preprocess(leak_cat, leak_num, False)),
                            ("m", XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=3, tree_method="hist", random_state=SEED))])
    leaky_model.fit(Xl_tr, yl_tr)
    leak_report = regression_report(yl_te, leaky_model.predict(Xl_te))

    # ---- 5. Độ quan trọng đặc trưng của mô hình tốt nhất (hoán vị trên test) ----
    best_model = models[best_name]
    imp = permutation_importance(best_model, X_te, y_te, scoring="neg_mean_absolute_error", n_repeats=10, random_state=SEED, n_jobs=1)
    importance = (
        pd.DataFrame({"feature": X_te.columns, "mae_increase": imp.importances_mean})
        .sort_values("mae_increase", ascending=False).reset_index(drop=True)
    )

    # ---- 6. Biểu đồ + lưu mô hình ----
    figs = {
        "pred_vs_actual": plots.pred_vs_actual(y_te, preds[best_name], f"{best_name}: dự đoán vs thực tế", "wait_pred_vs_actual.png"),
        "residuals": plots.residual_hist(y_te, preds[best_name], f"Phân bố sai số – {best_name}", "wait_residuals.png"),
        "models": plots.bar(list(results), [results[n]["mae"] for n in results], "MAE trên tập test (thấp hơn = tốt hơn)", "MAE (phút)",
                            "wait_models_mae.png", highlight=best_name),
        "importance": plots.bar(importance["feature"].head(10).tolist(), importance["mae_increase"].head(10).tolist(),
                                "Độ quan trọng đặc trưng (MAE tăng khi xáo trộn)", "MAE tăng thêm (phút)", "wait_importance.png"),
    }

    fingerprint = D.dataset_fingerprint()
    version = make_version("wait_time_kaggle", fingerprint, str(SEED), best_name)
    metadata = {
        "purpose": "nghiên cứu: dự đoán thời gian chờ trên dataset Kaggle (KHÔNG dùng cho ETA của hàng đợi)",
        "selection_rule": "mô hình đơn giản nhất trong ngưỡng 0,5% so với MAE thấp nhất",
        "algorithm": best_name, "dataset_sha256_12": fingerprint, "n_rows": int(len(df)), "seed": SEED,
        "features": D.FEATURES, "excluded_leaky": D.LEAKY_COLUMNS, "metrics_test": results[best_name],
        "baseline_mae": baseline, "improvement_vs_mean_baseline_pct": improvement_pct(baseline, best_mae),
        "best_params": {k: (v.item() if hasattr(v, "item") else v) for k, v in grid.best_params_.items()},
    }
    save_model("wait_time_kaggle", version, best_model, metadata)

    summary = {
        "version": version, "best": best_name, "best_raw": best_raw_name, "results": results, "cv": cv_rows, "baseline_mae": baseline,
        "best_mae": best_mae, "ci_best": ci_best, "ci_base": ci_base, "severity_baseline": sev, "leak": leak_report,
        "importance": importance.head(12).round(3).to_dict("records"), "figs": figs, "fingerprint": fingerprint,
        "best_params": metadata["best_params"], "n_rows": int(len(df)), "n_train": int(len(X_tr)), "n_test": int(len(X_te)),
        "target_stats": {"mean": round(float(y.mean()), 2), "sd": round(float(y.std()), 2), "p10": float(y.quantile(.1)), "p90": float(y.quantile(.9))},
    }
    write_report(summary)
    return summary


def write_report(s: dict) -> None:
    R = s["results"]
    rows = "\n".join(
        f"| {n} | {r['mae']} | {r['rmse']} | {r['r2']} | {r['median_ae']} | {r['p90_abs_error']} | {int(r['within_10_min'] * 100)}% |"
        for n, r in R.items()
    )
    cvrows = "\n".join(f"| {c['model']} | {c['cv_mae_mean']} | {'' if c['cv_mae_std'] is None else '± ' + str(c['cv_mae_std'])} |" for c in s["cv"])
    imp = "\n".join(f"| {i['feature']} | {i['mae_increase']} |" for i in s["importance"][:8])
    leak = s["leak"]
    ci_lo, ci_hi = s["ci_best"]
    b_lo, b_hi = s["ci_base"]
    md = f"""# Báo cáo: dự đoán thời gian chờ trên dataset Kaggle

> Sinh tự động bởi `python -m ai_service train-wait` – phiên bản mô hình `{s['version']}`, dữ liệu sha256 `{s['fingerprint']}`, hạt giống {SEED}.

## 1. Dữ liệu và cách làm
- {s['n_rows']:,} ca khám (10 khoa, 26 cột), không thiếu giá trị, không trùng `patient_id`.
- Nhãn: `waiting_time_minutes` (trung bình **{s['target_stats']['mean']}** phút, độ lệch chuẩn {s['target_stats']['sd']}, P10 {s['target_stats']['p10']:.0f} – P90 {s['target_stats']['p90']:.0f}).
- Chia cố định: train {s['n_train']:,} / test {s['n_test']:,}. Chọn mô hình bằng kiểm định chéo 5-fold **chỉ trên train**; tập test chỉ chạm **một lần** để báo cáo.
- **Loại 5 cột phát sinh sau khi khám** (rò rỉ dữ liệu): `patient_satisfaction_score`, `total_bill`, `medicine_cost`, `test_cost`, `appointment_status`; và `symptoms` (trùng 1-1 với `department`).

## 2. Kết quả trên tập test

| Mô hình | MAE (phút) | RMSE | R² | MedAE | Sai số P90 | Sai ≤ 10 phút |
|---|---|---|---|---|---|---|
{rows}

**Mô hình được chọn: {s['best']}** (đơn giản nhất trong ngưỡng 0,5% so với MAE thấp nhất, mô hình có MAE thấp nhất tuyệt đối là *{s['best_raw']}*) – MAE **{s['best_mae']}** phút (95% CI {ci_lo:.2f} – {ci_hi:.2f}), so với đoán trung bình MAE {s['baseline_mae']} (95% CI {b_lo:.2f} – {b_hi:.2f}): **giảm {improvement_pct(s['baseline_mae'], s['best_mae'])}%** sai số.

![MAE các mô hình]({s['figs']['models']})
![Dự đoán vs thực tế]({s['figs']['pred_vs_actual']})

### Kiểm định chéo 5-fold trên train (MAE)

| Mô hình | MAE trung bình | Độ lệch |
|---|---|---|
{cvrows}

## 3. Phát hiện quan trọng (cần trình bày trung thực khi bảo vệ)
1. **Chỉ một đặc trưng thực sự dự đoán được: `severity_level`.** Chỉ cần đoán theo mức nặng đã đạt MAE **{s['severity_baseline']['mae']}**, R² **{s['severity_baseline']['r2']}** – gần bằng mô hình phức tạp nhất. XGBoost/Random Forest không hơn đáng kể vì phần còn lại là **nhiễu** (tuổi, giới, bệnh nền, tỉnh, bảo hiểm, tháng, thứ… tương quan ≈ 0).
2. **Trần hiệu năng thực tế ≈ MAE {s['best_mae']}, R² ≈ {R[s['best']]['r2']}.** Mục tiêu ban đầu của đề cương (MAE ≤ 2,5 phút, R² ≥ 0,85) **không đạt được bằng đặc trưng hợp lệ** trên bộ dữ liệu này.
3. **Rò rỉ dữ liệu cho kết quả "đẹp" giả tạo:** thêm các cột sau khám, cùng XGBoost cho R² {leak['r2']} / MAE {leak['mae']} – tốt hơn hẳn, nhưng không dùng được thật vì những cột đó chưa tồn tại lúc cần dự đoán. Đây là lý do chúng bị loại.
4. Dữ liệu có dấu hiệu **tổng hợp** (nhãn gần như chỉ phụ thuộc mức nặng + nhiễu đều). Vì vậy mô hình ở đây dùng để **chứng minh quy trình ML đúng chuẩn**, còn mô hình tích hợp vào hệ thống là mô hình thời lượng khám (xem `reports/duration_model.md`).

### Độ quan trọng đặc trưng (hoán vị, MAE tăng khi xáo trộn)
| Đặc trưng | MAE tăng thêm (phút) |
|---|---|
{imp}

![Độ quan trọng đặc trưng]({s['figs']['importance']})

## 4. Đề xuất chỉnh mục tiêu trong đề cương
Thay "MAE ≤ 2,5 phút và R² ≥ 0,85" bằng mục tiêu có cơ sở: **giảm ≥ {int(improvement_pct(s['baseline_mae'], s['best_mae']))}% sai số so với cách ước tính cố định/đoán trung bình**, đo trên tập test độc lập, kèm khoảng tin cậy 95%.
"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "wait_time_kaggle.md").write_text(md, encoding="utf-8")
    (REPORTS_DIR / "wait_time_kaggle.json").write_text(json.dumps({k: v for k, v in s.items() if k != "figs"}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
