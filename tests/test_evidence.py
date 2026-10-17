import pytest

from recordcheck import db, evidence, llm
from recordcheck.models import Citation, CitationResult, Claim, Document


def _cr(n, status):
    return CitationResult(citation=Citation(n=n, raw=f"[{n}]"), status=status)


CITES = [_cr(1, "not_checked"), _cr(2, "found"), _cr(3, "mismatch"), _cr(4, "not_found")]


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    c = db.open_db()
    yield c
    c.close()


@pytest.fixture
def assessment(conn):
    doc = db.get_document(conn, "DOC-2026/0412-summary")
    return evidence.assess(doc, conn, CITES)


def test_seed_verdicts(assessment):
    assert assessment.method == "seed"
    v = {x.claim_id: x for x in assessment.verdicts}
    assert {k: x.weight for k, x in v.items()} == {
        "c1": "supported", "c2": "weak", "c3": "unsupported", "c4": "contradicted",
        "c5": "supported", "c6": "weak", "c7": "unsupported"}
    ids = lambda c: {l.record_id for l in v[c].links}
    assert ids("c1") == {"REC-2026/004811"}
    assert ids("c2") == {"POL-HARDSHIP-v3"}
    assert ids("c3") == set()
    assert "REC-2026/003540" in ids("c4") and "REC-2026/003540" in v["c4"].reason
    assert {"REC-2026/003540", "REC-2026/004790"} <= ids("c5")
    assert "REC-2026/004805" in ids("c5")
    assert ids("c6") == set() and "external source" in v["c6"].reason
    assert {"WEB-FORUM-2026-07", "POL-HARDSHIP-v3"} <= ids("c7")
    assert "[4]" in v["c7"].reason


def test_v4_not_linked_for_severe(assessment):
    assert "POL-HARDSHIP-v4" not in {l.record_id for l in assessment.verdicts[1].links}


def test_summary_zero_filled(assessment):
    assert evidence.summary(assessment.verdicts) == {
        "supported": 2, "weak": 2, "unsupported": 2, "contradicted": 1}
    assert evidence.summary([]) == {"supported": 0, "weak": 0, "unsupported": 0, "contradicted": 0}


def test_not_checked_citation_neutral(conn):
    recs = db.get_records(conn)
    c = Claim(id="c1", text="Weekly rent of $380 applies [1].", author="ai", position=1, citation_refs=[1])
    v = evidence.weigh(c, evidence.link_claim(c, recs, "2026/0412"), {r.id: r for r in recs}, [_cr(1, "not_checked")])
    assert v.weight == "supported"


def test_case_filter(conn):
    recs = db.get_records(conn)
    c = Claim(id="c1", text="Weekly earnings of $820.", author="ai", position=1)
    assert evidence.link_claim(c, recs, "2026/9999") == []


def test_sentence_split_fallback(conn):
    doc = Document(id="D", title="t", case_id="2026/0412", default_author="human",
                   body="The applicant lives alone. Rent is $380 a week [2]. Done!")
    claims = evidence.split_claims(doc, use_llm=False)
    assert [c.id for c in claims] == ["c1", "c2", "c3"]
    assert claims[1].citation_refs == [2] and claims[0].author == "human"
    a = evidence.assess(doc, conn, CITES, use_llm=False)
    assert a.method == "sentence-split"
    assert a.verdicts[0].weight == "contradicted"


def test_llm_available(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.available() is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert llm.available() is True


def test_llm_split_used(monkeypatch):
    monkeypatch.setattr(llm, "split_claims", lambda t: ["One [1].", "Two."])
    monkeypatch.setattr(llm, "LAST_MODEL_RETURNED", "m-1")
    doc = Document(id="D", title="t", body="One [1]. Two.")
    claims, method = evidence._split(doc, True)
    assert method == "llm:m-1" and claims[0].citation_refs == [1]


def test_complete_monkeypatched(monkeypatch):
    from recordcheck.models import LLMResult
    monkeypatch.setattr(llm, "complete", lambda p, system="": LLMResult(
        text="hi", model_requested="a", model_returned="b"))
    assert llm.complete("x").model_returned == "b"


def test_weak_when_only_non_authoritative_link():
    """A claim resting only on the forum post (non-authoritative, current) is weak, not a crash."""
    from recordcheck import evidence
    from recordcheck.models import Claim, ClaimLink, SourceRecord
    import datetime as dt
    forum = SourceRecord(id="WEB-1", title="Forum", system="Web", authoritative=False, status="current",
                         created=dt.date(2026, 7, 1), created_by="Unknown", content="x", fields={})
    claim = Claim(id="cx", text="Forum says so.", author="human", position=1)
    v = evidence.weigh(claim, [ClaimLink(claim_id="cx", record_id="WEB-1", rule="keyphrase")], {"WEB-1": forum})
    assert v.weight == "weak" and "WEB-1" in v.reason
