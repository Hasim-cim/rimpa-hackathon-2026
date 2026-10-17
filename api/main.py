"""FastAPI wrapper over the Record Check engine."""

from __future__ import annotations

import sqlite3
import threading
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from recordcheck import citations as cit
from recordcheck import db, evidence, gate as gatemod, passport, recall
from recordcheck import policy as policymod
from recordcheck.models import (
    AIEvent, Assessment, ChainReport, CitationResult, Document, Passport, RecallResult, Review, Tier,
)


def _open() -> sqlite3.Connection:
    # db.connect() does not allow cross-thread use; FastAPI runs sync endpoints in a thread pool.
    db.open_db().close()
    conn = sqlite3.connect(db.db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


conn = _open()
lock = threading.Lock()
rules = passport.load_tier_rules()

app = FastAPI(title="Record Check API", version="0.1.0")


class CheckRequest(BaseModel):
    document_id: str | None = None
    title: str | None = None
    body: str | None = None
    references: str = ""
    case_id: str | None = None


class CheckResponse(BaseModel):
    citations: list[CitationResult]
    assessment: Assessment


class PassportRequest(BaseModel):
    event: AIEvent
    review: Review | None = None
    tier: Tier | None = None
    citations: list[CitationResult] = []
    assessment: Assessment | None = None
    document_type: str | None = None         # policy document type; when given, the filing gate is enforced here


class Mark(BaseModel):
    status: Literal["withdrawn", "faulty"]
    effective_from: date
    reason: str
    by: str


class RecallRequest(BaseModel):
    model_id: str
    mark: Mark | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat(timespec="seconds")}


@app.post("/check", response_model=CheckResponse)
def check(req: CheckRequest) -> CheckResponse:
    with lock:
        if req.document_id:
            doc = db.get_document(conn, req.document_id)
            if doc is None:
                raise HTTPException(404, f"unknown document: {req.document_id}")
        elif req.body is not None:
            doc = Document(id="ADHOC", title=req.title or "Untitled", case_id=req.case_id,
                           body=req.body, references=req.references)
        else:
            raise HTTPException(422, "provide document_id, or title and body")
        results = cit.check_document(doc.references, conn=conn)
        return CheckResponse(citations=results, assessment=evidence.assess(doc, conn, results))


@app.post("/passport", response_model=Passport)
def issue_passport(req: PassportRequest) -> Passport:
    with lock:
        pol = policymod.load()
        tier = req.tier or passport.classify(req.event, pol.tier_rules)
        gate_status = None
        if req.document_type:
            dtype = policymod.doc_type(pol, req.document_type)
            if dtype is None:
                raise HTTPException(422, f"unknown document type {req.document_type!r}")
            result = gatemod.evaluate(req.assessment, req.citations, req.review, dtype, tier)
            gate_status = result.status
            if result.status == "blocked":
                raise HTTPException(409, {"gate": "blocked", "reasons": [r.text for r in result.reasons]})
        try:
            return passport.build(req.event, tier=tier, assessment=req.assessment, citations=req.citations,
                                  review=req.review, conn=conn, rules=pol.tier_rules,
                                  document_type=req.document_type, gate=gate_status, policy=pol)
        except passport.GateBlocked as e:
            raise HTTPException(409, str(e))


@app.get("/passport/{record_id:path}", response_model=Passport)
def get_passport(record_id: str) -> Passport:
    with lock:
        p = db.get_passport(conn, record_id)
    if p is None:
        raise HTTPException(404, f"unknown record: {record_id}")
    return p


@app.post("/recall", response_model=RecallResult)
def do_recall(req: RecallRequest) -> RecallResult:
    with lock:
        try:
            if req.mark:
                m = req.mark
                recall.mark_model(conn, req.model_id, m.status, m.effective_from, m.reason, m.by)
            return recall.recall(conn, req.model_id)
        except KeyError as e:
            raise HTTPException(404, str(e))


@app.get("/chain/verify", response_model=ChainReport)
def chain_verify() -> ChainReport:
    with lock:
        return passport.verify_chain(conn)
