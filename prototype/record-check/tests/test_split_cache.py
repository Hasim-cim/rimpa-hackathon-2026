"""Recorded AI split (Hasim: 'record the AI split'): the demo replays the same split, so its numbers are stable.
Offline: the model is faked."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from recordcheck import db, evidence, llm
from recordcheck.models import Document

BODY = "The applicant lives alone. The weekly rent is $380."


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "s.sqlite"))
    c = db.open_db()
    yield c
    c.close()


def fake(monkeypatch, claims, returned="claude-fake-1"):
    calls = []

    def split(text):
        calls.append(text)
        llm.LAST_MODEL_RETURNED = returned
        return claims
    monkeypatch.setattr(llm, "split_claims", split)
    return calls


def doc(body=BODY):
    return Document(id="D", title="t", case_id="2026/0412", body=body)


def test_first_split_is_recorded_and_the_second_replays_it(conn, monkeypatch):
    calls = fake(monkeypatch, ["The applicant lives alone.", "The weekly rent is $380."])
    a = evidence.assess(doc(), conn, use_llm=True)
    assert a.method == "llm:claude-fake-1" and len(calls) == 1
    rec = evidence.recorded_split(conn, BODY)
    assert rec["claims"] == ["The applicant lives alone.", "The weekly rent is $380."] and rec["model_returned"] == "claude-fake-1"
    def boom(t):
        raise AssertionError("a recorded split must not call the model")
    monkeypatch.setattr(llm, "split_claims", boom)
    b = evidence.assess(doc(), conn, use_llm=True)
    assert b.method.startswith("llm:claude-fake-1 (recorded ") and b.method.endswith(" UTC)")
    assert [c.text for c in b.claims] == [c.text for c in a.claims]
    assert [v.weight for v in b.verdicts] == [v.weight for v in a.verdicts]


def test_a_different_text_is_a_miss(conn, monkeypatch):
    calls = fake(monkeypatch, ["The applicant lives alone."])
    evidence.assess(doc("The applicant lives alone."), conn, use_llm=True)
    evidence.assess(doc("The applicant does not live alone."), conn, use_llm=True)   # model output not verbatim: no
    assert len(calls) == 2


def test_a_rejected_model_split_is_not_recorded(conn, monkeypatch):
    fake(monkeypatch, ["Something the document never said."])                    # fails the verbatim check
    a = evidence.assess(doc(), conn, use_llm=True)
    assert a.method == "sentence-split" and evidence.recorded_split(conn, BODY) is None


def test_without_ai_the_recording_is_not_used(conn, monkeypatch):
    fake(monkeypatch, ["The applicant lives alone.", "The weekly rent is $380."])
    evidence.assess(doc(), conn, use_llm=True)
    assert evidence.assess(doc(), conn, use_llm=False).method == "sentence-split"   # app mode: plain sentences


def test_stage_record_ai_records_only_documents_without_seed_claims(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("stage", Path(__file__).resolve().parent.parent / "scripts" / "stage.py")
    stage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "split_claims", lambda t: [s for s in evidence._regex_split(t)])   # verbatim sentences
    monkeypatch.setattr(db, "_shared", None)
    stage.reset(db_file=tmp_path / "st.sqlite", policy_file=tmp_path / "st.json")
    lines = stage.record_ai(db_file=tmp_path / "st.sqlite", policy_file=tmp_path / "st.json")
    assert any(l.startswith("DOC-2026/0587-eligibility: ") and "llm:" in l for l in lines)
    assert any(l.startswith("DOC-2026/0412-summary: seed claims") for l in lines)
