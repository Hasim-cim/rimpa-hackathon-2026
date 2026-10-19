"""The Records list in one pass: each passport's status for filters and search, decided by the same functions as the
passport view ("Since filing") and the dashboard (needs a person), so the three never disagree. No new tables."""

from __future__ import annotations

import re

from . import dashboard, db, recall, view
from .models import Passport, Policy, RecordIndexRow

LABELS = {"disposed": "Disposed", "changed": "Changed since filing", "needs_person": "Needs a person",
          "log_only": "Log only (T0)"}


_CASE = re.compile(r"\bcase (\d{4}/\d{4})\b", re.I)


def _case_id(p: Passport, docs: dict, recs: dict) -> str | None:
    """The case: the filed document's, else the one the prompt names, else its source records' (last resort)."""
    d = docs.get(p.record.final_document) if p.record.final_document else None
    if d is not None and d.case_id:
        return d.case_id
    m = _CASE.search(p.process.prompt or "")
    if m:
        return m.group(1)
    for rid in p.process.source_record_ids:
        r = recs.get(rid)
        if r is not None and r.fields.get("case_id"):
            return str(r.fields["case_id"])
    return None


def rows(conn, policy: Policy | None = None) -> list[RecordIndexRow]:
    docs = {d.id: d for d in db.get_documents(conn)}
    recs = {r.id: r for r in db.get_records(conn)}
    queued = recall.open_queue_ids(conn)
    out: list[RecordIndexRow] = []
    for row in conn.execute("SELECT payload, disposed_at FROM passports ORDER BY seq DESC"):
        p = Passport.model_validate_json(row["payload"])
        disposed = bool(row["disposed_at"])
        changed = False
        if not disposed:
            ch, _ = view._stored(conn, p)
            changed = view._since(conn, p, ch, policy).status == "problem"
        if disposed:
            status = "disposed"
        elif changed:
            status = "changed"
        elif dashboard._attention(p, queued):
            status = "needs_person"
        elif p.business.tier == "T0":
            status = "log_only"
        else:
            status = "filed"
        label = LABELS.get(status, "Filed")   # a filed record is never "Ready to file" (that is the Check page's word)
        out.append(RecordIndexRow(record_id=p.record.id, title=p.record.title, case_id=_case_id(p, docs, recs),
                                  tier=p.business.tier, function=p.business.function, created=p.record.created,
                                  gate=p.business.gate, status=status, status_label=label, changed_since=changed,
                                  document_type=p.business.document_type))
    return out
