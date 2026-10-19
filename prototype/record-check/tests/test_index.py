"""Records index (filters and search): one row per passport, statuses from the same rules as /view and /dashboard."""
from __future__ import annotations

import importlib
from datetime import date

import pytest

from recordcheck import dashboard, db, disposal, index, passport, policy as policymod, recall, view


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "i.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "p.json"))
    c = db.open_db()
    yield c, policymod.load()
    c.close()


def test_one_row_per_passport_newest_first_with_case_ids(env):
    conn, pol = env
    rows = index.rows(conn, pol)
    ps = db.get_passports(conn)
    assert [r.record_id for r in rows] == [p.record.id for p in ps][::-1]
    assert sum(r.status == "log_only" for r in rows) == sum(p.business.tier == "T0" for p in ps)
    assert all(r.case_id for r in rows if r.status != "log_only" and r.function != "Policy Q&A")
    assert {r.status for r in rows} <= {"filed", "needs_person", "changed", "disposed", "log_only"}
    assert all(r.status_label == "Filed" for r in rows if r.status == "filed")
    assert not any(r.status_label == "Ready to file" for r in rows)
    import re
    for p in ps:   # the case the prompt names wins over the case of the (shared, invented) source records
        m = re.search(r"case (\d{4}/\d{4})", p.process.prompt)
        if m and not p.record.final_document:
            assert next(r for r in rows if r.record_id == p.record.id).case_id == m.group(1), p.record.id


def test_statuses_agree_with_view_and_dashboard(env):
    conn, pol = env
    recall.mark_superseded(conn, "REC-2026/004790", "REC-2026/004912", "reissued", by="IM")
    rid = disposal.due_for_disposal(conn, as_of=date(2026, 10, 17))[0].record_id
    disposal.approve_disposal(conn, [rid], approved_by="IM", reason="r", as_of=date(2026, 10, 17))
    rows = {r.record_id: r for r in index.rows(conn, pol)}
    assert rows[rid].status == "disposed" and rows[rid].status_label == "Disposed"
    queued = recall.open_queue_ids(conn)
    for p in db.get_passports(conn):
        r = rows[p.record.id]
        if r.status == "disposed":
            continue
        since = {c.id: c for c in passport.view(conn, p.record.id, pol).checks}["since"]
        assert r.changed_since == (since.status == "problem"), p.record.id
        if r.status == "needs_person":
            assert dashboard._attention(p, queued)
    changed = [r for r in rows.values() if r.status == "changed"]
    assert changed and all(r.status_label == "Changed since filing" for r in changed)


def test_api_records_index(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "a.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "p.json"))
    import api.main as main
    main = importlib.reload(main)
    j = TestClient(main.app).get("/records/index").json()
    assert len(j) == 40 and {"record_id", "case_id", "status", "status_label", "changed_since"} <= set(j[0])
    main.conn.close()
