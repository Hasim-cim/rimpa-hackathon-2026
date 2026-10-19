"""Send a draft for review (deck: "Needs a person before filing … Send for review"). The server re-runs the check
itself and keeps the gate's own reasons; a caller's reasons are never trusted. A draft that is ready to file has
nothing to review. For a pasted draft only its title and a hash of its text are kept. No LLM beyond the check itself.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import citations as cit
from . import db, evidence
from . import gate as gatemod
from .hashing import sha256
from .models import Document, DraftReview, Policy


class NothingToReview(ValueError):
    """The gate says ready: file it instead."""


def _next_id(conn) -> str:
    n = conn.execute("SELECT COUNT(*) FROM draft_reviews").fetchone()[0]
    return f"DR-{n + 1:06d}"


def send(conn, doc: Document, document_type: str, requested_by: str, policy: Policy, note: str = "",
         ad_hoc: bool = False, use_llm: bool = False) -> DraftReview:
    """Open a review for a draft the gate does not pass, or return the one already open for it."""
    if not requested_by.strip():
        raise ValueError("A review request needs the name of the person asking.")
    dtype = next((d for d in policy.document_types if d.id == document_type), None)
    if dtype is None:
        raise ValueError(f"unknown document type {document_type!r}")
    body_hash = sha256(doc.body.encode("utf-8")) if ad_hoc else None
    doc_key = f"pasted:{body_hash}" if ad_hoc else doc.id
    row = conn.execute("SELECT payload FROM draft_reviews WHERE doc_key=? AND document_type=? AND status='open'",
                       (doc_key, document_type)).fetchone()
    if row:
        return DraftReview.model_validate_json(row["payload"])
    results = cit.check_document(doc.references, conn=conn)
    assessment = evidence.assess(doc, conn, results, use_llm=use_llm, policy=policy, document_type=document_type)
    result = gatemod.evaluate(assessment, results, None, dtype, dtype.default_tier)
    if result.status == "ready":
        raise NothingToReview(f"Ready to file as {dtype.name}: nothing for a person to review. File it instead.")
    db.lock(conn, db.SEED_LOCK)   # one writer: the id counts the rows
    dr = DraftReview(id=_next_id(conn), document_id=None if ad_hoc else doc.id, title=doc.title, body_hash=body_hash,
                     document_type=document_type, gate=result.status, reasons=[r.text for r in result.reasons],
                     requested_by=requested_by.strip(), note=note, created=datetime.now(timezone.utc))
    conn.execute("INSERT INTO draft_reviews(id, doc_key, document_type, status, created, payload) VALUES (?,?,?,?,?,?)",
                 (dr.id, doc_key, document_type, "open", dr.created.isoformat(), dr.model_dump_json()))
    db.audit(conn, actor=dr.requested_by, action="draft.sent_for_review", subject=dr.id,
             detail=f"{doc_key} as {document_type}; gate {result.status}; {len(dr.reasons)} reasons")
    conn.commit()
    return dr


def open_reviews(conn) -> list[DraftReview]:
    rows = conn.execute("SELECT payload FROM draft_reviews WHERE status='open' ORDER BY created DESC, id DESC").fetchall()
    return [DraftReview.model_validate_json(r["payload"]) for r in rows]


def count_open(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM draft_reviews WHERE status='open'").fetchone()[0]
