"""Test phân loại triệu chứng: luật an toàn (quan trọng nhất), bộ dữ liệu, mô hình."""
import pytest

from ai_service.triage import build_dataset, lexicon as L
from ai_service.triage.predictor import TriagePredictor
from ai_service.triage.rules import EMERGENCY, ROUTINE, URGENT, assess_urgency, normalize_text


# ------------------------------------------------ luật cấp cứu ------------------------------------------------
@pytest.mark.parametrize("text", [
    "tôi bị đau thắt ngực lan ra vai trái", "đau ngực dữ dội vã mồ hôi", "khó thở dữ dội đột ngột", "tôi không thở được",
    "bố tôi bị méo miệng nói ngọng đột ngột", "liệt nửa người bên phải", "con tôi bị co giật", "em bị ngất xỉu giữa lớp",
    "bi ngat xiu", "nôn ra máu nhiều", "đau đầu dữ dội đột ngột chưa từng thấy", "nghi ngộ độc thuốc", "toi muon tu tu",
    "TÔI BỊ ĐAU THẮT NGỰC", "dau that nguc", "hôn mê",
])
def test_emergency_rules_catch_dangerous_signs(text):
    urgency, reasons = assess_urgency(text)
    assert urgency == EMERGENCY and reasons, text


@pytest.mark.parametrize("text", [
    "tôi bị ngạt mũi 3 ngày", "bị ngạt mũi về đêm", "đi ngoài mấy lần đến nay", "đau họng nhẹ", "hơi đau đầu",
    "chảy máu chân răng khi đánh răng", "chảy máu cam thỉnh thoảng", "thở nặng nhọc khi gặp lạnh", "đau lưng khi cúi",
    "ho khan về đêm", "khó thở khi leo cầu thang", "mất ngủ kéo dài", "ngón chân cái sưng đỏ", "nghi ngộ độc thực phẩm",
])
def test_emergency_rules_do_not_overfire_on_routine_complaints(text):
    assert assess_urgency(text)[0] != EMERGENCY, text


@pytest.mark.parametrize("text", ["đi cầu ra máu tươi", "ho ra máu", "đi ngoài phân đen", "vàng da vàng mắt", "tức ngực khó thở khi nằm"])
def test_urgent_rules(text):
    assert assess_urgency(text)[0] == URGENT, text


def test_routine_by_default():
    assert assess_urgency("tôi muốn lấy cao răng")[0] == ROUTINE


def test_normalize_text_strips_accents_and_noise():
    assert normalize_text("  Đau Thắt-Ngực!!  ") == "dau that nguc"


# ------------------------------------------------ bộ dữ liệu ------------------------------------------------
def test_dataset_is_deterministic_balanced_and_grouped():
    a, b = build_dataset.build(1), build_dataset.build(1)
    assert a.equals(b)
    assert set(a["label"]) == set(L.SYMPTOMS)
    counts = a["label"].value_counts()
    assert counts.min() / counts.max() > 0.8  # các lớp cân bằng
    # mỗi nhóm (triệu chứng gốc) thuộc đúng một nhãn => chia theo nhóm không rò rỉ
    assert (a.groupby("group")["label"].nunique() == 1).all()
    # có biến thể KHÔNG DẤU trong dữ liệu (người dùng hay gõ không dấu)
    assert a["text"].map(lambda t: t == t.encode("ascii", "ignore").decode()).any()


def test_external_test_set_is_independent_of_training_phrases():
    train_phrases = {normalize_text(p) for ps in L.SYMPTOMS.values() for p in ps}
    ext_texts = {normalize_text(t) for t, _ in L.EXTERNAL_TEST}
    assert not (train_phrases & ext_texts)
    assert {label for _, label in L.EXTERNAL_TEST} == set(L.SYMPTOMS)


# ------------------------------------------------ mô hình ------------------------------------------------
@pytest.fixture(scope="module")
def triage():
    try:
        return TriagePredictor()
    except FileNotFoundError:
        pytest.skip("chưa huấn luyện mô hình triage (python -m ai_service train-triage)")


def test_triage_external_accuracy_floor(triage):
    """Sàn chất lượng trên tập ngoài viết tay (không dùng để huấn luyện)."""
    hit1 = hit3 = 0
    for text, label in L.EXTERNAL_TEST:
        keys = [p["specialty_key"] for p in triage.predict(text)["predictions"]]
        hit1 += keys[0] == label
        hit3 += label in keys
    n = len(L.EXTERNAL_TEST)
    assert hit1 / n >= 0.80 and hit3 / n >= 0.90


def test_triage_emergency_is_never_overridden_by_model(triage):
    r = triage.predict("Tôi đau ngực dữ dội lan ra tay trái, vã mồ hôi")
    assert r["urgency"] == EMERGENCY and r["recommendation"] == "CALL_EMERGENCY" and "115" in r["advice"]


@pytest.mark.parametrize("text,expected", [
    ("đau răng nhức buốt không ăn được", "dentistry"), ("đau lưng lan xuống chân tê bì", "spine"),
    ("sốt ho đờm vàng khó thở khò khè", "respiratory"), ("ợ chua đau thượng vị buồn nôn", "digestive"),
])
def test_triage_obvious_cases(triage, text, expected):
    assert triage.predict(text)["predictions"][0]["specialty_key"] == expected


def test_triage_output_contract_and_uncertainty(triage):
    r = triage.predict("hôm nay tôi thấy không khỏe")
    assert len(r["predictions"]) == 3 and abs(sum(p["probability"] for p in r["predictions"])) <= 1.0001
    assert r["predictions"] == sorted(r["predictions"], key=lambda p: -p["probability"])
    assert r["disclaimer"] and r["model_version"]
    assert r["uncertain"] == (r["predictions"][0]["probability"] < r["uncertain_threshold"])


@pytest.mark.parametrize("bad", ["", "  ", "ab", "x" * 1001, None, 123])
def test_triage_rejects_bad_text(triage, bad):
    with pytest.raises(ValueError):
        triage.predict(bad)
