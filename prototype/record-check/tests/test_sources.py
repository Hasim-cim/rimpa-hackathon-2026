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
    assert (h.total, h.eligible) == (19, 14)
    by = {i.record_id: i for i in h.items}
    assert by["POL-HARDSHIP-v3"].labels == ["obsolete"] and "POL-HARDSHIP-v4" in by["POL-HARDSHIP-v3"].notes[0]
    assert by["POL-HARDSHIP-v5-draft"].labels == ["draft"] and not by["POL-HARDSHIP-v5-draft"].eligible
    copy = by["SHARE-DELEG-COPY"]
    assert copy.labels == ["redundant", "trivial"] and copy.notes[0] == "same content as INS-DELEG-2025"
    assert by["INS-DELEG-2025"].labels == [] and by["INS-DELEG-2025"].eligible     # the original is not flagged
    flagged = [bool(i.labels) for i in h.items]
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
    assert v.weight == "weak" and f"{OLD_NOTICE} (superseded by {NEW_NOTICE})" in v.reason
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
