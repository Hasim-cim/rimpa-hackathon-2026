"""Model registry and recall query."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal

from . import db
from .models import Passport, RecallItem, RecallResult, Tier

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
    queued = {r["record_id"] for r in conn.execute("SELECT record_id FROM review_queue WHERE status='open'")}
    items: list[RecallItem] = []
    for row in conn.execute("SELECT payload FROM passports WHERE model_returned=? AND tier != 'T0'", (model_id,)):
        p = Passport.model_validate_json(row["payload"])
        items.append(RecallItem(record_id=p.record.id, tier=p.business.tier, function=p.business.function,
                                created=p.record.created, reviewer=p.review.reviewer if p.review else None,
                                queued=p.record.id in queued))
    items.sort(key=lambda i: i.created, reverse=True)
    items.sort(key=lambda i: TIER_RANK[i.tier], reverse=True)
    counts: dict[Tier, int] = {"T0": 0, "T1": 0, "T2": 0, "T3": 0}
    for i in items:
        counts[i.tier] += 1
    return RecallResult(model_id=model_id, entry=entry, counts=counts, items=items)


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
