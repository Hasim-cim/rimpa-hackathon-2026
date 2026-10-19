"""Source health: ROT (redundant, obsolete, trivial) and drafts across the records the AI draws on. No LLM."""

from __future__ import annotations

import sqlite3

from . import db
from .evidence import is_evidence
from .hashing import sha256
from .models import Policy, RotLabel, SourceHealth, SourceHealthReport, SourceRecord

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


def health(conn: sqlite3.Connection, policy: Policy | None = None) -> SourceHealthReport:
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
        items.append(SourceHealth(record_id=r.id, title=r.title, system=r.system, labels=labels,
                                  eligible=is_evidence(r), notes=notes))
    items.sort(key=lambda i: (not i.labels, i.record_id))
    counts = {k: sum(k in i.labels for i in items) for k in LABELS}
    return SourceHealthReport(total=len(items), eligible=sum(i.eligible for i in items), counts=counts, items=items)
