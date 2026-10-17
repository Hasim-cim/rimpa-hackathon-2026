import importlib

import pytest
from fastapi.testclient import TestClient

from recordcheck import db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "api.sqlite"))
    import api.main as main
    main = importlib.reload(main)
    yield TestClient(main.app)
    main.conn.close()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_check_seed_document(client):
    r = client.post("/check", json={"document_id": "DOC-2026/0412-summary"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["citations"]) == 4
    assert len(body["assessment"]["verdicts"]) == 7


def test_check_unknown_document(client):
    assert client.post("/check", json={"document_id": "nope"}).status_code == 404


def test_passport_issue_and_get(client):
    ev = {"id": "EVT-API-1", "app_id": "agency-assistant", "user": "A. Caseworker",
          "created": "2026-10-17T09:00:00", "prompt": "p", "output": "o",
          "model_requested": "northstar-8-2026-09-15", "model_returned": "northstar-8-2026-09-15",
          "provider": "Northstar AI (fictional vendor)", "decision_flag": True,
          "exported_to_document": "DOC-2026/0412-summary", "function": "Debt waiver assessment"}
    r = client.post("/passport", json={"event": ev, "review": None, "tier": None})
    assert r.status_code == 200
    p = r.json()
    assert p["business"]["tier"] == "T2"
    got = client.get("/passport/" + p["record"]["id"])
    assert got.status_code == 200 and got.json()["integrity"]["hash"] == p["integrity"]["hash"]
    assert client.get("/passport/REC-9999/1").status_code == 404
    assert client.get("/chain/verify").json()["ok"] is True


def test_recall(client):
    r = client.post("/recall", json={"model_id": "northstar-7-2026-03-01"})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 14
    r = client.post("/recall", json={"model_id": "northstar-7-2026-03-01", "mark": {
        "status": "faulty", "effective_from": "2026-03-01", "reason": "x", "by": "IM"}})
    assert r.json()["entry"]["status"] == "faulty"


def test_chain_verify(client):
    j = client.get("/chain/verify").json()
    assert j["ok"] is True and j["checked"] > 0


def test_api_refuses_blocked_passport(client):
    """A Blocked document cannot get a passport through the API either."""
    r = client.post("/check", json={"document_id": "DOC-2026/0412-summary"})
    assert r.status_code == 200
    body = r.json()
    ev = {"id": "EVT-api-blocked", "app_id": "agency-assistant", "user": "u", "created": "2026-10-17T12:00:00",
          "prompt": "p", "output": "o", "model_requested": "m", "model_returned": "m", "provider": "v",
          "decision_flag": True}
    r = client.post("/passport", json={"event": ev, "citations": body["citations"], "assessment": body["assessment"],
                                       "document_type": "decision-letter"})
    assert r.status_code == 409 and r.json()["detail"]["gate"] == "blocked"
