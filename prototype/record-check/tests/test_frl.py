"""Legislation references and the Federal Register of Legislation (L1). Offline: fixtures, and the live path with
the register mocked. Evidence: research/live-api-evidence/frl/."""
from __future__ import annotations

import pytest

from recordcheck import citations as cit
from recordcheck import db, frl


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "f.sqlite"))
    c = db.open_db()
    yield c
    c.close()


def ref(raw):
    (c,) = cit.extract_references(f"[1] {raw}")
    assert c.kind == "legislation", c
    return c


@pytest.mark.parametrize("raw, name", [
    ("Social Security Act 1991 (Cth) s 1237AAD.", "Social Security Act 1991"),
    ("Archives Act 1983 (Cth), s 24", "Archives Act 1983"),
    ("Privacy Act 1988 (Cth) sch 1", "Privacy Act 1988"),
    ("Public Governance, Performance and Accountability Act 2013 (Cth) s 15",
     "Public Governance, Performance and Accountability Act 2013"),
])
def test_normalise_strips_jurisdiction_and_section(raw, name):
    assert frl.normalise(raw) == name


def test_offline_fixtures_cover_the_demo_and_never_say_fabricated():
    got = {raw: cit.lookup(ref(raw), online=False) for raw in (
        "Social Security Act 1991 (Cth) s 1237AAD.", "Public Service Act 1922 (Cth)", "Social Security Act 1947",
        "Privacy Act 1989 (Cth)", "Records Integrity Act 2021 (Cth)")}
    ssa, ps, renamed, year, invented = got.values()
    assert ssa.status == "found" and "C2004A04121" in ssa.note and "section is for a person to confirm" in ssa.note
    assert ps.status == "mismatch" and "repealed on 5 December 1999" in ps.note and "Public Employment" in ps.note
    assert renamed.status == "mismatch" and "Social Services Consolidation Act 1947" in renamed.note   # both names
    assert year.status == "not_checked"          # no wrong-year fixture: live cannot find it either (tested 19 Oct)
    assert invented.status == "not_checked" and "No Commonwealth Act of this name" in invented.note
    assert all(r.status != "not_found" for r in got.values())


def test_state_legislation_is_never_sent_to_the_commonwealth_register(monkeypatch):
    monkeypatch.setattr(frl.httpx, "get", lambda *a, **k: pytest.fail("no call for state law"))
    r = cit.lookup(ref("Residential Tenancies Act 2010 (NSW) s 41"), online=True)
    assert r.status == "not_checked" and "State or territory" in r.note


class _Resp:
    def __init__(self, value, status=200):
        self.value, self.status_code = value, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise frl.httpx.HTTPStatusError("x", request=None, response=None)

    def json(self):
        return {"value": self.value}


def _register(answers, calls):
    """A fake register: answers[i] for the i-th call, recording each $filter."""
    def get(url, params=None, **kw):
        calls.append(params["$filter"])
        a = answers[len(calls) - 1]
        if isinstance(a, Exception):
            raise a
        return _Resp(a)
    return get


def test_live_in_force_is_cached_so_a_second_check_makes_no_call(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(frl.httpx, "get", _register([[{"id": "C2004A00538", "name": "Public Service Act 1999",
                                                       "status": "InForce", "year": 1999}]], calls))
    monkeypatch.setattr(frl, "_load_fixtures", lambda: {})
    r = cit.lookup(ref("Public Service Act 1999 (Cth) s 10"), online=True, conn=conn)
    assert r.status == "found" and r.source == "frl" and calls == ["name eq 'Public Service Act 1999'"]
    again = cit.lookup(ref("Public Service Act 1999 (Cth)"), online=False, conn=conn)   # offline now: from the cache
    assert again.status == "found" and len(calls) == 1


def test_live_wrong_year_keeps_acts_only(conn, monkeypatch):
    """The client-side filter, if the register's contains answer ever includes the Act itself (it did not, 19 Oct)."""
    calls = []
    contains = [{"id": "F2017L01234", "name": "Privacy Act 1988 - Tax File Number Guidelines", "collection": "LegislativeInstrument"},
                {"id": "C2004A03712", "name": "Privacy Act 1988", "status": "InForce", "year": 1988, "collection": "Act"}]
    monkeypatch.setattr(frl.httpx, "get", _register([[], contains], calls))
    monkeypatch.setattr(frl, "_load_fixtures", lambda: {})
    r = cit.lookup(ref("Privacy Act 1989 (Cth)"), online=True, conn=conn)
    assert r.status == "mismatch" and "The register has Privacy Act 1988" in r.note
    assert calls[1] == "contains(name,'Privacy Act')"


def test_live_no_match_is_not_checked_never_fabricated(conn, monkeypatch):
    monkeypatch.setattr(frl.httpx, "get", _register([[], []], []))
    monkeypatch.setattr(frl, "_load_fixtures", lambda: {})
    r = cit.lookup(ref("Records Integrity Act 2021 (Cth)"), online=True, conn=conn)
    assert r.status == "not_checked" and "No Commonwealth Act of this name" in r.note


@pytest.mark.parametrize("failure", [frl.httpx.ReadTimeout("slow"), frl.httpx.ConnectError("down")])
def test_timeout_or_rate_limit_reads_not_checked_and_is_not_cached(conn, monkeypatch, failure):
    monkeypatch.setattr(frl.httpx, "get", _register([failure], []))
    monkeypatch.setattr(frl, "_load_fixtures", lambda: {})
    r = cit.lookup(ref("Archives Act 1983 (Cth)"), online=True, conn=conn)
    assert r.status == "not_checked" and "did not respond" in r.note
    assert conn.execute("SELECT COUNT(*) FROM citation_cache WHERE key LIKE 'frl:%'").fetchone()[0] == 0


def test_http_429_reads_not_checked(conn, monkeypatch):
    monkeypatch.setattr(frl.httpx, "get", lambda *a, **k: _Resp([], status=429))
    monkeypatch.setattr(frl, "_load_fixtures", lambda: {})
    assert cit.lookup(ref("Archives Act 1983 (Cth)"), online=True, conn=conn).status == "not_checked"


def test_offline_and_not_cached_makes_no_call(monkeypatch):
    monkeypatch.setattr(frl.httpx, "get", lambda *a, **k: pytest.fail("offline must not call"))
    monkeypatch.setattr(frl, "_load_fixtures", lambda: {})
    r = cit.lookup(ref("Archives Act 1983 (Cth)"), online=False)
    assert r.status == "not_checked" and "online lookup is off" in r.note


def test_stage_labels_follow_the_register_result():
    from recordcheck.models import CitationResult
    c = ref("Archives Act 1983 (Cth)")
    other = CitationResult(citation=c, status="not_checked", source="frl",
                           note="The register lists this Act as NotYetInForce (C2099A00001); a person should confirm.")
    none = CitationResult(citation=c, status="not_checked", source="frl", note=frl.NO_MATCH)
    assert cit.match_stage(other)[1] == "listed with another status; a person confirms"
    assert cit.match_stage(none)[1] == "no Commonwealth Act of this name; a person confirms"

