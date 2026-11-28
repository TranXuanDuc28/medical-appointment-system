"""Huấn luyện + đánh giá mô hình THỜI LƯỢNG KHÁM (mô hình tích hợp vào hàng đợi).

Quy trình (khớp quy trình chuẩn, không rò rỉ):
  1. Nạp dữ liệu (mô phỏng hoặc log thật từ hàng đợi) và kiểm tra đúng hợp đồng đặc trưng (schema.py)
  2. Chia train/test THEO BUỔI KHÁM (cả buổi vào cùng một phía) để không rò rỉ giữa các ca cùng buổi
  3. Kiểm định chéo GroupKFold trên train để chọn mô hình; chọn mô hình ĐƠN GIẢN NHẤT trong ngưỡng 1% MAE
  4. Hiệu chuẩn khoảng dự đoán p10–p90 trên tập hiệu chuẩn tách riêng, kiểm tra độ phủ trên test
  5. Đánh giá ở mức hệ thống: sai số ETA so với cách cố định 15 phút (eta_simulation.py)
  6. Lưu mô hình có phiên bản + báo cáo reports/duration_model.md
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.inspection import permutation_importance
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, cross_val_score

from ai_service.common import plots
from ai_service.common.metrics import bootstrap_ci, improvement_pct, mae, regression_report
from ai_service.common.registry import make_version, save_model
from ai_service.config import DATA_DIR, REPORTS_DIR, SEED, ensure_dirs
from ai_service.duration import eta_simulation, schema as S, simulate
from ai_service.duration.model import COMPLEXITY_ORDER, DurationModel, build_candidates

REAL_PATH = DATA_DIR / "real" / "duration_from_queue.csv"
TUNED = "XGBoost (log, tinh chỉnh)"
REF = "Baseline: cố định 15 phút (hàng đợi hiện tại)"


def load_data(source: str, regenerate: bool, n_sessions: int) -> tuple[pd.DataFrame, str]:
    if source == "real":
        if not REAL_PATH.is_file():
            raise FileNotFoundError(f"Chưa có dữ liệu thật: chạy `python -m ai_service export-real` trước ({REAL_PATH})")
        df = pd.read_csv(REAL_PATH)
        if len(df) < 200:
            raise ValueError(f"Dữ liệu thật mới có {len(df)} ca, cần tối thiểu 200 để huấn luyện có ý nghĩa")
        label = "real"
    else:
        df = simulate.load_or_generate(force=regenerate, n_sessions=n_sessions)
        label = "synthetic"
    missing = [c for c in S.FEATURES + [S.TARGET, "session_id", "position"] if c not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột: {missing}")
    return df, label


def _group_cv(groups) -> GroupKFold:
    return GroupKFold(n_splits=5)


def run(source: str = "synthetic", regenerate: bool = False, n_sessions: int = 3000) -> dict:
    ensure_dirs()
    df, label = load_data(source, regenerate, n_sessions)
    X, y, g = df[S.FEATURES], df[S.TARGET].astype(float), df["session_id"]

    tr_idx, te_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED).split(X, y, g))
    X_tr, X_te, y_tr, y_te, g_tr = X.iloc[tr_idx], X.iloc[te_idx], y.iloc[tr_idx], y.iloc[te_idx], g.iloc[tr_idx]
    test_df = df.iloc[te_idx]

    # ---- Chọn mô hình bằng CV theo nhóm (chỉ trên train) ----
    models = build_candidates()
    cv = GroupKFold(n_splits=5)
    cv_mae = {}
    for name, m in models.items():
        s = -cross_val_score(m, X_tr, y_tr, cv=cv, groups=g_tr, scoring="neg_mean_absolute_error")
        cv_mae[name] = (float(s.mean()), float(s.std()))
    grid = GridSearchCV(
        clone(models["XGBoost (log)"]),
        {"regressor__m__max_depth": [3, 4, 6], "regressor__m__n_estimators": [200, 400], "regressor__m__learning_rate": [0.03, 0.06]},
        cv=cv, scoring="neg_mean_absolute_error", n_jobs=1,
    ).fit(X_tr, y_tr, groups=g_tr)
    models[TUNED] = grid.best_estimator_
    cv_mae[TUNED] = (float(-grid.best_score_), None)

    order = COMPLEXITY_ORDER + [TUNED]
    lowest = min(cv_mae[n][0] for n in order)
    chosen_name = next(n for n in order if cv_mae[n][0] <= lowest * 1.01)

    # ---- Đánh giá trên test (chạm một lần) ----
    preds, results = {}, {}
    for name, m in models.items():
        m.fit(X_tr, y_tr)
        preds[name] = np.clip(m.predict(X_te), S.MIN_DURATION, S.MAX_DURATION)
        results[name] = regression_report(y_te, preds[name])
    chosen = models[chosen_name]
    p = preds[chosen_name]
    mae_ci = bootstrap_ci(y_te, p, mae, seed=SEED)

    # ---- Hiệu chuẩn khoảng dự đoán p10–p90 (log-residual) trên tập hiệu chuẩn riêng ----
    fit_i, cal_i = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED + 1).split(X_tr, y_tr, g_tr))
    est_cal = clone(chosen).fit(X_tr.iloc[fit_i], y_tr.iloc[fit_i])
    resid = np.log(y_tr.iloc[cal_i].to_numpy()) - np.log(np.clip(est_cal.predict(X_tr.iloc[cal_i]), S.MIN_DURATION, S.MAX_DURATION))
    q_lo, q_hi = float(np.quantile(resid, 0.10)), float(np.quantile(resid, 0.90))
    final = DurationModel(chosen, q_lo, q_hi)  # `chosen` đã fit trên toàn bộ train ở trên
    band = final.predict_df(test_df)
    coverage = float(((y_te.to_numpy() >= band["p10_min"].to_numpy()) & (y_te.to_numpy() <= band["p90_min"].to_numpy())).mean())

    # ---- Mức hệ thống: sai số ETA ----
    strategies = {
        REF: preds[REF], "Trung bình theo khoa": preds["Baseline: trung bình theo khoa"],
        "Trung bình lịch sử của bác sĩ": preds["Baseline: trung bình lịch sử của bác sĩ"], f"ML: {chosen_name}": p,
    }
    eta = eta_simulation.compare(test_df, strategies, reference=REF)

    # ---- Phân tích thêm ----
    imp = permutation_importance(chosen, X_te, y_te, scoring="neg_mean_absolute_error", n_repeats=5, random_state=SEED, n_jobs=1)
    importance = pd.DataFrame({"feature": X_te.columns, "mae_increase": imp.importances_mean}).sort_values("mae_increase", ascending=False)
    by_sev = {k: round(float(mae(y_te[test_df["severity"] == k], p[(test_df["severity"] == k).to_numpy()])), 2) for k in S.SEVERITIES}
    by_dep = {k: round(float(mae(y_te[test_df["department"] == k], p[(test_df["department"] == k).to_numpy()])), 2) for k in S.DEPARTMENTS}

    figs = {
        "models": plots.bar(list(results), [results[n]["mae"] for n in results], "MAE thời lượng từng ca (test)", "MAE (phút)", "dur_models_mae.png", highlight=chosen_name),
        "pred": plots.pred_vs_actual(y_te, p, f"{chosen_name}: dự đoán vs thực tế", "dur_pred_vs_actual.png"),
        "importance": plots.bar(importance["feature"].tolist(), importance["mae_increase"].tolist(), "Độ quan trọng đặc trưng", "MAE tăng thêm (phút)", "dur_importance.png"),
        "eta": plots.bar(list(eta), [eta[k]["mae_overall"] for k in eta], "Sai số ETA bệnh nhân (MAE, phút) – thấp hơn = tốt hơn", "MAE ETA (phút)", "dur_eta_mae.png", highlight=f"ML: {chosen_name}"),
    }

    fingerprint = make_version(label, str(len(df)), str(SEED), chosen_name)
    version = fingerprint
    metadata = {
        "purpose": "dự đoán thời lượng một ca khám (phút) cho ETA hàng đợi", "data_source": label, "n_rows": int(len(df)),
        "n_sessions": int(g.nunique()), "seed": SEED, "algorithm": chosen_name, "features": S.FEATURES, "defaults": {k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in S.DEFAULTS.items()},
        "interval": {"q_lo": q_lo, "q_hi": q_hi, "nominal": 0.8, "coverage_test": round(coverage, 3)},
        "metrics_test": results[chosen_name], "mae_ci95": [round(mae_ci[0], 3), round(mae_ci[1], 3)],
        "baseline_const15_mae": results[REF]["mae"], "improvement_vs_const15_pct": improvement_pct(results[REF]["mae"], results[chosen_name]["mae"]),
        "eta_mae_const15": eta[REF]["mae_overall"], "eta_mae_model": eta[f"ML: {chosen_name}"]["mae_overall"],
        "eta_improvement_pct": eta[f"ML: {chosen_name}"]["improvement_vs_reference_pct"],
        "warning": "Dữ liệu mô phỏng: cần tái huấn luyện từ log thật (queue_events) trước khi dùng cho vận hành thật" if label == "synthetic" else None,
    }
    save_model("duration", version, final, metadata)

    summary = dict(version=version, label=label, chosen=chosen_name, results=results, cv_mae=cv_mae, mae_ci=mae_ci, coverage=coverage,
                   q=(q_lo, q_hi), eta=eta, importance=importance.head(10).round(3).to_dict("records"), by_sev=by_sev, by_dep=by_dep,
                   figs=figs, n_rows=int(len(df)), n_sessions=int(g.nunique()), n_train=int(len(X_tr)), n_test=int(len(X_te)),
                   best_params={k: (v.item() if hasattr(v, "item") else v) for k, v in grid.best_params_.items()})
    write_report(summary)
    return summary


def write_report(s: dict) -> None:
    R, E = s["results"], s["eta"]
    chosen_key = f"ML: {s['chosen']}"
    rows = "\n".join(f"| {n} | {r['mae']} | {r['rmse']} | {r['r2']} | {r['median_ae']} | {r['p90_abs_error']} |" for n, r in R.items())
    cv = "\n".join(f"| {n} | {m:.3f} | {'' if sd is None else '± ' + format(sd, '.3f')} |" for n, (m, sd) in s["cv_mae"].items())
    eta_rows = "\n".join(
        f"| {n} | {e['mae_overall']} | {e['p90']} | {int(e['within_10'] * 100)}% | {e['by_position'].get('vị trí 2–4', '')} | {e['by_position'].get('vị trí 5–8', '')} | {e['by_position'].get('vị trí ≥9', '')} | {e['improvement_vs_reference_pct']}% |"
        for n, e in E.items()
    )
    imp = "\n".join(f"| {i['feature']} | {i['mae_increase']} |" for i in s["importance"])
    sev = ", ".join(f"{k}: {v}" for k, v in s["by_sev"].items())
    dep = ", ".join(f"{S.DEPARTMENT_LABEL_VI[k]}: {v}" for k, v in s["by_dep"].items())
    warn = ""
    if s["label"] == "synthetic":
        warn = f"""> ⚠️ **Dữ liệu MÔ PHỎNG.** Các con số dưới đây phản ánh khả năng mô hình học lại các giả định của bộ mô phỏng (có nhiễu và đặc trưng nhiễu),
> **không phải** kết quả trên bệnh viện thật. Mục đích: chứng minh quy trình, và cho thấy ETA cải thiện thế nào *nếu* thời lượng phụ thuộc các yếu tố này.
> Khi hệ thống chạy thật, tái huấn luyện bằng `python -m ai_service export-real` rồi `train-duration --source real`.

### Giả định của bộ mô phỏng
{simulate.assumptions_markdown()}
"""
    md = f"""# Báo cáo: mô hình thời lượng khám (tích hợp vào hàng đợi)

> Sinh tự động bởi `python -m ai_service train-duration` – phiên bản `{s['version']}`, nguồn dữ liệu **{s['label']}**, hạt giống {SEED}.

{warn}
## 1. Cách làm
- {s['n_rows']:,} ca khám trong {s['n_sessions']:,} buổi khám; chia **theo buổi khám** (train {s['n_train']:,} ca / test {s['n_test']:,} ca) để không rò rỉ.
- Đặc trưng (đều biết lúc check-in): {', '.join(S.FEATURES)}.
- Huấn luyện trên log(thời lượng) vì thời lượng lệch phải và nhiễu nhân tính; đổi ngược về phút khi dự đoán.
- Chọn mô hình bằng kiểm định chéo 5-fold theo nhóm; chọn **mô hình đơn giản nhất trong ngưỡng 1% MAE**. Kết quả: **{s['chosen']}**.

## 2. Kết quả từng ca (tập test)

| Mô hình | MAE (phút) | RMSE | R² | MedAE | Sai số P90 |
|---|---|---|---|---|---|
{rows}

MAE của mô hình được chọn: **{R[s['chosen']]['mae']} phút** (95% CI {s['mae_ci'][0]:.2f} – {s['mae_ci'][1]:.2f}), R² **{R[s['chosen']]['r2']}**. MAE theo mức nặng — {sev}. Theo khoa — {dep}.

![MAE các mô hình]({s['figs']['models']})
![Dự đoán vs thực tế]({s['figs']['pred']})

**Khoảng dự đoán p10–p90:** độ phủ thực tế trên test **{s['coverage'] * 100:.1f}%** (danh định 80%).

### Kiểm định chéo 5-fold theo nhóm (MAE trên train)

| Mô hình | MAE | Độ lệch |
|---|---|---|
{cv}

## 3. Giá trị ở mức hệ thống: sai số ETA của bệnh nhân
Chờ(Pₙ) = Σ thời lượng những người đứng trước. So sánh cách ước tính thời lượng từng ca (mô phỏng trên các buổi khám của tập test):

| Cách ước tính | MAE ETA (phút) | P90 | Sai ≤ 10 phút | vị trí 2–4 | vị trí 5–8 | vị trí ≥9 | So với cố định 15' |
|---|---|---|---|---|---|---|---|
{eta_rows}

**Kết luận:** dùng mô hình thay cho "cố định 15 phút" giảm sai số ETA **{E[chosen_key]['improvement_vs_reference_pct']}%** (MAE {E[REF]['mae_overall']} → {E[chosen_key]['mae_overall']} phút). Sai số tích luỹ càng lớn khi bệnh nhân đứng càng sau, nên lợi ích càng rõ ở cuối hàng.

![Sai số ETA]({s['figs']['eta']})

### Độ quan trọng đặc trưng (hoán vị)
| Đặc trưng | MAE tăng thêm (phút) |
|---|---|
{imp}

![Độ quan trọng đặc trưng]({s['figs']['importance']})
"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "duration_model.md").write_text(md, encoding="utf-8")
    (REPORTS_DIR / "duration_model.json").write_text(
        json.dumps({k: v for k, v in s.items() if k not in ("figs",)}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
