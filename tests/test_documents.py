"""Every seed document assesses to the verdicts the demo script relies on (offline, regex split)."""
import os

import pytest

from recordcheck import citations, db, evidence

EXPECTED = {
    # the hardship summary: AI and human sentences both go red; AI sentences also go green
    "DOC-2026/0412-summary": ["supported", "weak", "unsupported", "contradicted", "supported", "weak", "unsupported"],
    # a careful human note: everything traces to current records
    "DOC-2026/0587-eligibility": ["supported", "supported", "supported", "supported"],
    # an AI briefing: right policy, one real study, two fabricated references
    "DOC-2026/briefing-waivers": ["supported", "supported", "unsupported", "weak", "supported"],
    # an agent's case note: mostly on record, one statement nothing on file supports
    "DOC-2026/0412-agent-note": ["supported", "supported", "supported", "supported", "unsupported"],
}


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    return db.open_db()


@pytest.mark.parametrize("doc_id", list(EXPECTED))
def test_document_verdicts(conn, doc_id):
    doc = db.get_document(conn, doc_id)
    cits = citations.check_document(doc.references, conn=conn) if doc.references else []
    a = evidence.assess(doc, conn, cits, use_llm=False)
    assert [v.weight for v in a.verdicts] == EXPECTED[doc_id], [(c.text[:40], v.weight, v.reason) for c, v in zip(a.claims, a.verdicts)]


def test_briefing_citations(conn):
    doc = db.get_document(conn, "DOC-2026/briefing-waivers")
    cits = citations.check_document(doc.references, conn=conn)
    assert [c.status for c in cits] == ["not_checked", "not_found", "found", "not_found"]


def test_summary_reference_3_is_mismatch_only_because_of_how_it_was_cited(conn):
    doc = db.get_document(conn, "DOC-2026/0412-summary")
    cits = citations.check_document(doc.references, conn=conn)
    assert cits[2].status == "mismatch" and "2024" in cits[2].note
