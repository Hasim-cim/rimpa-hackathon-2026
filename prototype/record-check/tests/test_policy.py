import pytest


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    # recordcheck/__init__ loads .env after conftest runs; make sure no test can reach the API
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


from recordcheck import db, evidence, passport, policy
from recordcheck.models import Citation, CitationResult, AIEvent
from datetime import datetime, timezone


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    return tmp_path


def test_presets_load():
    ps = policy.load_presets()
    assert [p.id for p in ps] == ["commonwealth-agency", "state-agency", "health-service", "local-council"]
    assert policy.get_preset("health-service").document_types[0].id == "clinical-note"
    with pytest.raises(KeyError):
        policy.get_preset("nope")


def test_from_preset_and_round_trip(env):
    pol = policy.from_preset(policy.get_preset("health-service"), "St Example Hospital", "IM")
    assert pol.version == "1" and pol.tier_rules.retention_days["T0"] == 90
    saved = policy.save(pol, "Pat")
    assert saved.version == "2" and saved.updated_by == "Pat"
    loaded = policy.load()
    assert loaded == saved
    assert policy.doc_type(loaded, "clinical-note").quality.min_supported_share == 0.8
    assert policy.doc_type(loaded, "zzz") is None


def test_load_creates_default_and_bumps_and_reset(env):
    assert not (env / "policy.json").exists()
    pol = policy.load()
    assert pol.sector == "commonwealth-agency" and pol.organisation == "Example Agency (prototype)"
    assert (env / "policy.json").exists()
    v = int(pol.version)
    assert int(policy.save(pol, "X").version) == v + 1
    policy.reset()
    assert not (env / "policy.json").exists()
    policy.reset()  # idempotent


def test_retention_override():
    pre = policy.get_preset("local-council").model_copy(update={"retention_days": {"T0": 30}})
    assert policy.from_preset(pre, "C", "IM").tier_rules.retention_days["T0"] == 30


def test_authoritative(env):
    pol = policy.load()
    conn = db.open_db()
    recs = {r.id: r for r in db.get_records(conn)}
    assert policy.authoritative(pol, recs["REC-2026/004811"])
    pol.authoritative_systems.remove("Payroll records system")
    assert not policy.authoritative(pol, recs["REC-2026/004811"])
    conn.close()


def test_suggest_off_without_key(env, monkeypatch):
    monkeypatch.setattr(policy.llm, "available", lambda: False)  # some test modules load .env; never hit the API
    assert policy.suggest("A regional hospital") is None


def test_suggest_never_raises(env, monkeypatch):
    monkeypatch.setattr(policy.llm, "available", lambda: True)

    def boom():
        raise RuntimeError("no network")
    monkeypatch.setattr(policy.llm, "_client", boom)
    assert policy.suggest("A regional hospital") is None


def test_evidence_respects_policy_systems(env):
    conn = db.open_db()
    doc = db.get_document(conn, "DOC-2026/0412-summary")
    cites = [CitationResult(citation=Citation(n=i, raw=f"[{i}]"), status=s) for i, s in
             [(1, "not_checked"), (2, "found"), (3, "mismatch"), (4, "not_found")]]
    base = {v.claim_id: v.weight for v in evidence.assess(doc, conn, cites).verdicts}
    assert base["c1"] == "supported"
    pol = policy.load()
    same = {v.claim_id: v.weight for v in evidence.assess(doc, conn, cites, policy=pol).verdicts}
    assert same == base
    pol.authoritative_systems.remove("Payroll records system")
    v = {v.claim_id: v for v in evidence.assess(doc, conn, cites, policy=pol).verdicts}
    assert v["c1"].weight == "weak"
    # DB untouched
    assert db.get_record(conn, "REC-2026/004811").authoritative is True
    conn.close()


def test_passport_records_type_and_gate(env):
    conn = db.open_db()
    ev = db.get_event(conn, db.get_documents(conn) and next(r[0] for r in conn.execute("SELECT id FROM ai_events LIMIT 1")))
    p = passport.build(ev, tier="T2", conn=conn, document_type="decision-letter", gate="attention")
    assert p.business.document_type == "decision-letter" and p.business.gate == "attention"
    assert db.get_passport(conn, p.record.id).business.gate == "attention"
    assert passport.verify_chain(conn).ok
    p2 = passport.build(ev, tier="T1", conn=conn)
    assert p2.business.gate is None and passport.verify_chain(conn).ok
    conn.close()
