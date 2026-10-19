"""FastAPI wrapper over the Record Check engine."""

from __future__ import annotations

import os
import threading
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from recordcheck import citations as cit
from recordcheck import dashboard, db, disposal, evidence, gate, llm, passport, printout, recall, sources
from recordcheck import policy as policymod
from recordcheck import view as vw
from recordcheck.models import (
    AIEvent, Assessment, ChainReport, CitationResult, DashboardReport, DisposalEntry, DisposalItem, Document, GateResult,
    ModelRegistryEntry, Passport, PassportView, RecordSummary, Policy, RecallResult, ReliabilityReport, Review, SectorPreset, SourceHealthReport, SourceRecallResult,
    SourceRecord, Tier,
)


def _open():
    # SQLite, or Postgres when DATABASE_URL is set; either connection is safe across FastAPI's worker threads
    return db.open_db()


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
    document_type: str | None = None         # with one, the response carries the filing gate before review


class CheckResponse(BaseModel):
    citations: list[CitationResult]
    assessment: Assessment
    gate: GateResult | None = None
    relied_on: list[str] = []                # records the claims rest on: what /passport will file as the sources


class PassportRequest(BaseModel):
    event: AIEvent
    review: Review | None = None
    tier: Tier | None = None
    citations: list[CitationResult] = []
    assessment: Assessment | None = None
    document_type: str | None = None         # policy document type; without one the strictest default bar applies


class Mark(BaseModel):
    status: Literal["withdrawn", "faulty"]
    effective_from: date
    reason: str
    by: str


class RecallRequest(BaseModel):
    model_id: str
    mark: Mark | None = None


class SupersedeMark(BaseModel):
    superseded_by: str | None = None
    reason: str
    by: str


class SourceRecallRequest(BaseModel):
    record_id: str
    mark: SupersedeMark | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "mode": mode(),
            "ai_for_pasted_text": False, "ai_for_trial_documents": mode() == "demo" and llm.available()}


def mode() -> str:
    """The deployment's mode, from the environment only, never from a caller: 'demo' (the presentation URL) or 'app'
    (the public working app, the default)."""
    return "demo" if os.environ.get("RECORDCHECK_MODE", "app").strip().lower() == "demo" else "app"


def _use_llm(trial_document: bool) -> bool:
    """AI claim splitting only in demo mode and only on the trial documents. Pasted text never goes to the model, in
    either mode, so the cost is bounded and nothing a visitor pastes leaves the server for the AI."""
    return mode() == "demo" and trial_document and llm.available()


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
        pol = policymod.load()
        dtype = policymod.doc_type(pol, req.document_type) if req.document_type else None
        if req.document_type and dtype is None:
            raise HTTPException(422, f"unknown document type {req.document_type!r}")
        results = cit.check_document(doc.references, conn=conn)
        assessment = evidence.assess(doc, conn, results, policy=pol, document_type=req.document_type,
                                     use_llm=_use_llm(trial_document=bool(req.document_id)))
        result = gate.evaluate(assessment, results, None, dtype, dtype.default_tier) if dtype else None
        return CheckResponse(citations=results, assessment=assessment, gate=result,
                             relied_on=evidence.relied_on(assessment, conn, pol, req.document_type))


@app.get("/documents", response_model=list[Document])
def documents() -> list[Document]:
    with lock:
        return db.get_documents(conn)


@app.get("/records", response_model=list[SourceRecord])
def records() -> list[SourceRecord]:
    with lock:
        return db.get_records(conn)


class LevelOut(BaseModel):
    id: str                                  # strict | standard | light
    name: str
    use_for: str
    summary: str                             # the bar in one plain sentence (policy.describe)
    checks: list[str]
    quality: dict


class TypeLevel(BaseModel):
    id: str
    name: str
    level: str                               # strict | standard | light | custom
    summary: str


class LevelsResponse(BaseModel):
    levels: list[LevelOut]
    document_types: list[TypeLevel]


@app.get("/policy/levels", response_model=LevelsResponse)
def policy_levels() -> LevelsResponse:
    """The strictness picker: the three named bars, and which one each document type is at now ('custom' = none)."""
    from recordcheck.models import DocumentType
    pol = policymod.load()
    levels = [LevelOut(id=lv.id, name=lv.name, use_for=lv.use_for, checks=list(lv.checks),
                       quality=lv.quality.model_dump(),
                       summary=policymod.describe(DocumentType(id=lv.id, name=lv.name, checks=lv.checks, quality=lv.quality)))
              for lv in policymod.LEVELS.values()]
    types = [TypeLevel(id=d.id, name=d.name, level=policymod.level_of(d) or "custom", summary=policymod.describe(d))
             for d in pol.document_types]
    return LevelsResponse(levels=levels, document_types=types)


@app.get("/policy", response_model=Policy)
def get_policy() -> Policy:
    return policymod.load()


@app.post("/passport", response_model=Passport)
def issue_passport(req: PassportRequest) -> Passport:
    with lock:
        pol = policymod.load()
        tier = req.tier or passport.classify(req.event, pol.tier_rules)
        dtype = policymod.doc_type(pol, req.document_type) if req.document_type else None
        if req.document_type and dtype is None:
            raise HTTPException(422, f"unknown document type {req.document_type!r}")
        if req.tier is None and dtype:  # as the console does: the type's default tier is the floor, escalations raise it
            tier = max(tier, dtype.default_tier, key=lambda t: passport.TIER_ORDER[t])
        # never trust a status or weight sent by the caller: look the citations up and re-weigh the claims here
        citations = cit.recheck(req.citations, conn=conn)
        try:
            assessment = evidence.reassess(req.assessment, conn, citations, policy=pol,
                                           document_type=req.document_type) if req.assessment else None
            event = req.event
            if assessment is not None:  # the sources are what the evidence rests on, never what the caller claims
                event = event.model_copy(update={"source_record_ids": evidence.relied_on(
                    assessment, conn, pol, req.document_type)})
            # build runs the filing gate itself, so it cannot be skipped by leaving out document_type
            return passport.build(event, tier=tier, assessment=assessment, citations=citations,
                                  review=req.review, conn=conn, rules=pol.tier_rules,
                                  document_type=req.document_type, policy=pol)
        except passport.GateBlocked as e:
            reasons = [r.text for r in e.result.reasons] if e.result else [str(e)]
            raise HTTPException(409, {"gate": "blocked", "reasons": reasons})
        except ValueError as e:  # tier below the rules, self-review, duplicate record, inconsistent assessment
            raise HTTPException(422, str(e))


@app.get("/passport/{record_id:path}.pdf", response_class=Response,
         responses={200: {"content": {"application/pdf": {}}}})
def get_passport_pdf(record_id: str) -> Response:
    """One-page printed passport. Registered before the JSON route, whose path parameter would swallow ".pdf"."""
    with lock:
        p = db.get_passport(conn, record_id)
        chain = passport.verify_chain(conn) if p else None
    if p is None:
        raise HTTPException(404, f"unknown record: {record_id}")
    return Response(printout.passport_pdf(p, chain), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{printout.filename(p)}"'})


@app.get("/passport/{record_id:path}/summary", response_model=RecordSummary)
def get_passport_summary(record_id: str) -> RecordSummary:
    """Headline, status, the four checks and the policy line: what a person reads first."""
    with lock:
        s = vw.summary(conn, record_id, policymod.load())
    if s is None:
        raise HTTPException(404, f"unknown record: {record_id}")
    return s


@app.get("/passport/{record_id:path}/view", response_model=PassportView)
def get_passport_view(record_id: str) -> PassportView:
    """The passport and the checks done on it at issue, plus the live 'Since filing' check."""
    with lock:
        v = passport.view(conn, record_id, policymod.load())
    if v is None:
        raise HTTPException(404, f"unknown record: {record_id}")
    return v


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


@app.post("/recall/record", response_model=SourceRecallResult)
def do_source_recall(req: SourceRecallRequest) -> SourceRecallResult:
    with lock:
        try:
            if req.mark:
                m = req.mark
                recall.mark_superseded(conn, req.record_id, m.superseded_by, m.reason, m.by)
            return recall.recall_by_record(conn, req.record_id)
        except KeyError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            raise HTTPException(422, str(e))


@app.get("/sources/health", response_model=SourceHealthReport)
def source_health() -> SourceHealthReport:
    with lock:
        return sources.health(conn, policymod.load())


@app.get("/sources/reliability", response_model=ReliabilityReport)
def source_reliability() -> ReliabilityReport:
    with lock:
        return sources.reliability(conn, policymod.load())


@app.get("/dashboard", response_model=DashboardReport)
def get_dashboard() -> DashboardReport:
    """Read-only information-manager dashboard: KPIs, model signals, recent passports, sources, disposal."""
    with lock:
        return dashboard.report(conn, policymod.load())


@app.get("/chain/verify", response_model=ChainReport)
def chain_verify() -> ChainReport:
    with lock:
        return passport.verify_chain(conn)


# ---------- console reads and IM actions (the web console's tabs) ----------

class QueueRequest(BaseModel):
    record_ids: list[str]
    reason: str
    by: str


class DisposalRequest(BaseModel):
    record_ids: list[str]
    approved_by: str
    reason: str
    as_of: date | None = None


class PolicySave(BaseModel):
    policy: Policy
    by: str


class FromPreset(BaseModel):
    preset_id: str
    organisation: str
    by: str


class SuggestRequest(BaseModel):
    description: str


@app.get("/passports", response_model=list[Passport])
def passports() -> list[Passport]:
    with lock:
        return db.get_passports(conn)[::-1]  # latest first


@app.get("/models", response_model=list[ModelRegistryEntry])
def models() -> list[ModelRegistryEntry]:
    with lock:
        return db.get_model_registry(conn)


@app.post("/recall/queue")
def queue(req: QueueRequest) -> dict:
    with lock:
        return {"queued": recall.queue_for_review(conn, req.record_ids, by=req.by, reason=req.reason)}


@app.get("/audit")
def audit(action_prefix: str = "", limit: int = 20) -> list[dict]:
    with lock:
        rows = conn.execute("SELECT at, actor, action, subject, detail FROM audit_log WHERE action LIKE ? "
                            "ORDER BY id DESC LIMIT ?", (f"{action_prefix}%", min(limit, 200))).fetchall()
    return [dict(r) for r in rows]


@app.get("/disposal/due", response_model=list[DisposalItem])
def disposal_due(as_of: date | None = None) -> list[DisposalItem]:
    with lock:
        return disposal.due_for_disposal(conn, as_of=as_of, rules=policymod.load().tier_rules)


@app.post("/disposal/approve", response_model=list[DisposalEntry])
def disposal_approve(req: DisposalRequest) -> list[DisposalEntry]:
    with lock:
        try:
            return disposal.approve_disposal(conn, req.record_ids, approved_by=req.approved_by, reason=req.reason,
                                             rules=policymod.load().tier_rules, as_of=req.as_of)
        except ValueError as e:  # blank approver
            raise HTTPException(422, str(e))


@app.get("/disposal/register", response_model=list[DisposalEntry])
def disposal_register() -> list[DisposalEntry]:
    with lock:
        return disposal.register(conn)


@app.get("/presets", response_model=list[SectorPreset])
def presets() -> list[SectorPreset]:
    return policymod.load_presets()


@app.put("/policy", response_model=Policy)
def save_policy(req: PolicySave) -> Policy:
    if not req.policy.document_types:
        raise HTTPException(422, "a policy needs at least one document type")
    with lock:
        req.policy.version = policymod.load().version  # save() bumps it; versions only count up
        return policymod.save(req.policy, by=req.by.strip() or "Information manager", conn=conn)


@app.post("/policy/preset", response_model=Policy)
def policy_from_preset(req: FromPreset) -> Policy:
    """Start from a preset, or reset to the current sector's defaults. Replaces the active policy."""
    try:
        preset = policymod.get_preset(req.preset_id)
    except KeyError as e:
        raise HTTPException(404, str(e))
    by = req.by.strip() or "Information manager"
    with lock:
        new = policymod.from_preset(preset, req.organisation.strip() or policymod.DEFAULT_ORG, by=by)
        new.version = policymod.load().version
        return policymod.save(new, by=by, conn=conn)


@app.post("/policy/suggest", response_model=policymod.Suggestion | None)
def suggest_policy(req: SuggestRequest) -> policymod.Suggestion | None:
    return policymod.suggest(req.description)  # None when the LLM is off; the IM picks a preset instead
