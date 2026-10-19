import json
import os
import sqlite3

import pytest

from recordcheck import citations as cit
from recordcheck.db import SEED_DIR

REFS = json.loads((SEED_DIR / "documents.json").read_text())[0]["references"]


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.delenv("RECORDCHECK_ONLINE", raising=False)


def test_normalise():
    assert cit.normalise("Indentured: Benefit deductions,  debt-recovery!") == "indentured benefit deductions debt recovery"


def test_extract_four():
    refs = cit.extract_references(REFS)
    assert [r.n for r in refs] == [1, 2, 3, 4]
    assert [r.kind for r in refs] == ["legislation", "article", "article", "article"]
    r2, r3 = refs[1], refs[2]
    assert (r2.authors, r2.year, r2.title) == ("Spicker, P.", 2023, "Discretion in overpayment recovery")
    assert r2.venue == "Journal of Social Welfare and Family Law"
    assert r3.year == 2022 and r3.title.startswith("Indentured: benefit")
    assert r3.venue == "Journal of Social Policy, 51(3)"
    assert refs[3].venue == "Australian Journal of Administrative Law, 26(3)"


def test_kind_case():
    (c,) = cit.extract_references("[1] Smith v Jones [2020] HCA 5.")
    assert c.kind == "case"


def test_check_document_statuses():
    res = cit.check_document(REFS)
    assert [r.status for r in res] == ["found", "found", "mismatch", "not_found"]
    assert res[0].note.startswith("Act found in force on the Federal Register of Legislation (C2004A04121)")
    assert [r.source for r in res] == ["fixture", "fixture", "fixture", "fixture"]
    assert cit.summary(res) == {"found": 2, "mismatch": 1, "not_found": 1, "not_checked": 0}


def test_summary_zero_filled():
    assert cit.summary([]) == {"found": 0, "mismatch": 0, "not_found": 0, "not_checked": 0}


def test_unknown_offline_not_checked():
    (c,) = cit.extract_references("[1] Nobody, A. (2020). A wholly unknown title here. Some Journal.")
    assert cit.lookup(c, online=False).status == "not_checked"


def test_network_error_not_raised(monkeypatch):
    def boom(*a, **k):
        raise cit.httpx.ConnectError("down")
    monkeypatch.setattr(cit.httpx, "get", boom)
    (c,) = cit.extract_references("[1] Nobody, A. (2020). A wholly unknown title here. Some Journal.")
    r = cit.lookup(c, online=True)
    assert r.status == "not_checked" and "ConnectError" in r.note


def test_online_judging_and_cache(monkeypatch):
    monkeypatch.setattr(cit, "_crossref", lambda c: [("A wholly unknown title here", 2020, "Some Journal", "10.1/x")])
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE citation_cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL)")
    (c,) = cit.extract_references("[1] Nobody, A. (2020). A wholly unknown title here. Some Journal.")
    r = cit.lookup(c, online=True, conn=conn)
    assert (r.status, r.source, r.doi) == ("found", "crossref", "10.1/x")
    assert conn.execute("SELECT COUNT(*) FROM citation_cache").fetchone()[0] == 1
    assert cit.lookup(c, online=False, conn=conn).status == "found"


def test_year_mismatch(monkeypatch):
    monkeypatch.setattr(cit, "_crossref", lambda c: [("A wholly unknown title here", 2024, "Some Journal", None)])
    (c,) = cit.extract_references("[1] Nobody, A. (2020). A wholly unknown title here. Some Journal.")
    assert cit.lookup(c, online=True).status == "mismatch"


@pytest.mark.skipif(os.environ.get("RECORDCHECK_ONLINE") != "true", reason="live network test")
def test_live_crossref():
    (c,) = cit.extract_references("[1] Edmiston, D. (2024). Indentured: benefit deductions, debt recovery and welfare disciplining. Social Policy & Administration.")
    assert cit.lookup(c, online=True).status in ("found", "mismatch", "not_checked")


BANNED = ("true", "false", "fake", "verified", "%")


def test_match_stage_labels():
    act, found, mm, nf = cit.check_document(REFS)
    assert cit.match_stage(found) == ("Step 2: lookup in offline cache, similarity 1.00", "found in cached index record")
    assert cit.match_stage(mm)[1] == "found, details differ"
    assert cit.match_stage(nf)[1] == "not found; possibly fabricated"
    assert cit.match_stage(act) == ("Step 2: exact Act name on the Federal Register of Legislation (offline copy)",
                                    "found in force on the register")
    case = cit.lookup(cit.extract_references("[1] Smith v Jones [2020] HCA 5.")[0], online=False)
    assert cit.match_stage(case) == ("Not looked up", "not checked; a person confirms")
    r = found.model_copy(update={"source": "openalex", "score": 0.912})
    assert cit.match_stage(r) == ("Step 3: fuzzy match in OpenAlex, similarity 0.91", "found in OpenAlex")


def test_stage_labels_wording(tmp_path, monkeypatch):
    """No label from either helper, across every seed document, says true/false/fake/verified or a percentage."""
    from recordcheck import db, evidence
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "t.sqlite"))
    conn = db.open_db()
    labels: list[str] = []
    for doc in db.get_documents(conn):
        results = cit.check_document(doc.references)
        labels += [s for r in results for s in cit.match_stage(r)]
        labels += [s for v in evidence.assess(doc, conn, results).verdicts for s in evidence.claim_stage(v)]
    conn.close()
    assert labels
    for s in labels:
        assert not any(b in s.lower() for b in BANNED), s
