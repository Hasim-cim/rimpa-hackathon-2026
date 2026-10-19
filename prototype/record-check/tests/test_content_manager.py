"""Content Manager adapter (I2): a contract test against Content Manager-shaped records. Offline, no network."""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from recordcheck import connectors, content_manager as cm, db, evidence, passport
from recordcheck.models import AIEvent, Claim


@pytest.fixture
def source():
    return cm.ContentManagerSource()


def test_it_is_a_record_source_over_assumed_shape_fixtures(source):
    assert isinstance(source, connectors.RecordSource) and source.shape == "assumed"
    assert len(source.list_records()) == 6 and source.get_record("NO-SUCH") is None


def test_read_mapper_follows_the_declared_rules(source):
    v4, v3, draft = (source.get_record(i) for i in ("CM-26/0101", "CM-24/0077", "CM-26/0500"))
    assert (v4.status, v4.title, v4.system, v4.created_by) == ("current", "Hardship policy guide, version 4",
                                                               "Content Manager", "Policy branch")
    assert v4.fields["retention_schedule"] == "Retain permanently (policy)" and v4.fields["record_type"] == "Policy"
    assert v3.status == "superseded" and v3.superseded_by == "CM-26/0101"     # the declared SupersededBy field
    assert draft.status == "draft"                                           # not finalised
    notice = source.get_record("CM-26/0412")
    assert notice.fields["case_id"] == "2026/0412" and notice.fields["debtAmount"] == 4860


def test_a_different_declared_rule_changes_the_mapping():
    s = cm.ContentManagerSource(cfg=cm.CMConfig(superseded_field="ReplacedBy", draft_when_not_finalised=False))
    assert s.get_record("CM-24/0077").status == "current"       # no ReplacedBy field: not superseded under this rule
    assert s.get_record("CM-26/0500").status == "current"


def test_the_engine_weighs_claims_against_content_manager_records(source):
    recs = source.list_records()
    by = {r.id: r for r in recs}
    def weigh(text):
        c = Claim(id="c1", text=text, author="ai", position=1)
        return evidence.weigh(c, evidence.link_claim(c, recs, "2026/0412"), by)
    assert weigh("The debt notice records an overpayment of $4,860.").weight == "supported"
    assert weigh("The applicant lives alone.").weight == "contradicted"       # CM tenancy record: two occupants
    draft = weigh("Draft version 5 for consultation proposes decisions within 14 days.")
    assert draft.weight == "weak" and "a draft" in draft.reason               # declared rule: not finalised = draft
    # "within 28 days of a complete application" still reads supported: it shares wording with version 4 (21 days).
    # That is gap EC-EVI-14 (numbers in a sentence linked by wording), which G1 closes; not an adapter issue.


def test_sink_writes_a_create_record_request_and_the_passport_to_the_outbox(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "s.sqlite"))
    conn = db.open_db()
    p = passport.build(AIEvent(id="EVT-CM", app_id="agency-assistant", user="u", created=datetime(2026, 10, 19, 9),
                               prompt="p", output="o", model_requested="m", model_returned="m", provider="x"),
                       tier="T1", conn=conn)
    sink = cm.ContentManagerSink(outbox=tmp_path / "outbox")
    assert isinstance(sink, connectors.PassportSink)
    r = sink.file(p)
    stem = p.record.id.replace("/", "-")
    req = json.loads((tmp_path / "outbox" / f"{stem}.create-record.json").read_text())
    assert req["operation"] == "Create Record" and req["RecordRecordType"] == "Record Check Passport"
    assert req["RecordExternalReference"] == p.record.id and req["then"]["operation"] == "Attach Electronic File"
    attached = json.loads((tmp_path / "outbox" / req["then"]["File"]).read_text())
    assert attached["integrity"]["hash"] == p.integrity.hash                   # the passport itself, unchanged
    log = [json.loads(l) for l in (tmp_path / "outbox" / "requests.log.jsonl").read_text().splitlines()]
    assert log[-1]["sent"] is False and r.location.startswith("outbox/")
    conn.close()
