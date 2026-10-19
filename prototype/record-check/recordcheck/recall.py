"""Model registry, recall by model, and recall by source record."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal

from . import db
from .models import Passport, RecallItem, RecallResult, SourceRecallResult, Tier, naive_utc

TIER_RANK = {"T3": 3, "T2": 2, "T1": 1, "T0": 0}


def mark_model(conn: sqlite3.Connection, model_id: str, status: Literal["withdrawn", "faulty"],
               effective_from: date, reason: str, by: str) -> None:
    cur = conn.execute(
        "UPDATE model_registry SET status=?, effective_from=?, reason=?, marked_by=? WHERE model_id=?",
        (status, effective_from.isoformat(), reason, by, model_id))
    if cur.rowcount == 0:
        raise KeyError(f"unknown model: {model_id}")
    db.audit(conn, actor=by, action=f"model.marked_{status}", subject=model_id,
             detail=f"effective from {effective_from.isoformat()}: {reason}")
    conn.commit()


def recall(conn: sqlite3.Connection, model_id: str) -> RecallResult:
    entry = next((e for e in db.get_model_registry(conn) if e.model_id == model_id), None)
    if entry is None:
        raise KeyError(f"unknown model: {model_id}")
    items, counts = _items(conn, (Passport.model_validate_json(row["payload"]) for row in conn.execute(
        "SELECT payload FROM passports WHERE model_returned=? AND tier != 'T0'", (model_id,))))
    return RecallResult(model_id=model_id, entry=entry, counts=counts, items=items)


def open_queue_ids(conn: sqlite3.Connection) -> set[str]:
    """Record ids with an open entry in the review queue."""
    return {r["record_id"] for r in conn.execute("SELECT record_id FROM review_queue WHERE status='open'")}


def _items(conn: sqlite3.Connection, passports) -> tuple[list[RecallItem], dict[Tier, int]]:
    """Recall items, tier descending then date descending, with per-tier counts."""
    queued = open_queue_ids(conn)
    items = [RecallItem(record_id=p.record.id, tier=p.business.tier, function=p.business.function,
                        created=p.record.created, reviewer=p.review.reviewer if p.review else None,
                        queued=p.record.id in queued) for p in passports]
    items.sort(key=lambda i: naive_utc(i.created), reverse=True)   # older DBs hold some aware times
    items.sort(key=lambda i: TIER_RANK[i.tier], reverse=True)
    counts: dict[Tier, int] = {"T0": 0, "T1": 0, "T2": 0, "T3": 0}
    for i in items:
        counts[i.tier] += 1
    return items, counts


def mark_superseded(conn: sqlite3.Connection, record_id: str, superseded_by: str | None, reason: str, by: str) -> None:
    """The source changed (a new policy version, a corrected notice). It stops counting as evidence at once."""
    if not by.strip():
        raise ValueError("a person must be named for marking a record superseded")
    rec = db.get_record(conn, record_id)
    if rec is None:
        raise KeyError(f"unknown record: {record_id}")
    if superseded_by is not None and (superseded_by == record_id or db.get_record(conn, superseded_by) is None):
        raise ValueError(f"superseded_by must name another existing record, not {superseded_by!r}")
    rec = rec.model_copy(update={"status": "superseded", "superseded_by": superseded_by})
    conn.execute("UPDATE records SET status=?, payload=? WHERE id=?", (rec.status, rec.model_dump_json(), record_id))
    db.audit(conn, actor=by, action="record.marked_superseded", subject=record_id,
             detail=(f"superseded by {superseded_by}: " if superseded_by else "") + reason)
    conn.commit()


def recall_by_record(conn: sqlite3.Connection, record_id: str) -> SourceRecallResult:
    """Every T1–T3 output whose passport lists this record as a source. Disposed rows list no sources."""
    rec = db.get_record(conn, record_id)
    if rec is None:
        raise KeyError(f"unknown record: {record_id}")
    rows = conn.execute("SELECT payload FROM passports WHERE tier != 'T0' AND disposed_at IS NULL")
    items, counts = _items(conn, (p for p in (Passport.model_validate_json(r["payload"]) for r in rows)
                                  if record_id in p.process.source_record_ids))
    return SourceRecallResult(record_id=record_id, record=rec, counts=counts, items=items)


def queue_for_review(conn: sqlite3.Connection, record_ids: list[str], by: str, reason: str) -> int:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    open_ids = {r["record_id"] for r in conn.execute("SELECT record_id FROM review_queue WHERE status='open'")}
    n = 0
    for rid in record_ids:
        if rid in open_ids:
            continue
        open_ids.add(rid)
        conn.execute("INSERT INTO review_queue(record_id, reason, queued_by, queued_at, status) VALUES (?,?,?,?, 'open')",
                     (rid, reason, by, now))
        db.audit(conn, actor=by, action="review.queued", subject=rid, detail=reason, at=now)
        n += 1
    conn.commit()
    return n
