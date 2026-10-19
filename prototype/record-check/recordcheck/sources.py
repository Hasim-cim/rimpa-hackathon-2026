"""Source health: ROT (redundant, obsolete, trivial) and drafts across the records the AI draws on. No LLM."""

from __future__ import annotations

import sqlite3
from datetime import date

from . import db
from .evidence import is_evidence, why_not_evidence
from .hashing import sha256
from .models import (Passport, Policy, ReliabilityDrag, ReliabilityReport, RotLabel, SourceHealth,
                     SourceHealthReport, SourceRecord)

LABELS: tuple[RotLabel, ...] = ("redundant", "obsolete", "trivial", "draft")


def _fingerprint(rec: SourceRecord) -> str:
    # case and spacing differences do not make a copy a different record
    return sha256(" ".join(rec.content.split()).casefold())


def _as_judged(records: list[SourceRecord], policy: Policy | None) -> list[SourceRecord]:
    # same rule as evidence.assess: a system the information manager has not listed is not evidence
    if policy is None:
        return records
    return [r if (r.system in policy.authoritative_systems or not r.authoritative)
            else r.model_copy(update={"authoritative": False}) for r in records]


def health(conn: sqlite3.Connection, policy: Policy | None = None, as_of: date | None = None) -> SourceHealthReport:
    as_of = as_of or date.today()
    records = _as_judged(db.get_records(conn), policy)
    groups: dict[str, list[SourceRecord]] = {}
    for r in records:
        groups.setdefault(_fingerprint(r), []).append(r)
    # in a group of copies, the one that counts as evidence (then the earliest) is the original
    original = {fp: min(g, key=lambda r: (not is_evidence(r), r.created, r.id)).id
                for fp, g in groups.items() if len(g) > 1}

    items: list[SourceHealth] = []
    for r in records:
        labels: list[RotLabel] = []
        notes: list[str] = []
        fp = _fingerprint(r)
        if fp in original and original[fp] != r.id:
            labels.append("redundant")
            notes.append(f"same content as {original[fp]}")
        if r.status in ("superseded", "disposed"):
            labels.append("obsolete")
            notes.append(f"superseded by {r.superseded_by}" if r.superseded_by else r.status)
        if not r.authoritative:
            labels.append("trivial")
            notes.append(f"'{r.system}' is not an authoritative system")
        if r.status == "draft":
            labels.append("draft")
            notes.append("a draft, not the approved version")
        overdue = bool(r.review_due and r.review_due < as_of and r.status == "current")
        if overdue:
            notes.append(f"overdue for review since {r.review_due.isoformat()}")
        items.append(SourceHealth(record_id=r.id, title=r.title, system=r.system, labels=labels,
                                  eligible=is_evidence(r), notes=notes, purpose=r.purpose, not_for=list(r.not_for),
                                  review_due=r.review_due, overdue=overdue))
    items.sort(key=lambda i: (not (i.labels or i.overdue), i.record_id))
    counts = {k: sum(k in i.labels for i in items) for k in LABELS}
    return SourceHealthReport(total=len(items), eligible=sum(i.eligible for i in items), counts=counts, items=items,
                              overdue=sum(i.overdue for i in items))


def reliability(conn: sqlite3.Connection, policy: Policy | None = None, top: int = 5,
                as_of: date | None = None) -> ReliabilityReport:
    """Share of retained AI outputs (T1-T3, not disposed) whose source records all still count as evidence, plus
    the sources pulling it down. Changes the moment a source is superseded, before anyone re-reads the outputs."""
    recs = {r.id: r for r in _as_judged(db.get_records(conn), policy)}
    h = {i.record_id: i for i in health(conn, policy, as_of).items}
    labels = {k: i.labels for k, i in h.items()}
    stale: dict[str, int] = {}
    rows = conn.execute("SELECT payload FROM passports WHERE tier != 'T0' AND disposed_at IS NULL")
    outputs = [Passport.model_validate_json(r["payload"]) for r in rows]
    with_sources = ok = checked = supported = 0
    bad: dict[str, int] = {}
    for p in outputs:
        ev = p.process.evidence_summary
        total = sum(ev.values())
        if total:
            checked += 1
            supported += ev.get("supported", 0) == total
        ids = list(dict.fromkeys(p.process.source_record_ids))
        if not ids:
            continue
        with_sources += 1
        for i in ids:
            if i in h and h[i].overdue:
                stale[i] = stale.get(i, 0) + 1
        failing = [i for i in ids if i not in recs or not is_evidence(recs[i])]
        ok += not failing
        for i in failing:
            bad[i] = bad.get(i, 0) + 1
    drag = [ReliabilityDrag(record_id=i, title=recs[i].title if i in recs else "(not in the records system)",
                            labels=labels.get(i, []), outputs=n,
                            why=why_not_evidence(recs[i]) if i in recs else "not found in the records system")
            for i, n in sorted(bad.items(), key=lambda kv: (-kv[1], kv[0]))[:top]]
    overdue = [ReliabilityDrag(record_id=i, title=recs[i].title, labels=labels.get(i, []), outputs=n,
                               why=f"overdue for review since {recs[i].review_due.isoformat()}")
               for i, n in sorted(stale.items(), key=lambda kv: (-kv[1], kv[0]))[:top]]
    return ReliabilityReport(retained=len(outputs), with_sources=with_sources, sources_ok=ok,
                             share=(ok / with_sources) if with_sources else None,
                             claim_checked=checked, claim_supported=supported, drag=drag, overdue=overdue)

