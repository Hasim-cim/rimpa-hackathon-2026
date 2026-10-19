"""Known gaps. Each test asserts the CORRECT behaviour and is expected to fail today (xfail, strict).

When someone fixes a gap the test XPASSes, strict mode turns that into a failure, and the fix must update
EDGE_CASES.md (move the row to tested) and delete the xfail marker. Do not "fix" a gap by editing the test.
The reason string must start with the register ID: tests/test_edge_register.py enforces it.
"""
from __future__ import annotations

import sys

import pytest

from recordcheck import citations as cit
from recordcheck import db, evidence, passport
from recordcheck.models import Document

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_edge_cases import cr, event, rec, weigh  # noqa: E402

GAP = pytest.mark.xfail


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("RECORDCHECK_ONLINE", raising=False)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    return tmp_path


@pytest.fixture
def conn(env):
    c = db.open_db()
    yield c
    c.close()


def seed_records():
    c = db.open_db()
    try:
        return db.get_records(c)
    finally:
        c.close()


# ---------- citations ----------

@pytest.mark.xfail(strict=True, reason="EC-CIT-12 duplicate [n] numbers: the last result wins and hides a not_found")
def test_gap_cit_duplicate_reference_numbers():
    cites = [cr(1, "not_found"), cr(1, "found")]
    v = weigh("Rents rose sharply last year [1].", [], cites=cites, refs=[1])
    assert v.weight == "unsupported"


@pytest.mark.xfail(strict=True, reason="EC-CIT-13 a claim cites [n] with no entry in the references list; weigh ignores it")
def test_gap_cit_claim_cites_reference_that_does_not_exist():
    r = rec("R", fields={"case_id": "C1", "debt_amount": 4860}, content="Debt record.")
    v = weigh("The debt is $4,860 [9].", [r], cites=[cr(1, "found")], refs=[9])
    assert "[9]" in v.reason


class _Resp:
    def __init__(self, item):
        self._item = item

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"items": [self._item]}}


def _crossref_item(**extra):
    item = {"DOI": "10.1/x", "title": ["A wholly unknown title here"], "issued": {"date-parts": [[2020]]},
            "container-title": ["Some Journal"], "author": [{"family": "Nobody", "given": "A"}]}
    item.update(extra)
    return item


@pytest.mark.xfail(strict=True, reason="EC-CIT-15 a real title cited under the wrong authors still returns found")
def test_gap_cit_author_mismatch_is_not_found_status(monkeypatch):
    monkeypatch.setattr(cit.httpx, "get", lambda *a, **k: _Resp(_crossref_item(author=[{"family": "Zed", "given": "Q"}])))
    (c,) = cit.extract_references("[1] Nobody, A. (2020). A wholly unknown title here. Some Journal.")
    assert cit.lookup(c, online=True).status == "mismatch"


# ---------- evidence ----------

@pytest.mark.xfail(strict=True, reason="EC-EVI-12 two current records disagree on a field; the claim is supported and the conflict is not surfaced")
def test_gap_evi_conflicting_current_records_are_surfaced():
    a = rec("A", fields={"case_id": "C1", "rent_weekly": 380}, content="Rent record.")
    b = rec("B", fields={"case_id": "C1", "rent_weekly": 420}, content="Rent record.")
    v = weigh("The weekly rent is $380.", [a, b], case="C1")
    assert "conflict" in v.reason.lower() or "disagree" in v.reason.lower()


@pytest.mark.xfail(strict=True, reason="EC-EVI-14 a wrong amount is supported when the surrounding words match a record")
def test_gap_evi_wrong_amount_with_matching_phrase_is_supported():
    v = weigh("The applicant's weekly earnings were $900 from Example Logistics Pty Ltd.", seed_records(), case="2026/0412")
    assert v.weight != "supported"


@pytest.mark.xfail(strict=True, reason="EC-EVI-16 dates and date ranges are never compared with record dates (ARCHITECTURE promises it)")
def test_gap_evi_wrong_date_range_is_supported():
    v = weigh("The applicant earned income from 1 June 2026 to 31 December 2026.", seed_records(), case="2026/0412")
    assert v.weight != "supported"


@pytest.mark.xfail(strict=True, reason="EC-EVI-18 contradiction rules cover only occupants; a wrong rent is merely unsupported")
def test_gap_evi_only_occupants_can_contradict():
    r = rec("R", fields={"case_id": "C1", "rent_weekly": 380}, content="Housing record.")
    v = weigh("The weekly rent is $500.", [r], case="C1")
    assert v.weight == "contradicted"


@pytest.mark.xfail(strict=True, reason="EC-EVI-19 any sentence containing 'household' is supported by an occupants record, whatever it says")
def test_gap_evi_household_word_links_any_household_claim():
    v = weigh("The household is five adults.", seed_records(), case="2026/0412")
    assert v.weight != "supported"


@pytest.mark.xfail(strict=True, reason="EC-EVI-28 sentence splitting breaks on abbreviations such as 'Dr.'")
def test_gap_evi_abbreviation_splits_a_sentence():
    doc = Document(id="D", title="t", body="Dr. Smith assessed the case. The rent is $380.50 a week.")
    assert [c.text for c in evidence.split_claims(doc, use_llm=False)] == [
        "Dr. Smith assessed the case.", "The rent is $380.50 a week."]


@pytest.mark.xfail(strict=True, reason="EC-EVI-29 a References block pasted into the body is split into claims")
def test_gap_evi_references_in_body_become_claims():
    doc = Document(id="D", title="t", body="Rent is $380.\n\nReferences\n[1] Spicker, P. (2023). Discretion in overpayment recovery. J.")
    assert not any("Spicker" in c.text or "References" in c.text for c in evidence.split_claims(doc, use_llm=False))


# ---------- passport and chain ----------

@pytest.mark.xfail(strict=True, reason="EC-PAS-03 deleting the newest passport(s) is not detected; nothing anchors the chain head")
def test_gap_pas_tail_truncation_is_undetected(conn):
    ev = event("agency-assistant", id="EVT-TAIL", decision_flag=True)
    p = passport.build(ev, tier="T2", conn=conn)
    conn.execute("DELETE FROM passports WHERE record_id=?", (p.record.id,))
    assert not passport.verify_chain(conn).ok


# ---------- source recall ----------

@pytest.mark.xfail(strict=True, reason="EC-SRC-10 any current link supports the whole claim, hiding the superseded fact")
def test_gap_src_fact_from_superseded_record_hidden_by_other_links(conn):
    from recordcheck import recall
    recall.mark_superseded(conn, "REC-2026/004790", "REC-2026/004912", "Amount recalculated", "I. Manager")
    a = evidence.assess(db.get_document(conn, "DOC-2026/0412-summary"), conn, use_llm=False)
    v = next(v for c, v in zip(a.claims, a.verdicts) if "$4,860" in c.text)
    assert v.weight != "supported"
