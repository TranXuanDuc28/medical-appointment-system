"""Giao diện dòng lệnh:  python -m ai_service <lệnh>

  simulate          sinh dữ liệu mô phỏng thời lượng khám (data/synthetic/)
  train-wait        huấn luyện + báo cáo dự đoán thời gian chờ trên dataset Kaggle
  train-duration    huấn luyện mô hình thời lượng khám (--source synthetic|real)
  build-triage      sinh bộ dữ liệu triệu chứng tiếng Việt (data/triage/)
  train-triage      huấn luyện + báo cáo phân loại triệu chứng
  export-real       xuất dữ liệu thật từ hàng đợi (MySQL) để tái huấn luyện
  train-all         chạy lần lượt tất cả bước trên (dữ liệu mô phỏng)
  serve             chạy dịch vụ HTTP (mặc định cổng 8001)
  triage "<text>"   thử nhanh phân loại một câu
  predict           thử nhanh dự đoán thời lượng (--department ... )
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def _utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8()
    p = argparse.ArgumentParser(prog="ai_service", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("simulate")
    sub.add_parser("train-wait")
    td = sub.add_parser("train-duration")
    td.add_argument("--source", choices=["synthetic", "real"], default="synthetic")
    td.add_argument("--regenerate", action="store_true", help="sinh lại dữ liệu mô phỏng")
    td.add_argument("--sessions", type=int, default=3000, help="số buổi khám mô phỏng")
    sub.add_parser("build-triage")
    sub.add_parser("train-triage")
    sub.add_parser("export-real")
    sub.add_parser("train-all")
    sv = sub.add_parser("serve")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=int(os.getenv("AI_PORT", "8001")))
    tr = sub.add_parser("triage")
    tr.add_argument("text")
    pr = sub.add_parser("predict")
    pr.add_argument("--department", required=True)
    pr.add_argument("--severity")
    pr.add_argument("--visit-type", dest="visit_type")
    pr.add_argument("--source")
    pr.add_argument("--age", type=int)
    pr.add_argument("--queue-length", dest="queue_length", type=int)
    a = p.parse_args(argv)

    if a.cmd == "simulate":
        from ai_service.duration import simulate
        df = simulate.load_or_generate(force=True)
        print(f"Đã sinh {len(df):,} ca / {df['session_id'].nunique():,} buổi -> {simulate.synthetic_path()}")
    elif a.cmd == "train-wait":
        from ai_service.wait_time.train import run
        s = run()
        print(f"Mô hình chọn: {s['best']} | MAE {s['best_mae']} (baseline {s['baseline_mae']}) | báo cáo: reports/wait_time_kaggle.md")
    elif a.cmd == "train-duration":
        from ai_service.duration.train import run
        s = run(a.source, a.regenerate, a.sessions)
        r = s["results"][s["chosen"]]
        eta_gain = s["eta"][f"ML: {s['chosen']}"]["improvement_vs_reference_pct"]
        print(f"Mô hình chọn: {s['chosen']} | MAE {r['mae']} phút, R² {r['r2']} | cải thiện ETA {eta_gain}% | báo cáo: reports/duration_model.md")
    elif a.cmd == "build-triage":
        from ai_service.triage import build_dataset
        df = build_dataset.write()
        print(f"Đã sinh {len(df):,} câu / {df['group'].nunique()} triệu chứng gốc -> {build_dataset.dataset_path()}")
    elif a.cmd == "train-triage":
        from ai_service.triage.train import run
        s = run()
        print(f"Top-1 (test theo nhóm) {s['holdout']['top1']} | Top-1 (tập ngoài) {s['external']['top1']} | báo cáo: reports/triage.md")
    elif a.cmd == "export-real":
        from ai_service.duration.export_real import export
        frame, path = export()
        print(f"Đã xuất {len(frame):,} ca thật ({frame['session_id'].nunique() if len(frame) else 0} buổi) -> {path}")
        if len(frame) < 200:
            print("⚠️  Chưa đủ 200 ca để huấn luyện có ý nghĩa; hãy vận hành hệ thống thêm.")
    elif a.cmd == "train-all":
        for cmd in (["train-wait"], ["train-duration", "--regenerate"], ["train-triage"]):
            print(f"\n=== {' '.join(cmd)} ===")
            main(cmd)
    elif a.cmd == "serve":
        import uvicorn
        uvicorn.run("ai_service.serve.app:app", host=a.host, port=a.port)
    elif a.cmd == "triage":
        from ai_service.triage.predictor import TriagePredictor
        print(json.dumps(TriagePredictor().predict(a.text), ensure_ascii=False, indent=2))
    elif a.cmd == "predict":
        from ai_service.duration.predictor import DurationPredictor
        req = {k: v for k, v in vars(a).items() if k != "cmd" and v is not None}
        print(json.dumps(DurationPredictor().predict([req])[0], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
