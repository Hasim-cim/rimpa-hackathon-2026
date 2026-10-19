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


def test_read_endpoints_and_check_gate(client):
    docs = client.get("/documents").json()
    assert "DOC-2026/0412-summary" in [d["id"] for d in docs]
    assert client.get("/records").json()
    types = [t["id"] for t in client.get("/policy").json()["document_types"]]
    assert "decision-letter" in types
    r = client.post("/check", json={"document_id": "DOC-2026/0412-summary", "document_type": "decision-letter"})
    assert r.json()["gate"]["status"] == "blocked"     # the demo draft: fabricated reference, contradiction
    assert client.post("/check", json={"document_id": "DOC-2026/0412-summary"}).json()["gate"] is None
    assert client.post("/check", json={"document_id": "DOC-2026/0412-summary", "document_type": "nope"}).status_code == 422


def test_source_health_and_source_recall(client):
    h = client.get("/sources/health").json()
    assert h["counts"]["draft"] == 1 and h["counts"]["redundant"] == 1
    r = client.post("/recall/record", json={"record_id": "REC-2026/004790"})
    assert r.status_code == 200 and r.json()["counts"]["T2"] == 4
    assert client.post("/recall/record", json={"record_id": "NO-SUCH"}).status_code == 404
    bad = {"record_id": "REC-2026/004790", "mark": {"superseded_by": "NO-SUCH", "reason": "r", "by": "I. Manager"}}
    assert client.post("/recall/record", json=bad).status_code == 422


def test_console_endpoints(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))  # never touch data/policy.json
    ps = client.get("/passports").json()
    assert len(ps) == 40 and ps[0]["record"]["created"] >= ps[-1]["record"]["created"]
    assert "northstar-7-2026-03-01" in [m["model_id"] for m in client.get("/models").json()]
    t2 = [i["record_id"] for i in client.post("/recall", json={"model_id": "northstar-7-2026-03-01"}).json()["items"]
          if i["tier"] == "T2"]
    assert client.post("/recall/queue", json={"record_ids": t2, "reason": "r", "by": "IM"}).json()["queued"] == 3
    assert client.get("/audit").json()

    due = [i["record_id"] for i in client.get("/disposal/due").json() if not i["on_hold"]]
    assert due
    bad = client.post("/disposal/approve", json={"record_ids": due, "approved_by": " ", "reason": "r"})
    assert bad.status_code == 422
    done = client.post("/disposal/approve", json={"record_ids": due, "approved_by": "IM", "reason": "past retention"})
    assert len(done.json()) == len(due) and len(client.get("/disposal/register").json()) == len(due)
    assert client.get("/chain/verify").json()["ok"] is True

    pol = client.get("/policy").json()
    pol["organisation"] = "Test Agency"
    saved = client.put("/policy", json={"policy": pol, "by": "IM"}).json()
    assert saved["organisation"] == "Test Agency" and int(saved["version"]) == int(pol["version"]) + 1
    pol["document_types"][0]["quality"]["max_unsupported"] = -1
    assert client.put("/policy", json={"policy": pol, "by": "IM"}).status_code == 422
    preset = client.get("/presets").json()[0]["id"]
    reset = client.post("/policy/preset", json={"preset_id": preset, "organisation": "X", "by": "IM"}).json()
    assert reset["sector"] == preset and int(reset["version"]) == int(saved["version"]) + 1
    assert client.post("/policy/suggest", json={"description": "a hospital"}).json() is None  # LLM off in tests


def test_passport_tier_floor_is_document_type_default(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    doc = "DOC-2026/0587-eligibility"
    ch = client.post("/check", json={"document_id": doc, "document_type": "decision-letter"}).json()
    ev = {"id": "EVT-API-FLOOR", "app_id": "agency-assistant", "user": "A. Caseworker", "created": "2026-10-17T09:00:00",
          "prompt": "p", "output": "o", "model_requested": "m", "model_returned": "m", "provider": "p",
          "exported_to_document": doc}  # the rules alone give T1; a decision letter defaults to T2
    r = client.post("/passport", json={"event": ev, "document_type": "decision-letter", "citations": ch["citations"],
                                       "assessment": ch["assessment"], "review": {"reviewer": "B. Team Leader",
                                       "decision": "approved", "reviewed_at": "2026-10-17T10:00:00"}})
    assert r.status_code == 200 and r.json()["business"]["tier"] == "T2"
