import pytest


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    # recordcheck/__init__ loads .env after conftest runs; make sure no test can reach the API
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


from recordcheck import db, evidence, gate, policy
from recordcheck.citations import check_document
from recordcheck.models import DocumentType, QualityBar, Review
from datetime import datetime, timezone


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    conn = db.open_db()
    pol = policy.load()

    def run(doc_id, type_id, review=None, tier=None, dtype=None):
        doc = db.get_document(conn, doc_id)
        cites = check_document(doc.references, online=False, conn=conn)
        a = evidence.assess(doc, conn, cites, policy=pol)
        dt = dtype or policy.doc_type(pol, type_id)
        return gate.evaluate(a, cites, review, dt, tier or dt.default_tier)

    yield run
    conn.close()


def text(r):
    return " | ".join(x.text for x in r.reasons)


def test_hardship_decision_letter_blocked(ctx):
    r = ctx("DOC-2026/0412-summary", "decision-letter")
    assert r.status == "blocked"
    assert r.reasons[0].status == "blocked"
    t = text(r)
    assert "2 unsupported claims; this document type allows 0" in t
    assert "1 contradicted claim;" in t
    assert "[4]" in t
    assert any("named reviewer" in x.text for x in r.reasons)
    assert r.counts["unsupported"] == 2 and r.counts["not_found"] == 1


def test_eligibility_case_note_ready(ctx):
    r = ctx("DOC-2026/0587-eligibility", "case-note")
    assert r.status == "ready" and r.reasons[0].status == "ready"
    assert "Case note" in r.reasons[0].text


def test_briefing_blocked_on_citations(ctx):
    r = ctx("DOC-2026/briefing-waivers", "briefing")
    assert r.status == "blocked"
    assert "[2]" in text(r) and "[4]" in text(r)


def test_agent_note_case_note_ready_and_strict_blocked(ctx):
    assert ctx("DOC-2026/0412-agent-note", "case-note").status == "ready"
    strict = DocumentType(id="strict", name="Strict", checks=["evidence"], quality=QualityBar(max_unsupported=0, require_reviewer=False))
    r = ctx("DOC-2026/0412-agent-note", "strict", dtype=strict)
    assert r.status == "blocked" and "allows 0" in text(r)


def test_reviewer_rule(ctx):
    dt = DocumentType(id="x", name="X", default_tier="T2", checks=["evidence"],
                      quality=QualityBar(max_unsupported=9, max_contradicted=9, require_reviewer=True))
    r = ctx("DOC-2026/0412-agent-note", "x", dtype=dt, tier="T2")
    assert r.status == "attention" and r.reasons[0].text == "Needs a named reviewer before filing."
    ok = Review(reviewer="R", decision="approved", reviewed_at=datetime.now(timezone.utc))
    assert ctx("DOC-2026/0412-agent-note", "x", dtype=dt, tier="T2", review=ok).status == "ready"
    rej = ok.model_copy(update={"decision": "rejected"})
    assert ctx("DOC-2026/0412-agent-note", "x", dtype=dt, tier="T2", review=rej).status == "blocked"
    assert ctx("DOC-2026/0412-agent-note", "x", dtype=dt, tier="T1").status == "ready"


def test_summary_line(ctx):
    r = ctx("DOC-2026/0587-eligibility", "case-note")
    assert gate.summary_line(r).startswith("Ready to file: ")


def test_build_refuses_a_blocked_gate(tmp_path, monkeypatch):
    """The gate is enforced in the engine, not only in the UI."""
    import datetime as dt
    import pytest
    from recordcheck import db, passport
    from recordcheck.models import AIEvent
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "g.sqlite"))
    conn = db.open_db()
    ev = AIEvent(id="EVT-x", app_id="agency-assistant", user="u", created=dt.datetime(2026, 10, 17, 12, 0),
                 prompt="p", output="o", model_requested="m", model_returned="m", provider="v", decision_flag=True)
    with pytest.raises(passport.GateBlocked):
        passport.build(ev, tier="T2", conn=conn, document_type="decision-letter", gate="blocked")
    assert db.get_passport(conn, "REC-2026/005113") is None


def test_passport_records_the_policy_it_was_judged_against(tmp_path, monkeypatch):
    import datetime as dt
    from recordcheck import db, passport, policy
    from recordcheck.models import AIEvent
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "g.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    conn = db.open_db()
    pol = policy.load()
    ev = AIEvent(id="EVT-y", app_id="agency-assistant", user="u", created=dt.datetime(2026, 10, 17, 12, 0),
                 prompt="p", output="o", model_requested="m", model_returned="m", provider="v")
    from recordcheck.models import Assessment, Claim, Verdict
    ok = Assessment(document_id="D", claims=[Claim(id="c1", text="t", author="ai", position=1)],
                    verdicts=[Verdict(claim_id="c1", weight="supported", reason="r")],
                    assessed_at=dt.datetime(2026, 10, 17, 12, 0), method="seed")
    p = passport.build(ev, tier="T1", conn=conn, assessment=ok, document_type="case-note", policy=pol)
    assert p.paradata.policy_version.startswith("policy v") and p.paradata.policy_hash == passport.policy_hash(pol)
    # saving an unchanged bar keeps the same content hash; the save itself is audited
    saved = policy.save(pol, by="im", conn=conn)
    assert passport.policy_hash(saved) == p.paradata.policy_hash
    assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='policy.saved'").fetchone()[0] == 1
    assert passport.verify_chain(conn).ok
