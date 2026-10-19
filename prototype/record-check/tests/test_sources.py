"""Source health (ROT and drafts) and recall by source record. Offline, seed data only."""

from datetime import date

import pytest

from recordcheck import db, evidence, policy as policymod, recall, sources
from recordcheck.models import Claim, Document

OLD_NOTICE, NEW_NOTICE = "REC-2026/004790", "REC-2026/004912"


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    c = db.open_db()
    yield c
    c.close()


def _verdict(conn, text: str, case_id: str | None = None):
    doc = Document(id="T", title="t", case_id=case_id, body="",
                   claims=[Claim(id="c1", text=text, author="ai", position=1)])
    return evidence.assess(doc, conn, use_llm=False).verdicts[0]


# ---------- source health ----------

def test_health_labels_rot_and_drafts(conn):
    h = sources.health(conn)
    assert h.counts == {"redundant": 1, "obsolete": 2, "trivial": 2, "draft": 1}
    assert (h.total, h.eligible) == (20, 15)
    by = {i.record_id: i for i in h.items}
    assert by["POL-HARDSHIP-v3"].labels == ["obsolete"] and "POL-HARDSHIP-v4" in by["POL-HARDSHIP-v3"].notes[0]
    assert by["POL-HARDSHIP-v5-draft"].labels == ["draft"] and not by["POL-HARDSHIP-v5-draft"].eligible
    copy = by["SHARE-DELEG-COPY"]
    assert copy.labels == ["redundant", "trivial"] and copy.notes[0] == "same content as INS-DELEG-2025"
    assert by["INS-DELEG-2025"].labels == [] and by["INS-DELEG-2025"].eligible     # the original is not flagged
    flagged = [bool(i.labels or i.overdue) for i in h.items]
    assert flagged == sorted(flagged, reverse=True)                                # flagged records first


def test_health_follows_the_policy(conn):
    pol = policymod.load()
    pol.authoritative_systems.remove("Payroll records system")
    by = {i.record_id: i for i in sources.health(conn, pol).items}
    assert by["REC-2026/004811"].labels == ["trivial"] and not by["REC-2026/004811"].eligible


def test_health_copy_differing_only_in_case_and_spacing_is_redundant(conn):
    rec = db.get_record(conn, "POL-HARDSHIP-v4")
    copy = rec.model_copy(update={"id": "Z-COPY", "content": "  " + rec.content.upper().replace(" ", "   ")})
    conn.execute("INSERT INTO records(id,status,authoritative,created,payload) VALUES (?,?,?,?,?)",
                 (copy.id, copy.status, 1, copy.created.isoformat(), copy.model_dump_json()))
    by = {i.record_id: i for i in sources.health(conn).items}
    assert by["Z-COPY"].labels == ["redundant"] and by["Z-COPY"].notes == ["same content as POL-HARDSHIP-v4"]


# ---------- drafts in weighing ----------

def test_claim_resting_on_a_draft_is_weak(conn):
    v = _verdict(conn, "Applicants with a current medical certificate are treated as meeting the hardship test.")
    assert v.weight == "weak"
    assert "POL-HARDSHIP-v5-draft (a draft, not the approved version)" in v.reason


# ---------- recall by source record ----------

def test_superseding_a_source_weakens_claims_at_once(conn):
    text = "The debt of $4,860 was raised on 20 August 2026."
    assert _verdict(conn, text, "2026/0412").weight == "supported"
    recall.mark_superseded(conn, OLD_NOTICE, NEW_NOTICE, "Amount recalculated", "I. Manager")
    v = _verdict(conn, text, "2026/0412")
    # G1: the reissued notice is current and holds the corrected amount, so the old figure is now contradicted
    assert v.weight == "contradicted" and f"{NEW_NOTICE} records debt_amount = 3,890" in v.reason
    assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='record.marked_superseded' AND actor='I. Manager'"
                        ).fetchone()[0] == 1


def test_recall_by_record_lists_outputs_that_relied_on_it(conn):
    r = recall.recall_by_record(conn, OLD_NOTICE)
    assert r.counts == {"T0": 0, "T1": 9, "T2": 4, "T3": 0}
    assert [i.tier for i in r.items[:4]] == ["T2"] * 4
    for p in (db.get_passport(conn, i.record_id) for i in r.items):
        assert OLD_NOTICE in p.process.source_record_ids
    assert recall.queue_for_review(conn, [i.record_id for i in r.items if i.tier == "T2"], "I. Manager",
                                   f"{OLD_NOTICE} superseded") == 4
    assert sum(i.queued for i in recall.recall_by_record(conn, OLD_NOTICE).items) == 4


def test_recall_by_record_for_an_unused_record_is_empty(conn):
    r = recall.recall_by_record(conn, "POL-HARDSHIP-v3")
    assert r.items == [] and sum(r.counts.values()) == 0


def test_mark_superseded_refusals(conn):
    with pytest.raises(KeyError):
        recall.mark_superseded(conn, "NO-SUCH", None, "r", "I. Manager")
    with pytest.raises(KeyError):
        recall.recall_by_record(conn, "NO-SUCH")
    with pytest.raises(ValueError):
        recall.mark_superseded(conn, OLD_NOTICE, None, "r", "  ")
    with pytest.raises(ValueError):
        recall.mark_superseded(conn, OLD_NOTICE, "NO-SUCH", "r", "I. Manager")
    with pytest.raises(ValueError):
        recall.mark_superseded(conn, OLD_NOTICE, OLD_NOTICE, "r", "I. Manager")
    assert db.get_record(conn, OLD_NOTICE).status == "current"       # nothing changed


# ---------- intended use (S1) ----------

WG = "POL-HARDSHIP-WG-2026"
PROPOSAL = ("Repayment plans running longer than five years attract an automatic partial waiver, "
            "capped at one third of the outstanding balance.")


@pytest.fixture
def pol(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    return policymod.load()


def _typed(conn, pol, text, document_type):
    doc = Document(id="T", title="t", case_id="2026/0412", body="",
                   claims=[Claim(id="c1", text=text, author="ai", position=1)])
    return evidence.assess(doc, conn, use_llm=False, policy=pol, document_type=document_type).verdicts[0]


def test_record_outside_its_intended_use_is_not_evidence(conn, pol):
    v = _typed(conn, pol, PROPOSAL, "decision-letter")
    assert v.weight == "weak" and WG in v.reason
    assert "intended use excludes Decision letter or assessment" in v.reason and "not policy" in v.reason
    assert _typed(conn, pol, PROPOSAL, "briefing").weight == "supported"


def test_without_a_document_type_intended_use_changes_nothing(conn, pol):
    assert _typed(conn, pol, PROPOSAL, None).weight == "supported"
    assert _verdict(conn, PROPOSAL, "2026/0412").weight == "supported"


def test_seed_documents_are_unchanged_by_the_intended_use_record(conn, pol):
    """The discussion paper links to no existing seed claim, so the demo gates do not move."""
    for d in db.get_documents(conn):
        for t in pol.document_types:
            a = evidence.assess(d, conn, use_llm=False, policy=pol, document_type=t.id)
            assert all(l.record_id != WG for v in a.verdicts for l in v.links), (d.id, t.id)


def test_health_shows_intended_use_without_a_rot_flag(conn):
    i = next(i for i in sources.health(conn).items if i.record_id == WG)
    assert i.labels == [] and i.eligible and "not policy" in i.purpose and i.not_for == ["decision-letter"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    import importlib
    from fastapi.testclient import TestClient
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "api.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    import api.main as main
    main = importlib.reload(main)
    yield TestClient(main.app)
    main.conn.close()


def test_api_check_and_passport_agree_on_intended_use(client):
    body = {"title": "t", "body": PROPOSAL, "case_id": "2026/0412"}
    letter = client.post("/check", json={**body, "document_type": "decision-letter"}).json()
    brief = client.post("/check", json={**body, "document_type": "briefing"}).json()
    assert letter["assessment"]["verdicts"][0]["weight"] == "weak"
    assert brief["assessment"]["verdicts"][0]["weight"] == "supported"
    ev = {"id": "EVT-S1", "app_id": "agency-assistant", "user": "u", "created": "2026-10-19T12:00:00", "prompt": "p",
          "output": "o", "model_requested": "m", "model_returned": "m", "provider": "v"}
    r = client.post("/passport", json={"event": ev, "assessment": brief["assessment"], "document_type": "briefing"})
    assert r.status_code == 200 and r.json()["process"]["evidence_summary"]["supported"] == 1
    r = client.post("/passport", json={"event": {**ev, "id": "EVT-S1b"}, "assessment": brief["assessment"],
                                       "document_type": "decision-letter"})   # same claims, re-weighed for this type
    assert r.status_code == 409 or r.json()["process"]["evidence_summary"]["weak"] == 1



# ---------- reliability (B2) ----------

def test_reliability_on_the_seed_and_after_a_source_is_superseded(conn):
    r = sources.reliability(conn)
    assert (r.retained, r.with_sources, r.sources_ok, r.share, r.drag) == (29, 29, 29, 1.0, [])
    assert (r.claim_checked, r.claim_supported) == (0, 0)
    recall.mark_superseded(conn, OLD_NOTICE, NEW_NOTICE, "reissued", by="IM")
    r = sources.reliability(conn)
    assert (r.sources_ok, r.with_sources) == (16, 29)
    (d,) = r.drag
    assert (d.record_id, d.outputs, d.labels) == (OLD_NOTICE, 13, ["obsolete"]) and NEW_NOTICE in d.why


def test_reliability_counts_claim_checks_and_skips_t0_and_disposed(conn):
    from recordcheck import disposal, passport
    from recordcheck.models import AIEvent, Assessment, Verdict
    from datetime import datetime
    before = sources.reliability(conn)
    ev = AIEvent(id="EVT-REL", app_id="agency-assistant", user="u", created=datetime(2026, 10, 19, 9), prompt="p",
                 output="o", model_requested="m", model_returned="m", provider="x", decision_flag=True,
                 source_record_ids=["NO-SUCH-RECORD"])
    a = Assessment(document_id="D", claims=[], assessed_at=datetime(2026, 10, 19, 9), method="seed",
                   verdicts=[Verdict(claim_id="c1", weight="supported", reason="r"),
                             Verdict(claim_id="c2", weight="weak", reason="r")])
    passport.build(ev, tier="T2", assessment=a, conn=conn)
    r = sources.reliability(conn)
    assert (r.retained, r.claim_checked, r.claim_supported) == (before.retained + 1, 1, 0)
    assert any(d.record_id == "NO-SUCH-RECORD" and "not found" in d.why for d in r.drag)
    due = disposal.due_for_disposal(conn, as_of=date(2026, 10, 17))
    disposal.approve_disposal(conn, [due[0].record_id], approved_by="IM", reason="r", as_of=date(2026, 10, 17))
    assert sources.reliability(conn).retained == r.retained          # T0 disposals never counted


def test_api_reliability(client):
    r = client.get("/sources/reliability")
    assert r.status_code == 200 and r.json()["share"] == 1.0


# ---------- review date (G3) ----------

FILE_NOTE = "REC-2026/004809"


def test_overdue_record_is_flagged_but_still_counts(conn):
    h = sources.health(conn, as_of=date(2026, 10, 19))
    i = next(i for i in h.items if i.record_id == FILE_NOTE)
    assert i.overdue and i.eligible and i.labels == [] and "overdue for review since 2026-09-30" in i.notes
    assert h.overdue == 1 and h.counts == {"redundant": 1, "obsolete": 2, "trivial": 2, "draft": 1}
    assert not next(i for i in sources.health(conn, as_of=date(2026, 9, 30)).items if i.record_id == FILE_NOTE).overdue


def test_overdue_changes_no_verdict_and_shows_in_reliability(conn):
    r = sources.reliability(conn, as_of=date(2026, 10, 19))
    assert r.share == 1.0 and r.drag == []                             # still counts as evidence
    (o,) = r.overdue
    assert (o.record_id, o.outputs) == (FILE_NOTE, 10) and "2026-09-30" in o.why
    assert sources.reliability(conn, as_of=date(2026, 9, 1)).overdue == []



def test_g1_pairs_each_amount_with_its_own_field_in_a_two_amount_sentence(conn):
    """The deployer's smoke test (19 Oct): '$4,860' was compared with rent_weekly because the sentence also says rent."""
    text = "Weekly rent of $380 leaves limited capacity to repay the $4,860 debt."
    assert _verdict(conn, text, "2026/0412").weight == "supported"                 # before: both amounts on file
    recall.mark_superseded(conn, OLD_NOTICE, NEW_NOTICE, "Amount recalculated", "I. Manager")
    v = _verdict(conn, text, "2026/0412")
    assert v.weight == "contradicted"
    assert v.reason == f"The claim says $4,860, but {NEW_NOTICE} records debt_amount = 3,890."   # the debt field, not rent
    assert "rent_weekly" not in v.reason
