"""Connector contract (I1): the seed database is the first RecordSource and PassportSink. Offline."""
from __future__ import annotations

from datetime import datetime

import pytest

from recordcheck import connectors, db, passport
from recordcheck.models import AIEvent


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "c.sqlite"))
    c = db.open_db()
    yield c
    c.close()


def test_seed_db_is_a_record_source(conn):
    src = connectors.SeedDbSource(conn)
    assert isinstance(src, connectors.RecordSource)
    recs = src.list_records()
    assert len(recs) == len(db.get_records(conn)) > 0
    one = src.get_record(recs[0].id)
    assert one is not None and one.id == recs[0].id and one.status
    assert src.get_record("NO-SUCH-RECORD") is None


def test_seed_db_is_a_passport_sink_with_a_receipt_and_an_audit_entry(conn):
    sink = connectors.SeedDbSink(conn)
    assert isinstance(sink, connectors.PassportSink)
    ev = AIEvent(id="EVT-SINK", app_id="agency-assistant", user="u", created=datetime(2026, 10, 19, 9), prompt="p",
                 output="o", model_requested="m", model_returned="m", provider="x")
    p = passport.build(ev, tier="T1", conn=conn)
    r = sink.file(p)
    assert (r.record_id, r.system, r.location) == (p.record.id, "Record Check database", f"passports/{p.record.id}")
    assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='passport.filed_back' AND subject=?",
                        (p.record.id,)).fetchone()[0] == 1
    assert passport.verify_chain(conn).ok


def test_sink_refuses_a_passport_that_is_not_in_the_chain(conn):
    p = db.get_passports(conn)[0].model_copy(deep=True)
    p.record.id = "REC-2026/999999"
    with pytest.raises(KeyError):
        connectors.SeedDbSink(conn).file(p)
