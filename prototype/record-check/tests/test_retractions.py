"""Retracted papers (D1): a reference to a retracted, withdrawn or expression-of-concern paper is never plain found.
Offline: the captured notice fixture, and Crossref mocked. Real example checked live 19 Oct: 10.1177/1758835919874651."""
from __future__ import annotations

from recordcheck import citations as cit
from recordcheck.models import Citation, CitationResult

RETRACTED = "10.1177/1758835919874651"


def found(doi, note="Fixture match on title and year."):
    return CitationResult(citation=Citation(n=1, raw="[1] x"), status="found", source="fixture", doi=doi, score=1.0,
                          note=note)


class _Resp:
    def __init__(self, items):
        self.items = items

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"items": self.items}}


def test_the_real_retraction_from_the_offline_notices():
    r = cit._with_updates(found(RETRACTED), None, online=False)
    assert r.status == "mismatch"
    assert r.note.startswith("Retracted on 2021-12-15 (notice 10.1177/17588359211061903).")


def test_a_paper_with_no_notice_stays_found(monkeypatch):
    monkeypatch.setattr(cit.httpx, "get", lambda *a, **k: _Resp([]))
    assert cit._with_updates(found("10.1/clean"), None, online=True).status == "found"


def test_crossref_record_carries_its_own_retraction_so_no_extra_call(monkeypatch):
    monkeypatch.setattr(cit.httpx, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no call")))
    upd = [{"type": "retraction", "DOI": "10.1/notice", "updated": {"date-time": "2024-03-01T00:00:00Z"}}]
    r = cit._with_updates(found("10.1/x"), upd, online=True)
    assert r.status == "mismatch" and "Retracted on 2024-03-01 (notice 10.1/notice)" in r.note


def test_openalex_match_asks_crossref_for_notices_and_reads_an_expression_of_concern(monkeypatch):
    calls = []

    def get(url, params=None, **k):
        calls.append(params.get("filter"))
        return _Resp([{"DOI": "10.1/eoc", "update-to": [{"DOI": "10.1/y", "type": "expression_of_concern",
                                                          "updated": {"date-time": "2025-05-05T00:00:00Z"}}]}])
    monkeypatch.setattr(cit.httpx, "get", get)
    r = cit._with_updates(found("10.1/Y"), None, online=True)       # DOI case differs: still the same paper
    assert calls == ["updates:10.1/Y"]
    assert r.status == "mismatch" and r.note.startswith("Expression of concern on 2025-05-05 (notice 10.1/eoc).")


def test_a_failed_notice_lookup_never_changes_the_result(monkeypatch):
    def down(*a, **k):
        raise cit.httpx.ConnectError("down")
    monkeypatch.setattr(cit.httpx, "get", down)
    assert cit._with_updates(found("10.1/z"), None, online=True).status == "found"


def test_not_found_and_not_checked_are_left_alone():
    nf = found(RETRACTED).model_copy(update={"status": "not_found"})
    assert cit._with_updates(nf, None, online=False).status == "not_found"


def test_end_to_end_crossref_search_hit_that_was_retracted(monkeypatch):
    item = {"DOI": "10.1/x", "title": ["A wholly unknown title here"], "issued": {"date-parts": [[2020]]},
            "container-title": ["Some Journal"], "updated-by": [{"type": "retraction", "DOI": "10.1/notice"}]}
    monkeypatch.setattr(cit.httpx, "get", lambda *a, **k: _Resp([item]))
    (c,) = cit.extract_references("[1] Nobody, A. (2020). A wholly unknown title here. Some Journal.")
    r = cit.lookup(c, online=True)
    assert r.status == "mismatch" and r.note.startswith("Retracted (notice 10.1/notice).")
