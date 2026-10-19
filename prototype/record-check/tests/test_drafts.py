"""Send for review (deck): the server re-runs the check, keeps its own reasons, refuses a ready draft, reuses an open
review, writes an audit row, and stores nothing pasted but a title and a hash. Offline."""
from __future__ import annotations

import importlib

import pytest

from recordcheck import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "p.json"))
    import api.main as main
    main = importlib.reload(main)
    yield TestClient(main.app), main
    main.conn.close()


SUMMARY = {"document_id": "DOC-2026/0412-summary", "document_type": "decision-letter", "requested_by": "A. Caseworker"}


def test_a_blocked_draft_is_sent_with_the_servers_own_reasons(client):
    c, main = client
    r = c.post("/drafts/review", json={**SUMMARY, "note": "please look", "reasons": ["caller made this up"]})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["id"] == "DR-000001" and j["status"] == "open" and j["gate"] == "blocked"
    assert any("not found ([4])" in x for x in j["reasons"]) and "caller made this up" not in j["reasons"]
    assert main.conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='draft.sent_for_review'").fetchone()[0] == 1


def test_idempotent_while_open_and_listed_newest_first(client):
    c, _ = client
    first = c.post("/drafts/review", json=SUMMARY).json()
    again = c.post("/drafts/review", json=SUMMARY).json()
    assert again["id"] == first["id"]
    other = c.post("/drafts/review", json={**SUMMARY, "document_type": "briefing"}).json()   # another type: new
    assert other["id"] != first["id"]
    assert [d["id"] for d in c.get("/drafts/review").json()] == [other["id"], first["id"]]


def test_a_ready_draft_has_nothing_to_review(client):
    c, _ = client
    r = c.post("/drafts/review", json={"document_id": "DOC-2026/0587-eligibility", "document_type": "case-note",
                                       "requested_by": "A. Caseworker"})
    assert r.status_code == 422 and "File it instead" in r.json()["detail"]


def test_unknown_document_and_bad_requests(client):
    c, _ = client
    assert c.post("/drafts/review", json={**SUMMARY, "document_id": "NOPE"}).status_code == 404
    assert c.post("/drafts/review", json={**SUMMARY, "requested_by": "  "}).status_code == 422
    assert c.post("/drafts/review", json={**SUMMARY, "document_type": "no-such-type"}).status_code == 422


def test_a_pasted_draft_keeps_only_its_title_and_a_hash(client):
    c, main = client
    body = "The applicant lives alone. My secret personal detail."
    r = c.post("/drafts/review", json={"title": "Pasted note", "body": body, "case_id": "2026/0412",
                                       "document_type": "case-note", "requested_by": "Visitor"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["document_id"] is None and j["title"] == "Pasted note" and len(j["body_hash"]) == 64
    stored = " ".join(row["payload"] for row in main.conn.execute("SELECT payload FROM draft_reviews"))
    assert "secret personal detail" not in stored and "lives alone" not in stored     # nothing pasted is stored
    audit = " ".join(row["detail"] for row in main.conn.execute("SELECT detail FROM audit_log"))
    assert "secret" not in audit


def test_dashboard_counts_open_draft_reviews(client):
    c, _ = client
    c.post("/drafts/review", json=SUMMARY)
    assert c.get("/dashboard").json()["queue"]["drafts_open"] == 1
