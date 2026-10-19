"""Stage database (S2): the reset touches only the stage target and brings the demo back to the seed."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from recordcheck import db, passport
from recordcheck.models import AIEvent

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("stage", ROOT / "scripts" / "stage.py")
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


@pytest.fixture
def files(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for k in ("RECORDCHECK_DB", "RECORDCHECK_POLICY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(db, "_shared", None)
    return tmp_path / "stage.sqlite", tmp_path / "stage-policy.json", tmp_path / "shared.sqlite"


def test_reset_brings_the_stage_back_to_the_seed_and_leaves_the_shared_db(files, monkeypatch):
    stage_db, stage_pol, shared_db = files
    shared = db.open_db(shared_db)
    ev = AIEvent(id="EVT-SHARED", app_id="agency-assistant", user="u", created="2026-10-19T09:00:00", prompt="p",
                 output="o", model_requested="m", model_returned="m", provider="x")
    passport.build(ev, tier="T1", conn=shared)
    shared.close()

    stage.reset(db_file=stage_db, policy_file=stage_pol)
    c = db.open_db(stage_db)
    passport.build(ev.model_copy(update={"id": "EVT-STAGE"}), tier="T1", conn=c)   # a rehearsal writes
    assert c.execute("SELECT COUNT(*) FROM passports").fetchone()[0] == 41
    c.close()

    msg = stage.reset(db_file=stage_db, policy_file=stage_pol)
    assert "chain ok (40)" in msg and "policy v2" in msg
    c = db.open_db(stage_db)
    assert c.execute("SELECT COUNT(*) FROM passports").fetchone()[0] == 40
    assert c.execute("SELECT COUNT(*) FROM disposal_register").fetchone()[0] == 0
    c.close()
    assert stage_pol.exists()
    shared = db.open_db(shared_db)                 # the shared DB still has its own passport
    assert shared.execute("SELECT COUNT(*) FROM passports").fetchone()[0] == 41
    shared.close()


def test_reset_clears_disposals_and_review_queue(files):
    from datetime import date
    from recordcheck import disposal, recall
    stage_db, stage_pol, _ = files
    stage.reset(db_file=stage_db, policy_file=stage_pol)
    c = db.open_db(stage_db)
    rid = disposal.due_for_disposal(c, as_of=date(2026, 10, 17))[0].record_id
    disposal.approve_disposal(c, [rid], approved_by="IM", reason="r", as_of=date(2026, 10, 17))
    recall.queue_for_review(c, [rid], by="IM", reason="r")
    c.close()
    stage.reset(db_file=stage_db, policy_file=stage_pol)
    c = db.open_db(stage_db)
    assert not disposal.register(c) and passport.verify_chain(c).ok
    assert c.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0] == 0
    c.close()


def test_postgres_reset_needs_an_explicit_url_and_yes(files, capsys):
    assert stage.main(["reset", "--database-url", "postgresql://u:p@example.invalid/db"]) == 2
    assert "without --yes" in capsys.readouterr().err
