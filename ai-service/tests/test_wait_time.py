"""Test pipeline dự đoán thời gian chờ trên dataset Kaggle (chống rò rỉ dữ liệu)."""
import pytest

from ai_service.config import kaggle_csv_path
from ai_service.wait_time import data as D


@pytest.fixture(scope="module")
def df():
    try:
        kaggle_csv_path()
    except FileNotFoundError:
        pytest.skip("không có dataset Kaggle")
    return D.load_raw()


def test_dataset_shape_and_no_missing(df):
    assert len(df) == 10_000 and df.shape[1] == 26
    assert df.isna().sum().sum() == 0


def test_leaky_columns_never_in_features(df):
    X, y = D.split_xy(df)
    assert not set(D.LEAKY_COLUMNS) & set(X.columns)
    assert D.TARGET not in X.columns and D.ID_COLUMN not in X.columns
    assert "symptoms" not in X.columns  # trùng 1-1 với department
    assert len(X) == len(y) == len(df)


def test_leaky_columns_do_exist_and_leak(df):
    """Đảm bảo lý do loại bỏ là có thật: cột điểm hài lòng tương quan mạnh (âm) với nhãn."""
    assert abs(df["patient_satisfaction_score"].corr(df[D.TARGET])) > 0.5


def test_feature_lists_cover_all_non_excluded_columns(df):
    used = set(D.FEATURES) | set(D.LEAKY_COLUMNS) | set(D.REDUNDANT_COLUMNS) | {D.TARGET, D.ID_COLUMN}
    assert set(df.columns) == used


def test_severity_is_the_only_strong_signal(df):
    means = df.groupby("severity_level")[D.TARGET].mean()
    assert means.max() - means.min() > 15
    for c in ("gender", "insurance", "city"):
        g = df.groupby(c)[D.TARGET].mean()
        assert g.max() - g.min() < 2.5, c
