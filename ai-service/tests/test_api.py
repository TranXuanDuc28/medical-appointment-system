"""Test API HTTP (FastAPI TestClient) với mô hình đã huấn luyện trong thư mục models/."""
import pytest
from fastapi.testclient import TestClient

from ai_service.serve.app import create_app


@pytest.fixture()
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture()
def secured(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_TOKEN", "bi-mat-123")
    with TestClient(create_app()) as c:
        yield c


def _need_models(client):
    h = client.get("/health").json()
    if h["status"] != "ok":
        pytest.skip(f"chưa đủ mô hình: {h}")
    return h


def test_health_reports_model_versions(client):
    h = _need_models(client)
    assert h["models"]["duration"] and h["models"]["triage"]


def test_predict_duration_batch(client):
    _need_models(client)
    r = client.post("/predict-duration", json={"items": [
        {"department": "Tim mạch", "severity": "SEVERE", "age": 70}, {"department": "Nha khoa", "severity": "MILD"}]})
    assert r.status_code == 200
    body = r.json()
    assert len(body["predictions"]) == 2 and body["model_version"]
    p = body["predictions"][0]
    assert p["p10_min"] <= p["duration_min"] <= p["p90_min"] and isinstance(p["used_defaults"], list)


@pytest.mark.parametrize("payload", [
    {"items": []}, {"items": [{"department": "???"}]}, {"items": [{"department": "Tim mạch", "age": -5}]},
    {"items": [{"department": "Tim mạch"}] * 201}, {}, {"items": "không phải danh sách"},
])
def test_predict_duration_rejects_bad_requests(client, payload):
    _need_models(client)
    assert client.post("/predict-duration", json=payload).status_code in (400, 422)


def test_bad_item_error_message_names_the_index(client):
    _need_models(client)
    r = client.post("/predict-duration", json={"items": [{"department": "Tim mạch"}, {"department": "???"}]})
    assert r.status_code == 422 and "#1" in r.json()["detail"]


def test_triage_endpoint(client):
    _need_models(client)
    r = client.post("/triage", json={"text": "đau thắt ngực lan ra vai trái, vã mồ hôi"})
    assert r.status_code == 200
    b = r.json()
    assert b["urgency"] == "EMERGENCY" and b["recommendation"] == "CALL_EMERGENCY"
    assert client.post("/triage", json={"text": "ab"}).status_code == 422
    assert client.post("/triage", json={}).status_code == 422


def test_token_required_when_configured(secured):
    _need_models(secured)
    body = {"items": [{"department": "Tim mạch"}]}
    assert secured.get("/health").status_code == 200  # health luôn mở cho giám sát
    assert secured.post("/predict-duration", json=body).status_code == 401
    assert secured.post("/predict-duration", json=body, headers={"X-AI-Token": "sai"}).status_code == 401
    assert secured.post("/predict-duration", json=body, headers={"X-AI-Token": "bi-mat-123"}).status_code == 200
    assert secured.get("/model-info").status_code == 401
    assert secured.post("/triage", json={"text": "đau răng"}).status_code == 401


def test_service_degrades_gracefully_without_models(tmp_path):
    with TestClient(create_app(tmp_path)) as c:  # thư mục models trống
        h = c.get("/health").json()
        assert h["status"] == "degraded" and h["models"] == {"duration": None, "triage": None}
        assert c.post("/predict-duration", json={"items": [{"department": "Tim mạch"}]}).status_code == 503
        assert c.post("/triage", json={"text": "đau răng"}).status_code == 503
