"""Postgres path (DATABASE_URL). Opt-in: skipped unless RECORDCHECK_TEST_DATABASE_URL points at a database the tests
may wipe. The normal suite stays on SQLite, offline and keyless.

    RECORDCHECK_TEST_DATABASE_URL=postgresql://... uv run pytest -q tests/test_postgres.py
"""
from __future__ import annotations

import importlib
import os
import threading
from datetime import date, datetime

import pytest

from recordcheck import db, disposal, passport, policy
from recordcheck.models import AIEvent

URL = os.environ.get("RECORDCHECK_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="set RECORDCHECK_TEST_DATABASE_URL to run the Postgres tests")

TABLES = ("records", "documents", "ai_events", "passports", "model_registry", "review_queue", "citation_cache",
          "disposal_register", "audit_log", "policy", "passport_checks")


@pytest.fixture
def pg(monkeypatch, tmp_path):
    import psycopg
    with psycopg.connect(URL, autocommit=True) as c:
        for t in TABLES:
            c.execute(f"DROP TABLE IF EXISTS {t}")
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))  # must stay unwritten
    monkeypatch.setattr(db, "_shared", None)
    yield
    if db._shared is not None:
        db._shared.close()


def ev(i: int, **kw) -> AIEvent:
    base = dict(id=f"EVT-PG-{i}", app_id="agency-assistant", user="A. Caseworker", created=datetime(2026, 10, 19, 9),
                prompt="p", output=f"o{i}", model_requested="m", model_returned="m", provider="x")
    return AIEvent(**{**base, **kw})


def test_fresh_database_self_seeds_once(pg):
    a = db.open_db()
    b = db.open_db()   # second instance on a seeded database: no reseed
    assert db.is_postgres(a)
    assert a.execute("SELECT COUNT(*) FROM passports").fetchone()[0] == 40
    assert b.execute("SELECT COUNT(*) FROM audit_log WHERE action='seed'").fetchone()[0] == 1
    r = passport.verify_chain(b)
    assert r.ok and r.checked == 40
    a.close(), b.close()


def test_a_passport_written_on_one_connection_is_read_on_another(pg):
    a, b = db.open_db(), db.open_db()
    p = passport.build(ev(1), tier="T1", conn=a)
    got = db.get_passport(b, p.record.id)
    assert got is not None and got.integrity.hash == p.integrity.hash
    assert passport.verify_chain(b).ok
    a.close(), b.close()


def test_concurrent_writers_keep_one_chain(pg):
    db.open_db().close()
    errors: list[Exception] = []

    def writer(k: int) -> None:
        c = db.open_db()
        try:
            for j in range(5):
                passport.build(ev(k * 100 + j), tier="T1", conn=c)
        except Exception as e:  # noqa: BLE001  (surface in the main thread)
            errors.append(e)
        finally:
            c.close()

    threads = [threading.Thread(target=writer, args=(k,)) for k in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    c = db.open_db()
    r = passport.verify_chain(c)
    assert r.ok and r.checked == 60, r
    assert c.execute("SELECT COUNT(DISTINCT seq) FROM passports").fetchone()[0] == 60
    c.close()


def test_refused_build_releases_the_chain_lock(pg):
    a, b = db.open_db(), db.open_db()
    first = passport.build(ev(1), tier="T1", conn=a)
    with pytest.raises(passport.DuplicateRecord):
        passport.build(ev(2), tier="T1", conn=a, record_id=first.record.id)
    passport.build(ev(3), tier="T1", conn=b)   # would hang if a still held the advisory lock
    assert passport.verify_chain(b).ok
    a.close(), b.close()


def test_policy_lives_in_the_database(pg):
    pol = policy.load()                         # first load seeds the default into the table
    default_systems = list(pol.authoritative_systems)
    pol.authoritative_systems = pol.authoritative_systems[:1]
    saved = policy.save(pol, by="IM", conn=db.open_db())
    db._shared.close()
    db._shared = None                           # a new instance sees the saved policy
    again = policy.load()
    assert again.version == saved.version and again.authoritative_systems == saved.authoritative_systems
    assert not policy.policy_path().exists()
    policy.reset()
    assert policy.load().authoritative_systems == default_systems   # back to the preset


def test_disposal_and_chain_on_postgres(pg):
    c = db.open_db()
    rid = disposal.due_for_disposal(c, as_of=date(2026, 10, 17))[0].record_id
    assert disposal.approve_disposal(c, [rid], approved_by="IM", reason="r", as_of=date(2026, 10, 17))
    assert [e.record_id for e in disposal.register(c)] == [rid]
    assert passport.verify_chain(c).ok
    c.close()


def test_reconnects_after_the_server_drops_an_idle_connection(pg):
    c = db.open_db()
    c._c.close()                                # what Neon does to an idle connection
    assert c.execute("SELECT COUNT(*) FROM records").fetchone()[0] > 0
    c.close()


def test_api_write_then_read_on_postgres(pg):
    from fastapi.testclient import TestClient
    import api.main as main
    main = importlib.reload(main)
    client = TestClient(main.app)
    e = {"id": "EVT-PG-API", "app_id": "agency-assistant", "user": "u", "created": "2026-10-19T12:00:00",
         "prompt": "p", "output": "o", "model_requested": "m", "model_returned": "m", "provider": "v"}
    r = client.post("/passport", json={"event": e})
    assert r.status_code == 200, r.text
    other = db.open_db()                        # another instance reads it back
    assert db.get_passport(other, r.json()["record"]["id"]) is not None
    assert client.get("/chain/verify").json()["ok"] is True
    other.close()
    main.conn.close()


def test_a_read_between_requests_leaves_no_open_transaction(pg):
    from psycopg.pq import TransactionStatus
    c = db.open_db()
    db.get_records(c)
    assert c._c.info.transaction_status == TransactionStatus.IDLE
    db.lock(c, db.CHAIN_LOCK)                   # inside a write, reads stay in the transaction
    db.latest_passport_hash(c)
    assert c._c.info.transaction_status == TransactionStatus.INTRANS
    c.rollback()
    c.close()


def test_stage_reset_on_postgres(pg):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("stage", Path(__file__).resolve().parent.parent / "scripts" / "stage.py")
    stage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage)
    c = db.open_db()
    passport.build(ev(9), tier="T1", conn=c)
    pol = policy.load()
    policy.save(pol, by="IM", conn=c)
    c.close()
    msg = stage.reset(database_url=URL)
    assert "chain ok (40)" in msg
    os.environ["DATABASE_URL"] = URL
    db._shared = None
    c = db.open_db()
    assert c.execute("SELECT COUNT(*) FROM passports").fetchone()[0] == 40
    assert policy.load().version == "2"
    c.close()
