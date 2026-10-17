from datetime import date

import pytest

from recordcheck import db, disposal, passport, recall

AS_OF = date(2026, 10, 17)
N7 = "northstar-7-2026-03-01"


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    c = db.open_db()
    yield c
    c.close()


def test_due_list(conn):
    items = disposal.due_for_disposal(conn, as_of=AS_OF)
    assert len(items) == 6
    assert all(i.tier == "T0" and not i.on_hold for i in items)
    assert [i.due for i in items] == sorted(i.due for i in items)
    assert all(i.created.date() <= date(2026, 7, 19) for i in items)
    assert disposal.pending_count(conn, as_of=AS_OF) == 6
    assert not any(i.tier != "T0" for i in disposal.due_for_disposal(conn, as_of=date(2030, 1, 1)))


def test_hold_and_approve(conn):
    recall.mark_model(conn, N7, "faulty", date(2026, 3, 1), "test", "im")
    items = disposal.due_for_disposal(conn, as_of=AS_OF)
    held = [i for i in items if i.on_hold]
    assert len(held) == 3 and all(i.model_returned == N7 and i.hold_reason for i in held)
    assert disposal.pending_count(conn, as_of=AS_OF) == 3

    ids = [i.record_id for i in items]
    before = {r["record_id"]: r["hash"] for r in conn.execute("SELECT record_id, hash FROM passports")}
    entries = disposal.approve_disposal(conn, ids, approved_by="IM", reason="past retention", as_of=AS_OF)
    assert len(entries) == 3
    assert len(disposal.register(conn)) == 3
    assert not {e.record_id for e in entries} & {i.record_id for i in held}

    rep = passport.verify_chain(conn)
    assert rep.ok and "3 disposed" in rep.detail

    rid = entries[0].record_id
    p = db.get_passport(conn, rid)
    assert p.record.title == "[destroyed]" and p.process.prompt == "[destroyed]"
    assert p.integrity.hash == before[rid] == entries[0].hash_retained
    assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='disposal.approved'").fetchone()[0] == 3

    assert disposal.approve_disposal(conn, ids, approved_by="IM", reason="again", as_of=AS_OF) == []


def test_chain_still_detects_broken_link_after_disposal(conn):
    ids = [i.record_id for i in disposal.due_for_disposal(conn, as_of=AS_OF)]
    disposal.approve_disposal(conn, ids, approved_by="IM", reason="r", as_of=AS_OF)
    assert passport.verify_chain(conn).ok
    conn.execute("UPDATE passports SET hash='x' WHERE record_id=?", (ids[0],))
    assert not passport.verify_chain(conn).ok


def test_non_t0_never_approved(conn):
    t12 = [r["record_id"] for r in conn.execute("SELECT record_id FROM passports WHERE tier != 'T0'")]
    assert disposal.approve_disposal(conn, t12, approved_by="IM", reason="r", as_of=date(2030, 1, 1)) == []


def test_disposal_scrubs_the_underlying_ai_event(tmp_path, monkeypatch):
    """Destroying the passport alone is not disposal: the prompt and output in ai_events go too."""
    import datetime as dt
    from recordcheck import db, disposal
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "s.sqlite"))
    conn = db.open_db()
    due = disposal.due_for_disposal(conn, as_of=dt.date(2026, 10, 17))
    rid = due[0].record_id
    event_id = db.get_passport(conn, rid).event_id
    assert db.get_event(conn, event_id).prompt != "[destroyed]"
    disposal.approve_disposal(conn, [rid], approved_by="im", reason="test", as_of=dt.date(2026, 10, 17))
    ev = db.get_event(conn, event_id)
    assert ev.prompt == "[destroyed]" and ev.output == "[destroyed]" and ev.user == "[destroyed]"
    assert ev.model_returned  # kept: the register still needs to know which model it was
