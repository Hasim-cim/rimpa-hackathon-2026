"""Console smoke test: drives app/streamlit_app.py through Streamlit's AppTest on a temp DB, offline.

A UI break (NameError on "Issue passport", a renamed widget, a tab that raises) fails pytest, not the stage demo.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from recordcheck import passport

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")
SUMMARY = "DOC-2026/0412-summary"
ELIGIBILITY = "DOC-2026/0587-eligibility"
IM_TABS = ["Setup", "Sources", "Recall", "Disposal", "Register"]


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "console.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    monkeypatch.setenv("RECORDCHECK_ONLINE", "false")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    st.cache_resource.clear()
    st.cache_data.clear()
    yield tmp_path / "console.sqlite"
    st.cache_resource.clear()
    st.cache_data.clear()


@pytest.fixture
def at(db_path):
    app = AppTest.from_file(APP, default_timeout=30)
    app.run()
    assert not app.exception
    return app


def button(at, prefix):
    for b in at.button:
        if b.label.startswith(prefix):
            return b
    raise AssertionError(f"no button starting {prefix!r}; have {[b.label for b in at.button]}")


def go(at, place):
    next(r for r in at.radio if r.label == "Go to").set_value(place).run()
    assert not at.exception


def start_check(at):
    button(at, "Check a document").click().run()
    assert not at.exception


def opened(at):
    return at.session_state["records_open"]


def form_button(at, label):
    return next(b for b in at.button if b.label == label)


def select(at, label, value):
    sb = next(s for s in at.selectbox if s.label == label)
    sb.select(value)


def rows(db_path, sql):
    c = sqlite3.connect(db_path)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def n_passports(db_path):
    return rows(db_path, "SELECT COUNT(*) FROM passports")[0][0]


def test_every_tab_loads(at):
    assert not at.exception and any("Check a document" == b.label for b in at.button)    # Records is the default
    go(at, "Information manager")
    assert [t.label for t in at.tabs] == IM_TABS


def test_stage_path_check_gate_and_issue_passport(at, db_path):
    before = n_passports(db_path)
    start_check(at)
    # Summary has unsupported/contradicted claims and fabricated references: the gate must block it.
    select(at, "Document", SUMMARY)
    at.run()
    button(at, "Run check").click().run()
    assert not at.exception
    assert button(at, "Issue passport").disabled, "hardship summary should be Blocked"
    assert any("Blocked by policy" in e.value for e in at.error)

    # Eligibility note is supported by authoritative records: gate opens once a reviewer is named.
    select(at, "Document", ELIGIBILITY)
    at.run()
    button(at, "Run check").click().run()
    assert not at.exception
    next(t for t in at.text_input if t.label == "Reviewer name").set_value("B. Team Leader")
    at.run()
    issue = button(at, "Issue passport")
    assert not issue.disabled, "eligibility note should be Ready with a reviewer"
    issue.click().run()
    assert not at.exception
    assert not [e for e in at.error if "Not filed" in e.value], [e.value for e in at.error]
    assert any("Passport issued" in s.value for s in at.success)

    assert n_passports(db_path) == before + 1
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    try:
        assert passport.verify_chain(c).ok
    finally:
        c.close()


def test_recall_mark_model_faulty_and_queue(at, db_path):
    go(at, "Information manager")
    select(at, "Model", "northstar-7-2026-03-01")
    select(at, "Status", "faulty")
    form_button(at, "Mark model").click().run()
    assert not at.exception
    assert rows(db_path, "SELECT status FROM model_registry WHERE model_id='northstar-7-2026-03-01'")[0][0] == "faulty"

    q = button(at, "Queue T2 records for re-review")
    assert not q.disabled, "seed data has T2 records from northstar-7"
    q.click().run()
    assert not at.exception
    assert any("Queued" in s.value for s in at.success)


def test_sources_mark_superseded_and_queue(at, db_path):
    go(at, "Information manager")
    form_button(at, "Mark superseded").click().run()  # defaults: debt notice superseded by its reissue
    assert not at.exception
    assert rows(db_path, "SELECT status FROM records WHERE id='REC-2026/004790'")[0][0] == "superseded"

    q = button(at, "Queue T2 outputs for re-review")
    assert not q.disabled, "outputs relied on the debt notice should include T2"
    q.click().run()
    assert not at.exception
    assert any("Queued" in s.value for s in at.success)


def test_disposal_approve(at, db_path):
    go(at, "Information manager")
    before = rows(db_path, "SELECT COUNT(*) FROM disposal_register")[0][0]
    b = button(at, "Approve destruction")
    assert not b.disabled, "seed T0 entries are past 90 days as of today"
    b.click().run()
    assert not at.exception
    assert rows(db_path, "SELECT COUNT(*) FROM disposal_register")[0][0] > before
    assert any("chain verified" in s.value for s in at.success)


def test_disposal_caption_and_match_steps(at):
    go(at, "Information manager")
    assert any("Retention here is a decision, not a timer" in c.value for c in at.caption)
    go(at, "Records")
    start_check(at)
    select(at, "Document", SUMMARY)
    at.run()
    button(at, "Run check").click().run()
    assert not at.exception
    assert any("No AI judge decides a weight" in c.value for c in at.caption)
    assert any(c.value.startswith("Matched by: Step 1") for c in at.caption)


def metric(at, label):
    return next(m for m in at.metric if m.label == label).value


def row(at, name):
    """The expander label of a check, e.g. ':green[**OK**] Evidence: 4 of 4 ...'."""
    return next(e.label for e in at.expander if f"] {name}:" in e.label)


def test_first_screen_on_a_fresh_db_explains_itself(at):
    # no passport has stored checks yet: open the newest, say it is an older record, fold its unrecorded checks
    assert any("File a document to see its passport" in i.value for i in at.info)
    assert any("Older record: summary only" in m.value for m in at.markdown)
    assert any(c.value.startswith("Not recorded for this older record:") for c in at.caption)
    assert not any("Not run" in e.label for e in at.expander)


def test_stage_path_v2_passport_first(at, db_path):
    """workstreams/05-demo-ops.md, 'Stage path v2', steps 1-7, clicked in order on a fresh DB."""
    # 1. Records is the first place
    assert next(r for r in at.radio if r.label == "Go to").value == "Records"

    # 2. Check: hardship summary as a decision letter -> Blocked
    start_check(at)
    select(at, "Document", SUMMARY)
    at.run()
    select(at, "Document type", "decision-letter")
    at.run()
    button(at, "Run check").click().run()
    assert button(at, "Issue passport").disabled and any("Blocked by policy" in e.value for e in at.error)

    # 3. Check: eligibility note as a case note, reviewer named -> Issue passport -> lands on its passport
    select(at, "Document", ELIGIBILITY)
    at.run()
    select(at, "Document type", "case-note")
    at.run()
    button(at, "Run check").click().run()
    next(t for t in at.text_input if t.label == "Reviewer name").set_value("B. Team Leader")
    at.run()
    button(at, "Issue passport").click().run()
    assert not at.exception
    new_id = rows(db_path, "SELECT record_id FROM passports ORDER BY seq DESC LIMIT 1")[0][0]
    assert opened(at) == new_id and any("Passport issued" in s.value for s in at.success)

    # 4. one headline, then its checks: no "Not run" rows
    assert any("Ready to file: every statement is supported by authoritative records" in m.value for m in at.markdown)
    assert "OK" in row(at, "Evidence") and "4 of 4 statements supported by authoritative records" in row(at, "Evidence")
    assert row(at, "Filing gate").startswith(":green") and "Ready to file" in row(at, "Filing gate")
    assert "Approved by B. Team Leader" in row(at, "Review")
    assert row(at, "Integrity").startswith(":green") and row(at, "Sources").startswith(":green")
    assert not any("Not run" in e.label for e in at.expander)

    # 5. Information manager -> Sources: tile 30 of 30 -> supersede the debt notice -> 17 of 30
    go(at, "Information manager")
    assert metric(at, "Retained AI outputs that cite records") == "30 of 30"
    form_button(at, "Mark superseded").click().run()          # defaults: 004790 superseded by 004912
    assert not at.exception
    assert metric(at, "Retained AI outputs that cite records") == "17 of 30"

    # 6. Recall by source: 13 outputs, 4 T2 -> queue T2
    assert metric(at, "Outputs affected") == "13" and metric(at, "T2 decision-informing") == "4"
    button(at, "Queue T2 outputs for re-review").click().run()
    assert any("Queued" in s.value for s in at.success)

    # 7. Records: an affected passport shows the Since filing alert as its headline
    go(at, "Records")
    affected = rows(db_path, "SELECT record_id FROM passports WHERE tier='T2' AND payload LIKE '%REC-2026/004790%' "
                             "ORDER BY seq DESC LIMIT 1")[0][0]
    at.session_state["records_open"] = affected                  # what clicking its row in the table does
    at.run()
    assert not at.exception
    since = row(at, "Since filing")
    assert since.startswith(":red") and "REC-2026/004790" in since and "REC-2026/004912" in since
    assert any("Changed since filing" in m.value for m in at.markdown)
