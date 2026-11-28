"""Huấn luyện + đánh giá phân loại triệu chứng -> chuyên khoa (TF-IDF ký tự + từ, Logistic Regression).

Đánh giá trung thực ở hai tầng:
  1. Tập test CHIA THEO NHÓM triệu chứng gốc (mô hình chưa thấy cụm triệu chứng đó, chỉ thấy các cụm khác)
  2. Tập NGOÀI (viết tay, câu nói tự nhiên, không sinh từ khuôn mẫu) – ước lượng khả năng khái quát thật sự

Lưu ý: dữ liệu do nhóm tự xây từ kiến thức phổ thông, CHƯA được bác sĩ kiểm định; kết quả chỉ chứng minh quy trình và giá trị gợi ý.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit
from sklearn.pipeline import FeatureUnion, Pipeline

from ai_service.common.registry import make_version, save_model
from ai_service.config import REPORTS_DIR, SEED, ensure_dirs
from ai_service.duration.schema import DEPARTMENT_LABEL_VI
from ai_service.triage import build_dataset, lexicon as L
from ai_service.triage.rules import normalize_text


def build_pipeline(C: float = 10.0) -> Pipeline:
    feats = FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)),
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
    ])
    return Pipeline([("tfidf", feats), ("clf", LogisticRegression(C=C, max_iter=3000, class_weight="balanced"))])


def topk_accuracy(proba: np.ndarray, classes: np.ndarray, y_true, k: int) -> float:
    top = np.argsort(-proba, axis=1)[:, :k]
    return float(np.mean([y in classes[t] for y, t in zip(y_true, top)]))


def threshold_table(proba, classes, y_true, thresholds=(0.0, 0.2, 0.3, 0.4, 0.5, 0.6)) -> list[dict]:
    """Đánh đổi giữa "dám trả lời" và độ chính xác: bỏ qua (uncertain) các ca có xác suất cao nhất < ngưỡng."""
    p1 = proba.max(axis=1)
    pred = classes[proba.argmax(axis=1)]
    rows = []
    for t in thresholds:
        keep = p1 >= t
        rows.append({"threshold": t, "coverage": round(float(keep.mean()), 3),
                     "top1_acc_on_answered": round(float((pred[keep] == np.asarray(y_true)[keep]).mean()), 3) if keep.any() else None})
    return rows


def run() -> dict:
    ensure_dirs()
    df = build_dataset.write()
    ext = pd.DataFrame(L.EXTERNAL_TEST, columns=["text", "label"])
    X, y, g = df["text"].map(normalize_text), df["label"], df["group"]

    tr_i, te_i = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED).split(X, y, g))
    X_tr, X_te, y_tr, y_te, g_tr = X.iloc[tr_i], X.iloc[te_i], y.iloc[tr_i], y.iloc[te_i], g.iloc[tr_i]

    grid = GridSearchCV(build_pipeline(), {"clf__C": [1, 3, 10, 30]}, cv=GroupKFold(n_splits=5), scoring="f1_macro", n_jobs=1)
    grid.fit(X_tr, y_tr, groups=g_tr)
    model = grid.best_estimator_
    classes = model.classes_

    # ---- Tầng 1: tập test theo nhóm ----
    p_te = model.predict_proba(X_te)
    pred_te = classes[p_te.argmax(axis=1)]
    holdout = {"top1": round(float((pred_te == y_te).mean()), 4), "top3": round(topk_accuracy(p_te, classes, y_te, 3), 4),
               "macro_f1": round(float(f1_score(y_te, pred_te, average="macro")), 4), "n": int(len(y_te))}

    # ---- Chọn ngưỡng "không chắc chắn" trên tập test theo nhóm (KHÔNG dùng tập ngoài để chọn) ----
    thr_table_hold = threshold_table(p_te, classes, y_te)
    # Quy tắc: độ chính xác cao nhất khi vẫn trả lời được ít nhất 60% số ca
    eligible = [r for r in thr_table_hold if r["coverage"] >= 0.6 and r["top1_acc_on_answered"] is not None]
    chosen_thr = max(eligible, key=lambda r: (r["top1_acc_on_answered"], -r["threshold"]))["threshold"]

    # ---- Tầng 2: tập NGOÀI viết tay ----
    p_ext = model.predict_proba(ext["text"].map(normalize_text))
    pred_ext = classes[p_ext.argmax(axis=1)]
    external = {"top1": round(float((pred_ext == ext["label"]).mean()), 4), "top3": round(topk_accuracy(p_ext, classes, ext["label"], 3), 4),
                "macro_f1": round(float(f1_score(ext["label"], pred_ext, average="macro")), 4), "n": int(len(ext))}
    thr_table_ext = threshold_table(p_ext, classes, ext["label"])
    cm = confusion_matrix(ext["label"], pred_ext, labels=list(classes))
    per_class = classification_report(ext["label"], pred_ext, labels=list(classes), output_dict=True, zero_division=0)
    wrong = [{"text": t, "true": a, "pred": b, "p": round(float(p), 2)} for t, a, b, p in zip(ext["text"], ext["label"], pred_ext, p_ext.max(axis=1)) if a != b]

    # ---- Huấn luyện lại trên TOÀN BỘ dữ liệu sinh để triển khai ----
    final = build_pipeline(grid.best_params_["clf__C"]).fit(X, y)
    version = make_version("triage", str(len(df)), str(SEED), str(grid.best_params_))
    metadata = {
        "purpose": "gợi ý chuyên khoa từ mô tả triệu chứng tiếng Việt (KHÔNG phải chẩn đoán)", "algorithm": "TF-IDF(char 2-5 + word 1-2) + LogisticRegression",
        "classes": list(classes), "n_rows": int(len(df)), "n_base_phrases": int(df["group"].nunique()), "seed": SEED,
        "best_C": grid.best_params_["clf__C"], "uncertain_threshold": chosen_thr, "holdout": holdout, "external": external,
        "data_note": "Dữ liệu do nhóm tự xây từ kiến thức phổ thông, chưa được bác sĩ kiểm định",
    }
    save_model("triage", version, final, metadata)

    summary = dict(version=version, holdout=holdout, external=external, thr_hold=thr_table_hold, thr_ext=thr_table_ext, chosen_thr=chosen_thr,
                   confusion=cm.tolist(), classes=list(classes), per_class={k: {m: round(v, 3) for m, v in per_class[k].items()} for k in classes},
                   wrong=wrong, n_rows=int(len(df)), n_groups=int(df["group"].nunique()), best_C=grid.best_params_["clf__C"])
    write_report(summary)
    return summary


def write_report(s: dict) -> None:
    classes = s["classes"]
    vi = lambda k: DEPARTMENT_LABEL_VI[k]
    header = "| Thực tế \\ Dự đoán | " + " | ".join(vi(c) for c in classes) + " |\n|---|" + "---|" * len(classes)
    cm_rows = "\n".join(f"| **{vi(c)}** | " + " | ".join(str(v) for v in row) + " |" for c, row in zip(classes, s["confusion"]))
    pc = "\n".join(f"| {vi(c)} | {s['per_class'][c]['precision']} | {s['per_class'][c]['recall']} | {s['per_class'][c]['f1-score']} | {int(s['per_class'][c]['support'])} |" for c in classes)
    thr = "\n".join(f"| {a['threshold']} | {a['coverage']} | {a['top1_acc_on_answered']} | {b['coverage']} | {b['top1_acc_on_answered']} |" for a, b in zip(s["thr_hold"], s["thr_ext"]))
    wrong = "\n".join(f"| {w['text']} | {vi(w['true'])} | {vi(w['pred'])} | {w['p']} |" for w in s["wrong"][:20]) or "| (không có) | | | |"
    H, E = s["holdout"], s["external"]
    md = f"""# Báo cáo: phân loại triệu chứng → chuyên khoa

> Sinh tự động bởi `python -m ai_service train-triage` – phiên bản `{s['version']}`.
> ⚠️ **Dữ liệu do nhóm tự xây** từ kiến thức y khoa phổ thông (không phải dữ liệu lâm sàng, chưa được bác sĩ kiểm định). Hệ thống chỉ **gợi ý chuyên khoa**, không chẩn đoán.

## 1. Dữ liệu và cách đánh giá
- {s['n_groups']} triệu chứng gốc cho 8 chuyên khoa, sinh thành **{s['n_rows']:,} câu** (thêm chủ ngữ, thời gian, mức độ, KHÔNG DẤU, gõ sai).
- **Tầng 1 – chia theo nhóm:** các biến thể của cùng một triệu chứng gốc không bao giờ nằm ở cả train lẫn test (mô hình chưa từng thấy cụm triệu chứng test).
- **Tầng 2 – tập ngoài:** {E['n']} câu viết tay tự nhiên, không sinh từ khuôn mẫu, không tham gia huấn luyện hay chọn ngưỡng.
- Mô hình: TF-IDF (ký tự 2–5 + từ 1–2) + Logistic Regression, C={s['best_C']} chọn bằng GroupKFold 5-fold trên train.

## 2. Kết quả

| Tập | Top-1 | Top-3 | Macro-F1 | Số câu |
|---|---|---|---|---|
| Test chia theo nhóm | {H['top1']} | {H['top3']} | {H['macro_f1']} | {H['n']} |
| **Tập ngoài viết tay** | **{E['top1']}** | **{E['top3']}** | **{E['macro_f1']}** | {E['n']} |

**Cách đọc (quan trọng):**
- **Test chia theo nhóm = ước lượng BI QUAN.** Mô hình chưa từng thấy cụm triệu chứng đó, câu lại bị nhiễu nặng (không dấu, gõ sai), và có nhiều triệu chứng mơ hồ thuộc nhiều khoa.
- **Tập ngoài = ước lượng LẠC QUAN.** Câu do chính nhóm viết nên dễ trùng từ khoá với dữ liệu huấn luyện (thiên lệch tác giả). Hiệu năng với người dùng thật nhiều khả năng nằm **giữa hai con số**; muốn biết chắc cần câu của người dùng thật hoặc bác sĩ gán nhãn.
- **Top-3 cao hơn Top-1 rõ rệt** vì nhiều triệu chứng thuộc nhiều khoa (vd. đau lưng lan xuống chân: Cột sống / Thần kinh). Vì vậy hệ thống trả về **3 gợi ý** để bệnh nhân chọn, và kèm ngưỡng "không chắc chắn".

### Từng chuyên khoa (tập ngoài)
| Chuyên khoa | Precision | Recall | F1 | Số câu |
|---|---|---|---|---|
{pc}

### Ma trận nhầm lẫn (tập ngoài)
{header}
{cm_rows}

### Các câu dự đoán sai (tập ngoài)
| Câu | Đúng | Dự đoán | Xác suất |
|---|---|---|---|
{wrong}

## 3. Ngưỡng "không chắc chắn"
Khi xác suất cao nhất thấp hơn ngưỡng, hệ thống không đoán mà đề nghị bệnh nhân mô tả thêm / chọn khoa thủ công. Ngưỡng được chọn trên tập test theo nhóm: **{s['chosen_thr']}**.

| Ngưỡng | Phủ (test nhóm) | Chính xác Top-1 khi trả lời | Phủ (tập ngoài) | Chính xác Top-1 khi trả lời |
|---|---|---|---|---|
{thr}

## 4. Luật an toàn chạy trước mô hình
Dấu hiệu cấp cứu (đau thắt ngực lan, khó thở nặng, nghi đột quỵ, co giật/ngất, nôn ra máu, đau đầu dữ dội đột ngột, ngộ độc, ý định tự hại...) được nhận diện bằng **luật cứng**, ưu tiên an toàn (thà báo nhầm còn hơn bỏ sót) và **không bị mô hình ghi đè**. Mức: `EMERGENCY` (gọi cấp cứu/đến ngay), `URGENT` (khám trong ngày), `ROUTINE`.
"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "triage.md").write_text(md, encoding="utf-8")
    (REPORTS_DIR / "triage.json").write_text(json.dumps(s, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
