"""Test mô hình thời lượng: hợp đồng đặc trưng, mô phỏng, suy luận, dữ liệu thật."""
import math

import numpy as np
import pandas as pd
import pytest

from ai_service.duration import eta_simulation, schema as S, simulate
from ai_service.duration.export_real import build_frame
from ai_service.duration.predictor import DurationPredictor


# ------------------------------------------------ schema ------------------------------------------------
@pytest.mark.parametrize("name,key", [
    ("Tim mạch", "cardiology"), ("Cơ xương khớp", "musculoskeletal"), ("Tiêu Hóa", "digestive"), ("Hô hấp - Phổi", "respiratory"),
    ("Tai mũi họng", "ent"), ("Nha khoa", "dentistry"), ("Cột sống", "spine"), ("Thần kinh", "neurology"),
    ("Cardiovascular", "cardiology"), ("Respiratory - Lungs", "respiratory"), ("ENT", "ent"), ("cardiology", "cardiology"),
])
def test_department_names_from_db_map_to_keys(name, key):
    assert S.normalize_department(name) == key


def test_unknown_department_rejected():
    assert S.normalize_department("Khoa lạ") is None
    with pytest.raises(ValueError, match="chuyên khoa"):
        S.normalize_row({"department": "Khoa lạ"})


def test_normalize_row_fills_defaults_and_reports_them():
    row, used = S.normalize_row({"department": "Tim mạch", "severity": "severe", "age": "70"})
    assert row["severity"] == "SEVERE" and row["age"] == 70
    assert "severity" not in used and "age" not in used
    assert {"visit_type", "source", "queue_length"} <= set(used)


@pytest.mark.parametrize("bad", [
    {"department": "Tim mạch", "age": -3}, {"department": "Tim mạch", "age": "abc"}, {"department": "Tim mạch", "severity": "EXTREME"},
    {"department": "Tim mạch", "queue_length": 9999}, {"department": "Tim mạch", "hour_of_day": 2}, "không phải dict",
])
def test_invalid_input_rejected_with_clear_message(bad):
    with pytest.raises(ValueError):
        S.normalize_row(bad)


def test_gender_aliases():
    assert S.normalize_row({"department": "ent", "gender": "nam"})[0]["gender"] == "M"
    assert S.normalize_row({"department": "ent", "gender": "female"})[0]["gender"] == "F"


# ------------------------------------------------ mô phỏng ------------------------------------------------
def test_simulation_is_deterministic_and_well_formed():
    a, b = simulate.simulate(60, seed=7), simulate.simulate(60, seed=7)
    pd.testing.assert_frame_equal(a, b)
    assert not simulate.simulate(60, seed=8).equals(a)
    assert set(S.FEATURES + [S.TARGET, "session_id", "position"]) <= set(a.columns)
    assert a[S.TARGET].between(S.MIN_DURATION, S.MAX_DURATION).all()
    assert set(a["department"]) <= set(S.DEPARTMENTS)
    # vị trí trong buổi liên tục từ 0
    assert (a.groupby("session_id")["position"].apply(lambda s: list(s) == list(range(len(s))))).all()


def _row(**over):
    base = {"department": "cardiology", "severity": "MODERATE", "visit_type": "NEW", "source": "BOOKED", "age": 35, "chronic_count": 0,
            "doctor_experience_years": 10, "hour_of_day": 9.0, "queue_length": 0}
    base.update(over)
    return base


def test_expected_minutes_monotonic_in_the_assumptions():
    e = simulate.expected_minutes
    assert e(_row(severity="SEVERE")) > e(_row(severity="MODERATE")) > e(_row(severity="MILD"))
    assert e(_row(visit_type="NEW")) > e(_row(visit_type="FOLLOW_UP"))
    assert e(_row(age=80)) > e(_row(age=35)) and e(_row(age=4)) > e(_row(age=35))
    assert e(_row(chronic_count=3)) > e(_row(chronic_count=0))
    assert e(_row(doctor_experience_years=2)) > e(_row(doctor_experience_years=30))
    assert e(_row(source="WALK_IN")) > e(_row(source="BOOKED"))
    assert e(_row(queue_length=14)) < e(_row(queue_length=0))  # hàng đợi dài => bác sĩ nhanh hơn
    assert e(_row(hour_of_day=11.5)) > e(_row(hour_of_day=8.0))  # cuối buổi mệt hơn


def test_assumptions_table_lists_every_department():
    md = simulate.assumptions_markdown()
    assert all(S.DEPARTMENT_LABEL_VI[d] in md for d in S.DEPARTMENTS)


# ------------------------------------------------ suy luận bằng mô hình đã huấn luyện ------------------------------------------------
@pytest.fixture(scope="module")
def predictor():
    try:
        return DurationPredictor()
    except FileNotFoundError:
        pytest.skip("chưa huấn luyện mô hình thời lượng (python -m ai_service train-duration)")


def test_model_predictions_are_sane_and_ordered(predictor):
    base = {"department": "Tim mạch", "visit_type": "NEW", "source": "BOOKED", "age": 40, "queue_length": 2}
    mild, mod, sev = (predictor.predict([{**base, "severity": s}])[0] for s in ("MILD", "MODERATE", "SEVERE"))
    assert mild["duration_min"] < mod["duration_min"] < sev["duration_min"]
    new = predictor.predict([{**base, "severity": "MODERATE", "visit_type": "NEW"}])[0]["duration_min"]
    fol = predictor.predict([{**base, "severity": "MODERATE", "visit_type": "FOLLOW_UP"}])[0]["duration_min"]
    assert new > fol
    for r in (mild, mod, sev):
        assert S.MIN_DURATION <= r["p10_min"] <= r["duration_min"] <= r["p90_min"] <= S.MAX_DURATION


def test_model_batch_equals_single_and_reports_defaults(predictor):
    items = [{"department": d} for d in ("Tim mạch", "Nha khoa", "Thần kinh")]
    batch = predictor.predict(items)
    assert [b["duration_min"] for b in batch] == [predictor.predict([i])[0]["duration_min"] for i in items]
    assert "severity" in batch[0]["used_defaults"] and batch[0]["model_version"] == predictor.version


def test_model_rejects_bad_item_with_index(predictor):
    with pytest.raises(ValueError, match="Phần tử #1"):
        predictor.predict([{"department": "Tim mạch"}, {"department": "???"}])


def test_model_beats_constant_15_in_metadata(predictor):
    m = predictor.meta
    assert m["metrics_test"]["mae"] < m["baseline_const15_mae"]
    assert m["eta_improvement_pct"] > 20
    assert 0.7 <= m["interval"]["coverage_test"] <= 0.9  # khoảng p10–p90 phủ ≈ 80%


# ------------------------------------------------ ETA ------------------------------------------------
def test_eta_comparison_gives_zero_error_for_perfect_predictions():
    df = pd.DataFrame({"session_id": [1, 1, 1, 1], "position": [0, 1, 2, 3], "duration_min": [10.0, 20.0, 5.0, 15.0]})
    res = eta_simulation.compare(df, {"hoàn hảo": df["duration_min"].to_numpy(), "cố định 15": np.full(4, 15.0)}, reference="cố định 15")
    assert res["hoàn hảo"]["mae_overall"] == 0
    assert res["hoàn hảo"]["improvement_vs_reference_pct"] == 100.0
    # bệnh nhân đầu tiên (chờ 0) không tính vào sai số
    assert res["cố định 15"]["n"] == 3


# ------------------------------------------------ dữ liệu thật xuất từ hàng đợi ------------------------------------------------
def _raw_tickets(n=12):
    t0 = pd.Timestamp("2026-11-12 08:00:00")
    rows = []
    for i in range(n):
        start = t0 + pd.Timedelta(minutes=20 * i)
        rows.append({"ticket_id": i + 1, "doctor_id": 5, "ticket_date": "2026-11-12", "shift": "MORNING", "source": "BOOKED" if i % 2 else "WALK_IN",
                     "check_in_at": start - pd.Timedelta(minutes=30), "started_at": start, "finished_at": start + pd.Timedelta(minutes=10 + i % 3),
                     "years_of_experience": 12, "specialty_vi": "Tim mạch", "date_of_birth": "1960-01-01", "gender_code": "M",
                     "chronic_conditions": "Cao huyết áp, tiểu đường", "severity": "SEVERE" if i == 0 else None})
    return pd.DataFrame(rows)


def test_build_frame_from_queue_rows_matches_contract():
    f = build_frame(_raw_tickets())
    assert set(S.FEATURES + [S.TARGET, "session_id", "position"]) <= set(f.columns)
    assert len(f) == 12 and f["department"].eq("cardiology").all()
    assert f["age"].iloc[0] == 67 and f["chronic_count"].iloc[0] == 2
    assert f["severity"].iloc[0] == "SEVERE" and f["severity"].iloc[1] == "MODERATE"  # thiếu -> mặc định
    assert list(f["position"]) == list(range(12)) and f["session_id"].nunique() == 1
    # lịch sử bác sĩ chỉ dùng các ca TRƯỚC (không rò rỉ nhãn): 5 ca đầu chưa đủ để tính
    assert f["doctor_hist_avg_min"].iloc[:5].isna().all()
    assert math.isclose(f["doctor_hist_avg_min"].iloc[5], f["duration_min"].iloc[:5].mean(), abs_tol=0.01)


def test_build_frame_drops_noise_rows():
    raw = _raw_tickets(8)
    raw.loc[0, "finished_at"] = raw.loc[0, "started_at"] + pd.Timedelta(seconds=10)  # bấm nhầm
    raw.loc[1, "finished_at"] = raw.loc[1, "started_at"] + pd.Timedelta(hours=6)  # quên bấm hoàn thành
    raw.loc[2, "specialty_vi"] = "Khoa lạ"
    assert len(build_frame(raw)) == 5
    assert build_frame(raw.iloc[0:0]).empty
