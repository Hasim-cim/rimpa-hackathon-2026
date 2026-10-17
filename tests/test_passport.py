from datetime import datetime

import pytest

from recordcheck import db, passport
from recordcheck.models import AIEvent, ToolCall

RULES = passport.load_tier_rules()


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    c = db.open_db()
    yield c
    c.close()


def ev(app="agency-assistant", **kw) -> AIEvent:
    base = dict(id="EVT-TEST-1", app_id=app, user="A. Caseworker", created=datetime(2026, 10, 17, 9, 0),
                prompt="p", output="o", model_requested="m", model_returned="m", provider="x", function="Eligibility review")
    base.update(kw)
    return AIEvent(**base)


def test_classify_all_tiers():
    assert passport.classify(ev("policy-chat"), RULES) == "T0"
    assert passport.classify(ev("unknown-app"), RULES) == "T0"
    assert passport.classify(ev("agency-assistant"), RULES) == "T1"
    assert passport.classify(ev("policy-chat", exported_to_document="DOC-1"), RULES) == "T1"
    assert passport.classify(ev("policy-chat", decision_flag=True), RULES) == "T2"
    assert passport.classify(ev("drafting-helper", tool_calls=[ToolCall(name="x", side_effect=True)]), RULES) == "T3"
    assert passport.classify(ev("agency-assistant", tool_calls=[ToolCall(name="x")]), RULES) == "T1"


def test_reason_sentence():
    tier, why = passport.classify_with_reason(ev(decision_flag=True), RULES)
    assert tier == "T2"
    assert why.startswith("Default T1 for Agency assistant")
    assert "T2" in why


def test_build_extends_chain(conn):
    before = db.latest_passport_hash(conn)
    n = len(db.get_passports(conn))
    p = passport.build(ev(decision_flag=True), tier="T2", assessment=None, citations=[], review=None, conn=conn)
    assert p.business.tier == "T2"
    assert p.record.id == "REC-2026/005113"  # one past the highest seeded record id
    assert p.integrity.prev_hash == before
    assert p.paradata.use_register_id == "USE-agency-assistant"
    assert p.process.citation_summary == {"found": 0, "mismatch": 0, "not_found": 0, "not_checked": 0}
    assert len(db.get_passports(conn)) == n + 1
    assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='passport.issued'").fetchone()[0] == 1
    r = passport.verify_chain(conn)
    assert r.ok and r.checked == n + 1


def test_seed_chain_ok(conn):
    assert passport.verify_chain(conn).ok


def test_tamper_breaks_chain(conn):
    rid = db.get_passports(conn)[10].record.id
    row = conn.execute("SELECT payload FROM passports WHERE record_id=?", (rid,)).fetchone()
    conn.execute("UPDATE passports SET payload=? WHERE record_id=?",
                 (row["payload"].replace("Debt waiver", "Tampered").replace("Eligibility", "Tampered").replace("Policy", "Tampered")
                  .replace("Correspondence", "Tampered").replace("Case note", "Tampered"), rid))
    r = passport.verify_chain(conn)
    assert not r.ok and r.first_break == rid
