"""Passport view (P1): the checks shown are what was checked at issue; seed passports still verify; 'Since filing'
is the one live check. Offline."""
from __future__ import annotations

import importlib
import json
from datetime import date, datetime, timezone

import pytest

from recordcheck import citations as cit
from recordcheck import db, disposal, evidence, passport, recall
from recordcheck import policy as policymod
from recordcheck.models import AIEvent, Review

ELIG, SUMMARY = "DOC-2026/0587-eligibility", "DOC-2026/0412-summary"
OLD_NOTICE, NEW_NOTICE = "REC-2026/004790", "REC-2026/004912"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "v.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    c = db.open_db()
    yield c, policymod.load()
    c.close()


def _file(conn, pol, doc_id=ELIG, dtype="decision-letter", user="A. Caseworker"):
    doc = db.get_document(conn, doc_id)
    res = cit.check_document(doc.references, conn=conn)
    a = evidence.assess(doc, conn, res, policy=pol, document_type=dtype)
    ev = AIEvent(id=f"EVT-V-{doc_id}", app_id="agency-assistant", user=user, created=datetime(2026, 10, 19, 10),
                 prompt="p", output=doc.body, model_requested="northstar-8-2026-09-15",
                 model_returned="northstar-8-2026-09-15", provider="x", exported_to_document=doc.id, decision_flag=True,
                 source_record_ids=sorted({l.record_id for v in a.verdicts for l in v.links}), function="Review")
    p = passport.build(ev, tier="T2", assessment=a, citations=res, conn=conn, policy=pol, document_type=dtype,
                       review=Review(reviewer="B. Team Leader", decision="approved",
                                     reviewed_at=datetime(2026, 10, 19, 11, tzinfo=timezone.utc)))
    return p, a, res


def checks(v):
    return {c.id: c for c in v.checks}


def test_view_of_a_new_passport_is_what_was_checked_at_issue(env):
    conn, pol = env
    p, a, res = _file(conn, pol)
    v = passport.view(conn, p.record.id, pol)
    assert v.at_issue and v.gate == "ready" and v.reviewer == "B. Team Leader"
    c = checks(v)
    assert [x.id for x in v.checks] == ["citations", "evidence", "sources", "gate", "review", "integrity",
                                        "retention", "since"]
    items = c["evidence"].details["items"]
    assert [(i["claim_id"], i["weight"], i["reason"]) for i in items] == [(x.claim_id, x.weight, x.reason)
                                                                          for x in a.verdicts]
    assert c["gate"].status == "ok" and "Decision letter or assessment" in c["gate"].summary
    assert c["integrity"].status == "ok" and c["review"].status == "ok" and c["since"].status == "ok"


def test_stored_checks_are_tamper_evident(env):
    conn, pol = env
    p, _, _ = _file(conn, pol)
    row = conn.execute("SELECT payload FROM passport_checks WHERE record_id=?", (p.record.id,)).fetchone()
    data = json.loads(row["payload"])
    data["assessment"]["verdicts"][0]["weight"] = "contradicted"
    conn.execute("UPDATE passport_checks SET payload=? WHERE record_id=?", (json.dumps(data), p.record.id))
    c = checks(passport.view(conn, p.record.id, pol))
    assert c["integrity"].status == "problem" and "stored at issue" in c["integrity"].summary


def test_seed_passports_still_verify_and_say_summary_only(env):
    conn, pol = env
    assert passport.verify_chain(conn).ok
    seed = next(p for p in db.get_passports(conn) if p.business.tier == "T2")
    v = passport.view(conn, seed.record.id, pol)
    c = checks(v)
    assert not v.at_issue and c["integrity"].status == "ok"
    assert c["evidence"].status == "not_run" and c["sources"].status == "not_run"
    assert "not recorded" in c["sources"].summary


def test_since_filing_flips_when_a_source_is_superseded_and_a_model_is_recalled(env):
    conn, pol = env
    seed = next(p for p in db.get_passports(conn) if OLD_NOTICE in p.process.source_record_ids and p.business.tier != "T0")
    assert checks(passport.view(conn, seed.record.id, pol))["since"].status == "ok"
    recall.mark_superseded(conn, OLD_NOTICE, NEW_NOTICE, "reissued", by="IM")
    s = checks(passport.view(conn, seed.record.id, pol))["since"]
    assert s.status == "problem" and OLD_NOTICE in s.summary and NEW_NOTICE in s.summary
    recall.mark_model(conn, seed.agent.model_returned, "faulty", date(2026, 3, 1), "bad dates", "IM")
    s = checks(passport.view(conn, seed.record.id, pol))["since"]
    assert "marked faulty" in s.summary and s.details["recall"]


def test_disposed_passport_view_drops_the_detail(env):
    conn, pol = env
    rid = disposal.due_for_disposal(conn, as_of=date(2026, 10, 17))[0].record_id
    disposal.approve_disposal(conn, [rid], approved_by="IM", reason="r", as_of=date(2026, 10, 17))
    v = passport.view(conn, rid, pol)
    assert v.disposed and "since" not in checks(v) and "Disposed on" in checks(v)["retention"].summary
    assert checks(v)["integrity"].status == "ok"


def test_disposal_destroys_stored_checks(env):
    conn, pol = env
    p, _, _ = _file(conn, pol, user="C. Officer")
    conn.execute("UPDATE passports SET tier='T0' WHERE record_id=?", (p.record.id,))   # make it eligible
    assert conn.execute("SELECT COUNT(*) FROM passport_checks").fetchone()[0] == 1
    due = [i.record_id for i in disposal.due_for_disposal(conn, as_of=date(2027, 1, 30))]
    assert p.record.id in due                                          # filed 19 Oct 2026, T0: due 17 Jan 2027
    disposal.approve_disposal(conn, [p.record.id], approved_by="IM", reason="r", as_of=date(2027, 1, 30))
    assert conn.execute("SELECT COUNT(*) FROM passport_checks").fetchone()[0] == 0


def test_api_view(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "api.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    import api.main as main
    main = importlib.reload(main)
    client = TestClient(main.app)
    rid = db.get_passports(main.conn)[0].record.id
    r = client.get(f"/passport/{rid}/view")
    assert r.status_code == 200 and r.json()["record_id"] == rid and len(r.json()["checks"]) == 8
    assert client.get(f"/passport/{rid}").json()["record"]["id"] == rid
    assert client.get("/passport/REC-9999/1/view").status_code == 404
    main.conn.close()


def test_api_files_only_the_records_the_evidence_rests_on(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "api.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    import api.main as main
    main = importlib.reload(main)
    client = TestClient(main.app)
    chk = client.post("/check", json={"document_id": ELIG, "document_type": "case-note"}).json()
    relied = chk["relied_on"]
    assert "REC-2026/005110" in relied and "REC-2025/008800" not in relied     # wording-only, superseded match
    ev = {"id": "EVT-REL-API", "app_id": "agency-assistant", "user": "A. Caseworker",
          "created": "2026-10-19T12:00:00", "prompt": "p", "output": "o", "model_requested": "m",
          "model_returned": "m", "provider": "v", "decision_flag": True,
          "source_record_ids": ["REC-2025/008800", "REC-2026/004790"]}           # what a caller might claim
    review = {"reviewer": "B. Team Leader", "decision": "approved", "reviewed_at": "2026-10-19T13:00:00"}
    r = client.post("/passport", json={"event": ev, "assessment": chk["assessment"], "citations": chk["citations"],
                                       "document_type": "case-note", "review": review})
    assert r.status_code == 200, r.text
    assert r.json()["process"]["source_record_ids"] == relied
    plain = client.post("/passport", json={"event": {**ev, "id": "EVT-REL-PLAIN"}})   # no claims: sources kept
    assert plain.json()["process"]["source_record_ids"] == ["REC-2025/008800", "REC-2026/004790"]
    main.conn.close()

