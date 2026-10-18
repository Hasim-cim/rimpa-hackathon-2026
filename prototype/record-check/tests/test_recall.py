from datetime import date

import pytest

from recordcheck import db, recall

N7 = "northstar-7-2026-03-01"


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    c = db.open_db()
    yield c
    c.close()


def test_recall_counts_and_order(conn):
    r = recall.recall(conn, N7)
    assert r.counts == {"T0": 0, "T1": 11, "T2": 3, "T3": 0}
    assert len(r.items) == 14
    assert [i.tier for i in r.items[:3]] == ["T2"] * 3
    assert all(i.tier != "T0" for i in r.items)
    assert not any(i.queued for i in r.items)
    for tier in ("T2", "T1"):
        ds = [i.created for i in r.items if i.tier == tier]
        assert ds == sorted(ds, reverse=True)


def test_mark_model_audited(conn):
    recall.mark_model(conn, N7, "faulty", date(2026, 10, 1), "Systematic misreading of income", "M. Manager")
    e = recall.recall(conn, N7).entry
    assert e.status == "faulty" and e.marked_by == "M. Manager" and e.effective_from == date(2026, 10, 1)
    assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='model.marked_faulty'").fetchone()[0] == 1


def test_queue_for_review(conn):
    t2 = [i.record_id for i in recall.recall(conn, N7).items if i.tier == "T2"]
    assert recall.queue_for_review(conn, t2, "M. Manager", "Model faulty") == 3
    assert recall.queue_for_review(conn, t2, "M. Manager", "Model faulty") == 0
    assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='review.queued'").fetchone()[0] == 3
    r = recall.recall(conn, N7)
    assert sum(i.queued for i in r.items) == 3
