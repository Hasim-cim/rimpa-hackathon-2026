"""Legislation references checked against the Federal Register of Legislation (Commonwealth law only). No LLM.

Offline by default, from fixtures captured from the register (data/seed/frl_fixtures.json); live behind the same
switch as Crossref (RECORDCHECK_ONLINE). The register is slow and rate-limits, so a live answer is cached per Act
name, a call gives up after TIMEOUT seconds, and any failure reads `not_checked`, never `not_found`: the register
only holds Commonwealth Acts, so "no match" can be state law, a regulation or a misnaming, and is never "possibly
fabricated" (EC-CIT-18, planner override 19 Oct). Evidence: research/live-api-evidence/frl/ and
research/live-data-and-metadata-2026-10-19.md.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from .db import SEED_DIR
from .models import Citation, CitationResult

BASE = "https://api.prod.legislation.gov.au/v1"
TIMEOUT = 8.0
FIXTURE_FILE = SEED_DIR / "frl_fixtures.json"
STATE = re.compile(r"\((NSW|Vic|Qld|WA|SA|Tas|ACT|NT)\)")
_SECTION = re.compile(r"\s+(s|ss|sec|section|sch|pt|part)\.?\s*\d", re.I)

NO_MATCH = ("No Commonwealth Act of this name on the Federal Register of Legislation; a person should confirm "
            "(it may be state legislation, a regulation or misnamed).")
NO_ANSWER = "The Federal Register of Legislation did not respond; a person should confirm the reference."
STATE_NOTE = "State or territory legislation is outside the Federal Register of Legislation. Flagged for a person to confirm."


def normalise(raw: str) -> str:
    """'Social Security Act 1991 (Cth) s 1237AAD.' -> 'Social Security Act 1991'."""
    s = re.sub(r"\((Cth|Commonwealth)\)", "", raw)
    s = _SECTION.split(s)[0]
    s = re.sub(r"[.,;]+$", "", s).strip()
    m = re.search(r"^(.*?\b(Act|Regulations?|Rules?)\b(\s+\d{4})?)", s)
    return " ".join((m.group(1) if m else s).split())


def _has_section(raw: str) -> bool:
    return bool(_SECTION.search(raw))


def _year(name: str) -> int | None:
    m = re.search(r"(\d{4})$", name)
    return int(m.group(1)) if m else None


def _stem(name: str) -> str:
    return re.sub(r"\s+\d{4}$", "", name)


def _load_fixtures() -> dict[str, Any]:
    if not FIXTURE_FILE.exists():
        return {}
    with open(FIXTURE_FILE, encoding="utf-8") as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


def _get(path: str, params: dict[str, str]) -> list[dict[str, Any]]:
    r = httpx.get(f"{BASE}/{path}", params=params, headers={"Accept": "application/json"}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("value", [])


def query(name: str) -> dict[str, Any]:
    """Ask the register: exact name (which also matches former names), then same stem with another year.
    Returns {"exact": [...], "similar": [...]} as the fixtures store it."""
    esc = name.replace("'", "''")
    exact = _get("titles", {"$filter": f"name eq '{esc}'", "$select": "id,name,status,year,statusHistory"})
    similar: list[dict[str, Any]] = []
    if not exact:
        stem = _stem(name).replace("'", "''")
        rows = _get("titles", {"$filter": f"contains(name,'{stem}')", "$select": "id,name,status,year,collection",
                               "$top": "10"})
        # no server-side "Act only" filter (combined filters return 400): keep Acts with the same stem here
        similar = [r for r in rows if r.get("collection") == "Act" and _stem(r.get("name", "")) == _stem(name)]
    return {"exact": exact, "similar": similar}


def _repealed_on(title: dict[str, Any]) -> tuple[str | None, str | None]:
    """(date, repealing Act) from the register's status history; only what the register states."""
    for h in reversed(title.get("statusHistory") or []):
        if h.get("status") == "Repealed":
            by = next((r.get("affectedByTitle", {}).get("name") for r in h.get("reasons") or []
                       if r.get("affect") == "Repeal" and r.get("affectedByTitle")), None)
            return (h.get("start") or "")[:10] or None, by
    return None, None


def judge(c: Citation, name: str, answer: dict[str, Any], source: str) -> CitationResult:
    """Turn the register's answer into a status and a note a records person would accept."""
    section = "; the section is for a person to confirm" if _has_section(c.raw) else ""
    exact = answer.get("exact") or []
    if exact:
        t = exact[0]
        listed = "" if t.get("name") == name else f" It is listed on the register as {t.get('name')}."
        common = dict(citation=c, source=source, matched_title=t.get("name"), matched_year=t.get("year"),
                      doi=None, score=1.0)
        if t.get("status") == "InForce":
            return CitationResult(status="found", note=f"Act found in force on the Federal Register of Legislation "
                                                       f"({t.get('id')}){section}.{listed}", **common)
        if t.get("status") == "Repealed":
            on, by = _repealed_on(t)
            when = f" on {datetime.fromisoformat(on).strftime('%-d %B %Y')}" if on else ""
            how = f" by the {by}" if by else ""
            return CitationResult(status="mismatch", note=f"The Federal Register of Legislation records this Act as "
                                                          f"repealed{when}{how} ({t.get('id')}).{listed}", **common)
        return CitationResult(status="not_checked", note=f"The register lists this Act as {t.get('status')} "
                                                         f"({t.get('id')}); a person should confirm.{listed}", **common)
    similar = answer.get("similar") or []
    if similar:
        t = similar[0]
        return CitationResult(citation=c, status="mismatch", source=source, matched_title=t.get("name"),
                              matched_year=t.get("year"), score=0.9,
                              note=f"The register has {t.get('name')}, not {name}; check the year ({t.get('id')}).")
    return CitationResult(citation=c, status="not_checked", source=source, note=NO_MATCH)


def lookup(c: Citation, *, online: bool, conn=None) -> CitationResult:
    """A legislation reference: fixture, then this database's cache, then (online only) the register."""
    if STATE.search(c.raw):
        return CitationResult(citation=c, status="not_checked", source="none", note=STATE_NOTE)
    name = normalise(c.raw)
    fx = _load_fixtures().get(name)
    if fx is not None:
        return judge(c, name, fx, "fixture")
    key = f"frl:{name.casefold()}"
    if conn is not None:
        row = conn.execute("SELECT payload, fetched_at FROM citation_cache WHERE key=?", (key,)).fetchone()
        if row:   # an earlier live answer: stamped with when it was fetched
            return judge(c, name, json.loads(row["payload"]), "frl").model_copy(
                update={"checked_at": datetime.fromisoformat(row["fetched_at"])})
    if not online:
        return CitationResult(citation=c, status="not_checked", source="none",
                              note="Not in the offline register cache and online lookup is off; a person should confirm.")
    try:
        answer = query(name)
    except Exception:  # timeout, rate limit, 4xx/5xx, bad JSON: never raise, never read as fabricated
        return CitationResult(citation=c, status="not_checked", source="none", note=NO_ANSWER)
    if conn is not None:
        from . import db
        db.upsert(conn, "citation_cache", "key",
                  dict(key=key, payload=json.dumps(answer), fetched_at=datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return judge(c, name, answer, "frl").model_copy(update={"checked_at": datetime.now(timezone.utc)})
