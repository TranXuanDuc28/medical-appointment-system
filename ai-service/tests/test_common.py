"""Test tiện ích dùng chung: chỉ số đánh giá, kho mô hình."""
import json

import numpy as np
import pytest

from ai_service.common import metrics, registry


def test_regression_report_known_values():
    y = np.array([10.0, 20.0, 30.0, 40.0])
    p = np.array([12.0, 18.0, 33.0, 36.0])
    r = metrics.regression_report(y, p)
    assert r["mae"] == pytest.approx(2.75, abs=1e-3)  # (2+2+3+4)/4
    assert r["rmse"] == pytest.approx(np.sqrt((4 + 4 + 9 + 16) / 4), abs=1e-3)
    assert r["within_5_min"] == 1.0
    assert r["n"] == 4


def test_r2_perfect_and_mean_predictor():
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert metrics.r2(y, y) == pytest.approx(1.0)
    assert metrics.r2(y, np.full(5, y.mean())) == pytest.approx(0.0, abs=1e-12)


def test_bootstrap_ci_brackets_point_estimate_and_is_reproducible():
    rng = np.random.default_rng(0)
    y = rng.normal(20, 5, 500)
    p = y + rng.normal(0, 3, 500)
    lo, hi = metrics.bootstrap_ci(y, p, metrics.mae, n_boot=300, seed=1)
    assert lo <= metrics.mae(y, p) <= hi
    assert (lo, hi) == metrics.bootstrap_ci(y, p, metrics.mae, n_boot=300, seed=1)


def test_improvement_pct():
    assert metrics.improvement_pct(10, 6) == 40.0
    assert metrics.improvement_pct(0, 5) == 0.0


def test_registry_roundtrip_and_current_pointer(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "MODELS_DIR", tmp_path)
    v1 = registry.make_version("a", "b")
    registry.save_model("demo", v1, {"x": 1}, {"algorithm": "dummy"})
    model, meta = registry.load_current("demo", tmp_path)
    assert model == {"x": 1} and meta["version"] == v1 and meta["algorithm"] == "dummy"
    v2 = "20300101-test"
    registry.save_model("demo", v2, {"x": 2}, {})
    assert registry.load_current("demo", tmp_path)[0] == {"x": 2}
    assert json.loads((tmp_path / "demo" / "current.json").read_text())["version"] == v2
    # có thể quay lại phiên bản cũ mà không mất file
    assert (tmp_path / "demo" / v1 / "model.joblib").is_file()


def test_registry_missing_model_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Chưa có mô hình"):
        registry.load_current("khong-ton-tai", tmp_path)


def test_make_version_deterministic_for_same_inputs():
    assert registry.make_version("x", "y")[-8:] == registry.make_version("x", "y")[-8:]
    assert registry.make_version("x", "y")[-8:] != registry.make_version("x", "z")[-8:]
