"""Information-manager dashboard: counts match the seed worked out independently; signals never act."""

import importlib
import json
import re

import pytest
from fastapi.testclient import TestClient

from recordcheck import dashboard, db, policy as policymod
from recordcheck.models import DashboardReport

N7, ATLAS = "northstar-7-2026-03-01", "atlas-mini-2025-11-20"
BANNED = re.compile(r"true|false|fake|verified", re.I)


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "d.sqlite"))
    c = db.open_db()
    yield c
    c.close()


@pytest.fixture
def pol():
    return policymod.from_preset(policymod.get_preset(policymod.DEFAULT_PRESET), "Test agency", "tests")


def _seed(name):
    return json.loads((db.SEED_DIR / name).read_text(encoding="utf-8"))


def _kpi(rep, id_):
    return next(k for k in rep.kpis if k.id == id_)


def test_kpis_match_independent_counts(conn, pol):
    rep = dashboard.report(conn, pol)
    raw = _seed("passports.json")
    recs = {r["id"]: r for r in _seed("records.json")}
    total = len(raw)

    approved = sum(p["business"].get("gate") in ("ready", None) and bool(p["review"])
                   and p["review"]["decision"] in ("approved", "approved_with_edits") for p in raw)
    needs = sum(bool(p["process"]["evidence_summary"].get("contradicted") or p["process"]["evidence_summary"].get("unsupported")
                     or p["process"]["citation_summary"].get("not_found")
                     or p["business"].get("gate") in ("blocked", "attention")) for p in raw)

    def weak(r):
        return (not r["authoritative"] or r["system"] not in pol.authoritative_systems
                or r["status"] in ("draft", "superseded"))

    def narrow(p):   # seed passports are summary-only: judged on their source ids
        ids = list(dict.fromkeys(p["process"]["source_record_ids"]))
        return bool(ids) and (len(ids) == 1 or len({recs[i]["system"] for i in ids}) == 1 or any(weak(recs[i]) for i in ids))

    t0 = sum(p["business"]["tier"] == "T0" for p in raw)
    fa = _kpi(rep, "filed_approved")
    assert (fa.count, fa.total, fa.not_counted) == (approved, total - t0, t0)      # T0 logs need no review
    assert fa.not_counted_label == f"{t0} logs needed no review (T0, kept 90 days)"
    assert _kpi(rep, "needs_review").label.startswith("Misinformation signals: ")
    assert _kpi(rep, "narrow_evidence").label == f"Bias signals: {_kpi(rep, 'narrow_evidence').count} of {total} rest on narrow evidence"
    assert _kpi(rep, "needs_review").count == needs and needs > 0
    assert _kpi(rep, "narrow_evidence").count == sum(narrow(p) for p in raw)
    k = _kpi(rep, "needs_review")
    assert k.percent == round(100 * needs / total, 1) and k.display == f"{needs} of {total} ({round(100 * needs / total)}%)"
    assert sum(r.total for r in rep.by_function) == total
    assert sum(r.needs_review for r in rep.by_function) == needs
    assert sum(r.narrow_evidence for r in rep.by_function) == _kpi(rep, "narrow_evidence").count


def test_model_signals_flag_only_northstar_7(conn, pol):
    rep = dashboard.report(conn, pol)
    by = {s.model_id: s for s in rep.model_signals}
    assert len(by) == 3
    n7 = by[N7]
    assert n7.suggested and n7.references_checked >= 10 and 0.30 <= n7.rate <= 0.40
    assert [m for m, s in by.items() if s.suggested] == [N7]
    assert by[ATLAS].references_checked >= 10 and by[ATLAS].rate < 0.15 and not by[ATLAS].suggested
    assert _kpi(rep, "recall_suggested").count == 1
    assert _kpi(rep, "recall_suggested").plain.startswith(f"Recall suggested: {N7}, ")
    assert _kpi(rep, "recall_suggested").plain.endswith("The information manager decides.")


def test_signal_never_recalls(conn, pol):
    dashboard.report(conn, pol)
    assert {e.model_id: e.status for e in db.get_model_registry(conn)}[N7] == "active"
    assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE action LIKE 'model.%'").fetchone()[0] == 0


def test_min_refs_above_count_turns_flag_off(conn, pol):
    pol.recall_signal_min_refs = 16
    rep = dashboard.report(conn, pol)
    assert not any(s.suggested for s in rep.model_signals)
    assert _kpi(rep, "recall_suggested").count == 0


def test_zero_passports_says_none_yet(conn, pol):
    for t in ("passports", "ai_events", "passport_checks"):
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    rep = dashboard.report(conn, pol)
    for k in rep.kpis:
        if k.id != "recall_suggested":
            assert k.display == "none yet" and k.percent is None and k.count == 0
    assert rep.recent == [] and rep.by_function == [] and rep.recent_supported == []
    assert rep.authorship.ai == rep.authorship.human == 0


def test_recent_is_last_ten_filed(conn, pol):
    rep = dashboard.report(conn, pol)
    assert [r.record_id for r in rep.recent] == [p["record"]["id"] for p in _seed("passports.json")[::-1][:10]]


def test_disposed_passports_are_excluded(conn, pol):
    from datetime import date
    from recordcheck import disposal
    due = disposal.due_for_disposal(conn, rules=pol.tier_rules)
    assert due
    before = dashboard.report(conn, pol)
    disposal.approve_disposal(conn, [due[0].record_id], approved_by="IM", reason="test", rules=pol.tier_rules)
    after = dashboard.report(conn, pol)
    assert sum(r.total for r in after.by_function) == sum(r.total for r in before.by_function) - 1
    assert after.disposal_due.count == before.disposal_due.count - 1


def test_stored_checks_feed_statements_authorship_and_narrow_evidence(conn, pol):
    # a passport issued with stored checks: one AI statement resting on a single record
    from recordcheck import citations as cit, evidence, passport
    from recordcheck.models import AIEvent
    doc = db.get_document(conn, "DOC-2026/0412-summary")
    results = cit.check_document(doc.references, conn=conn)
    assessment = evidence.assess(doc, conn, results, policy=pol, document_type=None)
    ev = AIEvent(id="EVT-DASH-1", app_id="agency-assistant", user="A. Caseworker", created="2026-10-18T09:00:00",
                 prompt="p", output="o", model_requested=N7, model_returned=N7, provider="Northstar AI (fictional vendor)",
                 exported_to_document=doc.id, function="Debt waiver assessment",
                 source_record_ids=evidence.relied_on(assessment, conn, pol, None))
    loose = pol.document_types[0].model_copy(deep=True)
    loose.quality.max_unsupported = loose.quality.max_contradicted = 99
    loose.quality.citations_not_found_blocks = False
    pol.document_types[0] = loose
    p = passport.build(ev, tier="T1", assessment=assessment, citations=results, conn=conn, policy=pol,
                       document_type=loose.id)
    rep = dashboard.report(conn, pol)
    assert rep.authorship.passports_counted == 1
    assert rep.authorship.ai + rep.authorship.human == len(assessment.claims)
    assert rep.recent[0].record_id == p.record.id
    sup = [v for v in assessment.verdicts if v.weight == "supported"]
    assert len(rep.recent_supported) == min(10, len(sup))
    assert all(s.source_record_ids for s in rep.recent_supported)


def test_no_forbidden_words(conn, pol):
    rep = dashboard.report(conn, pol)
    texts = [rep.authorship.plain, rep.rot.plain, rep.disposal_due.plain]
    texts += [t for k in rep.kpis for t in (k.label, k.plain, k.display)]
    texts += [s.plain for s in rep.model_signals] + [r.status for r in rep.recent]
    texts += [s.text for s in rep.recent_supported]
    for t in texts:
        assert not BANNED.search(t), t


def test_api_route(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "api.sqlite"))
    import api.main as main
    main = importlib.reload(main)
    try:
        r = TestClient(main.app).get("/dashboard")
        assert r.status_code == 200
        rep = DashboardReport.model_validate(r.json())
        assert [k.id for k in rep.kpis] == ["filed_approved", "needs_review", "narrow_evidence", "recall_suggested"]
    finally:
        main.conn.close()


def test_old_policy_json_still_loads(pol):
    d = json.loads(pol.model_dump_json())
    d.pop("recall_signal_threshold"); d.pop("recall_signal_min_refs")
    from recordcheck.models import Policy
    p = Policy.model_validate(d)
    assert p.recall_signal_threshold == 0.30 and p.recall_signal_min_refs == 10
    assert policymod.get_preset(policymod.DEFAULT_PRESET)


# ---------- B2: series counted in the engine, so the web does no maths ----------

def test_series_on_the_seed(conn, pol):
    rep = dashboard.report(conn, pol)
    assert len(rep.filed_by_week) == 8 and rep.filed_by_week[-1].week_start.weekday() == 0
    assert sum(w.filed for w in rep.filed_by_week) <= 40 and all(w.approved <= w.filed for w in rep.filed_by_week)
    assert [(g.document_type, g.not_recorded) for g in rep.gate_by_type] == [(None, 40)]   # seed predates types
    assert sum(m.filed for m in rep.by_model) == 40 and {m.status for m in rep.by_model} <= {"active", "not registered"}
    assert rep.bias.ok + rep.bias.attention + rep.bias.not_run == 40
    assert rep.bias.attention == _kpi(rep, "narrow_evidence").count          # one rule, two views: they agree
    assert (rep.queue.open, rep.queue.closed) == (0, 0)


def test_series_follow_filing_queueing_and_recall(conn, pol):
    from datetime import datetime, timezone
    from recordcheck import citations as cit, evidence, passport, recall
    from recordcheck.models import AIEvent, Review
    doc = db.get_document(conn, "DOC-2026/0587-eligibility")
    a = evidence.assess(doc, conn, [], use_llm=False, policy=pol, document_type="case-note")
    ev = AIEvent(id="EVT-B2", app_id="agency-assistant", user="A. Caseworker", created=datetime(2026, 10, 19, 9),
                 prompt="p", output=doc.body, model_requested="m-new", model_returned="m-new", provider="x",
                 decision_flag=True, source_record_ids=evidence.relied_on(a, conn, pol, "case-note"))
    passport.build(ev, tier="T2", assessment=a, conn=conn, policy=pol, document_type="case-note",
                   review=Review(reviewer="B. Team Leader", decision="approved", reviewed_at=datetime.now(timezone.utc)))
    recall.queue_for_review(conn, [db.get_passports(conn)[0].record.id], by="IM", reason="r")
    rep = dashboard.report(conn, pol)
    case_note = next(g for g in rep.gate_by_type if g.document_type == "case-note")
    assert (case_note.name, case_note.ready) == ("Case note", 1)
    assert next(m for m in rep.by_model if m.model_id == "m-new").status == "not registered"
    assert rep.filed_by_week[-1].filed >= 1 and rep.queue.open == 1
    assert rep.bias.attention == _kpi(rep, "narrow_evidence").count == 8   # the human-written note counts in both
