"""A real title cited under the wrong authors (D2, closes EC-CIT-15). Offline; Crossref and OpenAlex mocked."""
from __future__ import annotations

import pytest

from recordcheck import citations as cit
from recordcheck.models import Citation, CitationResult


class _Resp:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def _crossref(authors):
    return _Resp({"message": {"items": [{"DOI": "10.1/x", "title": ["A wholly unknown title here"],
                                         "issued": {"date-parts": [[2020]]}, "container-title": ["Some Journal"],
                                         "author": [{"family": a, "given": "Q"} for a in authors]}]}})


def lookup(cited_authors, crossref_authors, monkeypatch):
    monkeypatch.setattr(cit.httpx, "get", lambda *a, **k: _crossref(crossref_authors))
    (c,) = cit.extract_references(f"[1] {cited_authors} (2020). A wholly unknown title here. Some Journal.")
    return cit.lookup(c, online=True)


@pytest.mark.parametrize("authors, expected", [
    ("Okafor, L. & Brennan, S.", ["okafor", "brennan"]),
    ("Spicker, P.", ["spicker"]),
    ("van der Berg, J. and Smith, K.", ["berg", "smith"]),
    (None, []),
])
def test_cited_surnames(authors, expected):
    assert cit.cited_surnames(authors) == expected


def test_wrong_authors_is_mismatch_and_names_both(monkeypatch):
    r = lookup("Nobody, A.", ["Zed"], monkeypatch)
    assert r.status == "mismatch" and "lists Zed as authors, not Nobody, A." in r.note


def test_one_matching_author_is_enough(monkeypatch):
    assert lookup("Okafor, L. & Brennan, S.", ["Brennan", "Lee"], monkeypatch).status == "found"


def test_particles_in_family_names_still_match(monkeypatch):
    assert lookup("van der Berg, J.", ["van der Berg"], monkeypatch).status == "found"


def test_no_authors_on_either_side_changes_nothing(monkeypatch):
    assert lookup("Nobody, A.", [], monkeypatch).status == "found"
    r = CitationResult(citation=Citation(n=1, raw="x"), status="found", source="fixture", note="n")
    assert cit._authors_match(r, ["Zed"]).status == "found"          # nothing cited to compare


def test_wrong_authors_adds_to_an_existing_mismatch(monkeypatch):
    monkeypatch.setattr(cit.httpx, "get", lambda *a, **k: _crossref(["Zed"]))
    (c,) = cit.extract_references("[1] Nobody, A. (2015). A wholly unknown title here. Some Journal.")
    r = cit.lookup(c, online=True)
    assert r.status == "mismatch" and "published 2020, not 2015" in r.note and "lists Zed" in r.note
