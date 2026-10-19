"""Reference extraction and lookup: fixture cache -> Crossref -> OpenAlex; Acts -> Federal Register of Legislation.

Offline by default. Online lookups run only when ``online`` is True, or when it is None and the
RECORDCHECK_ONLINE env var is "true"/"1". Network failures never raise; they return ``not_checked``.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

import httpx

from . import db, frl
from .db import SEED_DIR
from .models import Citation, CitationResult, CitationStatus

FIXTURE_FILE = SEED_DIR / "citation_fixtures.json"
THRESHOLD = 0.85
MAILTO = "hasim.rahman@cimenviro.com"
TIMEOUT = 10.0
LEGISLATION_NOTE = "Legislation is outside Crossref and OpenAlex. Flagged for a person to confirm."
GOVERNMENT_NOTE = ("Government guidance or a web page is outside Crossref and OpenAlex. "
                   "Flagged for a person to confirm.")

_REF_MARKER = re.compile(r"^\s*\[(\d+)\]\s*", re.M)
_YEAR = re.compile(r"\((\d{4})[a-z]?\)")
_LEGISLATION = re.compile(r"\bAct\b|\((?:Cth|NSW|Vic|Qld|WA|SA|Tas|ACT|NT)\)|\bs \d")
_CASE = re.compile(r"\sv\s|\[\d{4}\]\s*[A-Z]")
# a web address other than a DOI, or a government body as author: the indexes hold neither, so an empty answer
# would read "possibly fabricated" for, say, NAA's own guidance. These are flagged for a person instead.
_WEB = re.compile(r"https?://(?!(?:dx\.)?doi\.org/)\S+|\bwww\.\S+", re.I)
_GOV_AUTHOR = re.compile(r"\b(?:National Archives|Archives|Department|Agency|Commission(?:er)?|Office of|Government|"
                         r"Authority|Ombudsman|Parliament|Council|Ministry|Bureau|Tribunal)\b")


def normalise(title: str) -> str:
    """Lowercase, keep alphanumerics, collapse whitespace."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())


def _kind(raw: str) -> str:
    if _CASE.search(raw):
        return "case"
    if _LEGISLATION.search(raw):
        return "legislation"
    year = _YEAR.search(raw)
    if _WEB.search(raw) or (year and _GOV_AUTHOR.search(raw[: year.start()])):
        return "other"
    return "article"


def _parse(n: int, raw: str) -> Citation:
    kind = _kind(raw)
    c = Citation(n=n, raw=raw, kind=kind)  # type: ignore[arg-type]
    m = _YEAR.search(raw)
    if kind != "article" or not m:
        c.title = raw.strip().rstrip(".") if kind != "article" else None
        if m:
            c.year = int(m.group(1))
        return c
    c.year = int(m.group(1))
    c.authors = raw[: m.start()].strip().rstrip(",") or None
    rest = raw[m.end():].lstrip(" .,")
    t = re.match(r"(.+?)(?:\.(?:\s+|$)|$)", rest, re.S)
    if t:
        c.title = t.group(1).strip()
        venue = rest[t.end():].strip().rstrip(".").strip()
        c.venue = venue or None
    return c


def extract_references(text: str) -> list[Citation]:
    """Parse the "References" block (everything after a line reading 'References') by [n] markers."""
    block = text
    h = re.search(r"^\s*References\s*:?\s*$", text, re.M | re.I)
    if h:
        block = text[h.end():]
    marks = list(_REF_MARKER.finditer(block))
    out: list[Citation] = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(block)
        raw = " ".join(block[m.end():end].split())
        if raw:
            out.append(_parse(int(m.group(1)), raw))
    return out


def _load_fixtures() -> dict[str, dict[str, Any]]:
    with open(FIXTURE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if k != "_note"}


def _online(online: bool | None) -> bool:
    if online is not None:
        return online
    return os.environ.get("RECORDCHECK_ONLINE", "").strip().lower() in ("true", "1")


def _venue_differs(cited: str | None, found: str | None) -> bool:
    if not cited or not found:
        return False
    a, b = normalise(cited), normalise(found)
    if not a or not b or a in b or b in a:
        return False
    return SequenceMatcher(None, a, b).ratio() < 0.5


def _judge(c: Citation, title: str | None, year: int | None, venue: str | None,
           doi: str | None, source: str) -> CitationResult:
    score = SequenceMatcher(None, normalise(c.title or ""), normalise(title or "")).ratio() if title else 0.0
    score = round(score, 3)
    base: dict[str, Any] = dict(citation=c, source=source, doi=doi, score=score)
    if score < THRESHOLD:
        return CitationResult(status="not_found", note="No close title match. Possibly fabricated. A person must confirm or remove it.", **base)
    base.update(matched_title=title, matched_year=year, matched_venue=venue)
    year_off = c.year is not None and year is not None and abs(c.year - year) > 1
    venue_off = _venue_differs(c.venue, venue)
    if year_off or venue_off:
        parts = []
        if year_off:
            parts.append(f"published {year}, not {c.year}")
        if venue_off:
            parts.append(f"in {venue}, not {c.venue}")
        return CitationResult(status="mismatch", note=f"Title found, but {' '.join(parts)}.", **base)
    return CitationResult(status="found", note=f"{source.capitalize()} match on title and year.", **base)


def _crossref(c: Citation) -> list[tuple[str | None, int | None, str | None, str | None]]:
    q = " ".join(x for x in (c.title, c.authors) if x)
    r = httpx.get("https://api.crossref.org/works", timeout=TIMEOUT, params={
        "query.bibliographic": q, "rows": 5, "mailto": MAILTO,
        "select": "DOI,title,author,issued,container-title"})
    r.raise_for_status()
    out = []
    for it in r.json().get("message", {}).get("items", []):
        parts = (it.get("issued") or {}).get("date-parts") or [[None]]
        out.append(((it.get("title") or [None])[0], (parts[0] or [None])[0],
                    (it.get("container-title") or [None])[0], it.get("DOI")))
    return out


def _openalex(c: Citation) -> list[tuple[str | None, int | None, str | None, str | None]]:
    params: dict[str, Any] = {"search": c.title or c.raw, "per-page": 5}
    if key := os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = key
    r = httpx.get("https://api.openalex.org/works", timeout=TIMEOUT, params=params)
    r.raise_for_status()
    out = []
    for it in r.json().get("results", []):
        src = ((it.get("primary_location") or {}).get("source") or {}).get("display_name")
        doi = (it.get("doi") or "").removeprefix("https://doi.org/") or None
        out.append((it.get("title"), it.get("publication_year"), src, doi))
    return out


def _best(c: Citation, cands: list[tuple[Any, ...]], source: str) -> CitationResult:
    results = [_judge(c, *cand, source) for cand in cands if cand[0]]
    rank = {"found": 2, "mismatch": 1, "not_found": 0}
    if not results:
        return CitationResult(citation=c, status="not_found", source=source, score=0.0,  # type: ignore[arg-type]
                              note="No results returned. Possibly fabricated. A person must confirm or remove it.")
    return max(results, key=lambda r: (rank[r.status], r.score or 0.0))


def _cache_put(conn: sqlite3.Connection, key: str, res: CitationResult) -> None:
    db.upsert(conn, "citation_cache", "key",
              dict(key=key, payload=res.model_dump_json(), fetched_at=datetime.now(timezone.utc).isoformat()))
    conn.commit()


def lookup(c: Citation, *, online: bool | None = None, conn: sqlite3.Connection | None = None) -> CitationResult:
    if c.kind == "legislation":   # Commonwealth Acts: the Federal Register of Legislation (fixtures, then live)
        return frl.lookup(c, online=_online(online), conn=conn)
    if c.kind == "case":
        return CitationResult(citation=c, status="not_checked", source="none", note=LEGISLATION_NOTE)
    if c.kind == "other":
        return CitationResult(citation=c, status="not_checked", source="none", note=GOVERNMENT_NOTE)
    key = normalise(c.title or "")
    fx = _load_fixtures().get(key)
    if fx:
        if fx.get("matched_title"):
            # the cache stores what the index holds; found vs mismatch depends on how *this* document cited it
            return _judge(c, fx["matched_title"], fx.get("matched_year"), fx.get("matched_venue"), fx.get("doi"), "fixture")
        return CitationResult(citation=c, **fx)
    if conn is not None and key:
        row = conn.execute("SELECT payload FROM citation_cache WHERE key=?", (key,)).fetchone()
        if row:
            return CitationResult.model_validate_json(row["payload"]).model_copy(update={"citation": c})
    if not _online(online) or not key:
        return CitationResult(citation=c, status="not_checked", source="none",
                              note="Not in the offline cache and online lookup is off.")
    best: CitationResult | None = None
    errors: list[str] = []
    for fn, source in ((_crossref, "crossref"), (_openalex, "openalex")):
        try:
            res = _best(c, fn(c), source)
        except Exception as e:  # never raise on network or parse failures
            errors.append(f"{source}: {type(e).__name__}")
            continue
        if res.status in ("found", "mismatch"):
            best = res
            break
        if best is None or (res.score or 0) > (best.score or 0):
            best = res
    if best is None or (errors and best.status == "not_found"):
        return CitationResult(citation=c, status="not_checked", source="none",
                              note="Lookup failed (" + ", ".join(errors) + "). Flagged for a person to confirm.")
    if conn is not None:
        _cache_put(conn, key, best)
    return best


def recheck(results: list[CitationResult], *, conn: sqlite3.Connection | None = None) -> list[CitationResult]:
    """Look up caller-supplied results again from their raw text; a status sent over the API is never trusted."""
    return [lookup(_parse(r.citation.n, r.citation.raw), conn=conn) for r in results]


def check_document(text: str, **kw: Any) -> list[CitationResult]:
    return [lookup(c, **kw) for c in sorted(extract_references(text), key=lambda c: c.n)]


def summary(results: list[CitationResult]) -> dict[str, int]:
    counts: dict[str, int] = {"found": 0, "mismatch": 0, "not_found": 0, "not_checked": 0}
    for r in results:
        counts[r.status] += 1
    return counts


_STAGE_SOURCE = {"crossref": "Crossref", "openalex": "OpenAlex"}


def match_stage(r: CitationResult) -> tuple[str, str]:
    """(stage, strength) for display: which lookup step decided this result, and how strong it is. Presentation only."""
    sim = f", similarity {r.score:.2f}" if r.score is not None else ""
    if r.citation.kind == "legislation" and r.source in ("fixture", "frl"):
        where = "the Federal Register of Legislation"
        stage = "Step 2: exact Act name on the Federal Register of Legislation" + (" (offline copy)" if r.source == "fixture" else "")
        strength = {"found": "found in force on the register", "mismatch": "found, details differ (repealed or another year)",
                    "not_checked": "no Commonwealth Act of this name; a person confirms"}.get(r.status, "a person confirms")
        return stage, strength
    if r.source == "fixture":
        stage, where = "Step 2: lookup in offline cache" + sim, "cached index record"
    elif r.source in _STAGE_SOURCE:
        where = _STAGE_SOURCE[r.source]
        stage = f"Step 3: fuzzy match in {where}" + sim
    else:
        stage, where = "Not looked up", "an index"
    strength = {
        "found": f"found in {where}",
        "mismatch": "found, details differ",
        "not_found": "not found; possibly fabricated",
        "not_checked": "not checked; a person confirms",
    }.get(r.status, "unknown result; a person confirms")
    return stage, strength
