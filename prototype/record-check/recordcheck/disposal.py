"""Disposal of T0 log entries. Content is destroyed; the passport row, hash and chain position are kept as a stub."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone

from . import db
from .models import DisposalEntry, DisposalItem, Passport, TierRules

DESTROYED = "[destroyed]"
HOLD_REASON = "Model under recall; disposal blocked until the recall closes"
HELD_STATUSES = ("faulty", "withdrawn")


def _rules(rules: TierRules | None) -> TierRules:
    if rules is not None:
        return rules
    from .passport import load_tier_rules
    return load_tier_rules()


def due_for_disposal(conn: sqlite3.Connection, *, as_of: date | None = None,
                     rules: TierRules | None = None) -> list[DisposalItem]:
    rules = _rules(rules)
    as_of = as_of or date.today()
    held = {e.model_id for e in db.get_model_registry(conn) if e.status in HELD_STATUSES}
    items: list[DisposalItem] = []
    q = ("SELECT p.record_id, p.tier, p.model_returned, p.created, COALESCE(e.app_id, '') AS app_id "
         "FROM passports p LEFT JOIN ai_events e ON e.id = p.event_id WHERE p.disposed_at IS NULL")
    for r in conn.execute(q):
        days = rules.retention_days.get(r["tier"])
        if days is None:
            continue
        created = datetime.fromisoformat(r["created"])
        due = created.date() + timedelta(days=days)
        if due > as_of:
            continue
        on_hold = r["model_returned"] in held
        late = (as_of - due).days
        reason = (f"Held: model {r['model_returned']} under recall" if on_hold else
                  f"{r['tier']} log, " + ("due today" if late == 0 else f"{late} day{'s' if late != 1 else ''} past retention"))
        items.append(DisposalItem(record_id=r["record_id"], tier=r["tier"], app_id=r["app_id"],
                                  model_returned=r["model_returned"], created=created, due=due,
                                  on_hold=on_hold, hold_reason=HOLD_REASON if on_hold else "", reason=reason))
    items.sort(key=lambda i: (i.due, i.record_id))
    return items


def pending_count(conn: sqlite3.Connection, *, as_of: date | None = None, rules: TierRules | None = None) -> int:
    return sum(1 for i in due_for_disposal(conn, as_of=as_of, rules=rules) if not i.on_hold)


def _stub(p: Passport) -> Passport:
    """Same shape, every content field destroyed. record.content_hash and integrity stay as they were."""
    d = p.model_dump(mode="json")
    d["record"].update(title=DESTROYED, final_document=None)
    d["agent"].update(person=DESTROYED, ai_system=DESTROYED, model_requested=DESTROYED, provider=DESTROYED)
    d["business"].update(function=DESTROYED, tier_reason=DESTROYED, disposal=DESTROYED)
    d["process"].update(prompt=DESTROYED, system_prompt=None, source_record_ids=[], citation_summary={},
                        evidence_summary={}, tool_calls=[])
    d["review"] = None
    d["paradata"].update(use_register_id=DESTROYED, impact_assessment_ref=None)
    return Passport.model_validate(d)


def approve_disposal(conn: sqlite3.Connection, record_ids: list[str], *, approved_by: str, reason: str,
                     rules: TierRules | None = None, as_of: date | None = None) -> list[DisposalEntry]:
    if not approved_by.strip():
        raise ValueError("Disposal needs the name of the person approving it.")
    rules = _rules(rules)
    eligible = {i.record_id: i for i in due_for_disposal(conn, as_of=as_of, rules=rules) if not i.on_hold}
    now = datetime.now(timezone.utc)
    entries: list[DisposalEntry] = []
    for rid in record_ids:
        item = eligible.get(rid)
        if item is None:
            continue
        p = db.get_passport(conn, rid)
        if p is None:
            continue
        entry = DisposalEntry(record_id=rid, tier=item.tier, created=item.created, disposed_at=now,
                              approved_by=approved_by, authority=rules.disposal_authority, reason=reason,
                              hash_retained=p.integrity.hash)
        conn.execute("INSERT INTO disposal_register(record_id,tier,created,disposed_at,approved_by,authority,reason,hash_retained) "
                     "VALUES (?,?,?,?,?,?,?,?)",
                     (rid, entry.tier, item.created.isoformat(), now.isoformat(), approved_by,
                      entry.authority, reason, entry.hash_retained))
        conn.execute("DELETE FROM passport_checks WHERE record_id=?", (rid,))   # the detail goes with the content
        conn.execute("UPDATE passports SET disposed_at=?, payload=? WHERE record_id=?",
                     (now.isoformat(), _stub(p).model_dump_json(), rid))
        # the interaction itself lives in ai_events; destroying the passport alone would not be disposal
        ev = db.get_event(conn, p.event_id)
        if ev is not None:
            scrubbed = ev.model_copy(update={
                "user": "[destroyed]", "prompt": "[destroyed]", "system_prompt": None, "output": "[destroyed]",
                "source_record_ids": [], "tool_calls": [], "function": "[destroyed]",
            })
            conn.execute("UPDATE ai_events SET payload=? WHERE id=?", (scrubbed.model_dump_json(), ev.id))
        db.audit(conn, actor=approved_by, action="disposal.approved", subject=rid,
                 detail=f"tier {entry.tier}; authority {entry.authority}; hash retained {entry.hash_retained[:12]}; {reason}")
        entries.append(entry)
    conn.commit()
    return entries


def register(conn: sqlite3.Connection) -> list[DisposalEntry]:
    rows = conn.execute("SELECT * FROM disposal_register ORDER BY disposed_at DESC, record_id").fetchall()
    return [DisposalEntry(**{k: r[k] for k in r.keys()}) for r in rows]
