"""Shared data models. This file is the contract between modules; change shapes here first."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

def naive_utc(dt: datetime) -> datetime:
    """One time convention for records: naive UTC, as the seed stores them. An aware time (an ISO string ending in Z,
    as the web sends) is converted to UTC and its offset dropped, so passports always sort and compare together."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


Tier = Literal["T0", "T1", "T2", "T3"]
Weight = Literal["supported", "weak", "unsupported", "contradicted"]
CitationStatus = Literal["found", "mismatch", "not_found", "not_checked"]
Author = Literal["ai", "human"]
RecordStatus = Literal["current", "draft", "superseded", "disposed"]   # only current records count as evidence
RotLabel = Literal["redundant", "obsolete", "trivial", "draft"]
ModelStatus = Literal["active", "withdrawn", "faulty"]


# ---------- authoritative records ----------

class SourceRecord(BaseModel):
    id: str                                  # e.g. REC-2026/004811
    title: str
    system: str                              # e.g. "Payroll records system"
    authoritative: bool = True
    status: RecordStatus = "current"
    superseded_by: str | None = None
    created: date
    created_by: str
    reviewed_by: str | None = None
    content: str                             # plain text the linking rules search
    fields: dict[str, Any] = Field(default_factory=dict)   # structured facts: case_id, amount_weekly, occupants...
    hash: str | None = None
    purpose: str = ""                        # intended use in plain words, e.g. "Discussion paper; not policy"
    not_for: list[str] = Field(default_factory=list)       # policy document-type ids it must not be relied on for
    review_due: date | None = None           # when the owner should next confirm it is still right


# ---------- documents and claims ----------

class Claim(BaseModel):
    id: str
    text: str
    author: Author
    position: int                            # order in the document
    citation_refs: list[int] = Field(default_factory=list)   # [n] markers this sentence relies on


class Document(BaseModel):
    id: str
    title: str
    case_id: str | None = None
    body: str                                # the prose, with [n] markers
    references: str = ""                     # the "References" block, raw
    default_author: Author = "ai"
    claims: list[Claim] = Field(default_factory=list)       # pre-split claims (seed); empty → split at runtime


class ClaimLink(BaseModel):
    claim_id: str
    record_id: str
    rule: str                                # which linking rule matched, e.g. "case_id+amount"
    note: str = ""


class Verdict(BaseModel):
    claim_id: str
    weight: Weight
    links: list[ClaimLink] = Field(default_factory=list)
    reason: str                              # one sentence a records person would accept


class Assessment(BaseModel):
    document_id: str
    claims: list[Claim]
    verdicts: list[Verdict]
    assessed_at: datetime
    method: str                              # "seed" | "sentence-split" | "llm:<model_returned>"


# ---------- citations ----------

class Citation(BaseModel):
    n: int
    raw: str
    title: str | None = None
    authors: str | None = None
    year: int | None = None
    venue: str | None = None
    kind: Literal["article", "legislation", "case", "other"] = "article"


class CitationResult(BaseModel):
    citation: Citation
    status: CitationStatus
    source: Literal["fixture", "crossref", "openalex", "frl", "none"] = "none"   # frl: Federal Register of Legislation
    doi: str | None = None
    matched_title: str | None = None
    matched_year: int | None = None
    matched_venue: str | None = None
    score: float | None = None
    note: str = ""
    checked_at: datetime | None = None       # when a live lookup answered (UTC); None = offline copy or not looked up


# ---------- AI events and passports ----------

class ToolCall(BaseModel):
    name: str
    side_effect: bool = False
    summary: str = ""


class AIEvent(BaseModel):
    id: str
    app_id: str                              # registered app or agent, e.g. "agency-assistant"
    user: str
    created: datetime
    prompt: str
    system_prompt: str | None = None
    output: str
    model_requested: str
    model_returned: str
    provider: str
    source_record_ids: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    exported_to_document: str | None = None  # document id, if the output went into one
    decision_flag: bool = False              # informed a decision about a person, case or money
    function: str = ""                       # business function, e.g. "Debt waiver assessment"


class Review(BaseModel):
    reviewer: str
    decision: Literal["approved", "approved_with_edits", "rejected"]
    reviewed_at: datetime
    note: str = ""


class PassportRecord(BaseModel):
    id: str                                  # REC-...
    title: str
    created: datetime
    ai_generated: bool = True
    final_document: str | None = None
    content_hash: str


class PassportAgent(BaseModel):
    person: str
    ai_system: str
    model_requested: str
    model_returned: str
    provider: str


class PassportBusiness(BaseModel):
    function: str
    tier: Tier
    tier_reason: str
    disposal: str
    document_type: str | None = None         # policy document type id, e.g. "decision-letter"
    gate: Literal["ready", "attention", "blocked"] | None = None   # filing gate result at issue time


class PassportProcess(BaseModel):
    prompt: str
    system_prompt: str | None
    source_record_ids: list[str]
    citation_summary: dict[str, int]         # {"found": 1, "mismatch": 1, ...}
    evidence_summary: dict[str, int]         # {"supported": 2, ...}
    tool_calls: list[ToolCall]
    checks_hash: str | None = None           # sha256 of the PassportChecks stored at issue (None: summary only)


class PassportIntegrity(BaseModel):
    hash: str
    prev_hash: str | None
    algorithm: str = "sha256"
    version: int = 1
    corrects: str | None = None              # record id this version corrects, if any


class PassportParadata(BaseModel):
    use_register_id: str
    impact_assessment_ref: str | None = None
    policy_version: str
    policy_hash: str | None = None           # sha256 of the policy content the gate was judged against


class Passport(BaseModel):
    record: PassportRecord
    agent: PassportAgent
    business: PassportBusiness
    process: PassportProcess
    review: Review | None
    integrity: PassportIntegrity
    paradata: PassportParadata
    event_id: str


# ---------- tiers ----------

class TierRules(BaseModel):
    app_defaults: dict[str, Tier]            # app_id → default tier
    app_names: dict[str, str] = Field(default_factory=dict)
    escalations: dict[str, Tier]             # "exported_to_document": "T1", "decision_flag": "T2", "side_effect_tool_call": "T3"
    retention: dict[Tier, str]               # human-readable retention per tier
    retention_days: dict[Tier, int] = Field(default_factory=lambda: {"T0": 90})   # fixed periods; tiers absent follow the business record
    disposal_authority: str = "Normal administrative practice (prototype setting)"
    policy_version: str


# ---------- policy (what the information manager configures) ----------

GateStatus = Literal["ready", "attention", "blocked"]


class QualityBar(BaseModel):
    """What good looks like for one document type. Thresholds over the four weights and four citation statuses."""
    max_unsupported: int = Field(0, ge=0)    # more than this → blocked
    max_contradicted: int = Field(0, ge=0)
    max_weak: int | None = Field(None, ge=0) # None = no limit; exceeding → attention
    citations_not_found_blocks: bool = True  # any not_found citation → blocked
    citations_mismatch_attention: bool = True
    citations_not_checked_attention: bool = True  # a reference nobody could look up → a person confirms it
    require_reviewer: bool = True            # T2+ needs a named reviewer before "ready"
    min_supported_share: float | None = Field(None, ge=0, le=1)  # e.g. 0.6 → attention below 60% supported


class DocumentType(BaseModel):
    id: str                                  # "decision-letter"
    name: str
    description: str = ""
    default_tier: Tier = "T1"
    checks: list[Literal["citations", "evidence"]] = Field(default_factory=lambda: ["citations", "evidence"])
    quality: QualityBar = Field(default_factory=QualityBar)


class Policy(BaseModel):
    """The active configuration. Saved to data/policy.json; starts from a preset."""
    organisation: str
    sector: str                              # preset id, e.g. "commonwealth-agency"
    sector_name: str
    guidance: list[str] = Field(default_factory=list)       # names of guidance the passport cites, for display
    document_types: list[DocumentType]
    authoritative_systems: list[str]         # record.system values that count as evidence
    tier_rules: TierRules
    version: str = "1"
    updated_by: str = ""
    updated_at: datetime | None = None
    # dashboard signal for the information manager (never triggers a recall): flag a model once at least
    # `recall_signal_min_refs` of its checked references are in and this share of them were not found
    recall_signal_threshold: float = Field(0.30, ge=0, le=1)
    recall_signal_min_refs: int = Field(10, ge=1)


class SectorPreset(BaseModel):
    id: str
    name: str
    description: str
    guidance: list[str]
    document_types: list[DocumentType]
    authoritative_systems: list[str]
    retention_days: dict[Tier, int] = Field(default_factory=lambda: {"T0": 90})


class GateReason(BaseModel):
    status: GateStatus
    text: str


class GateResult(BaseModel):
    document_type: str
    status: GateStatus
    reasons: list[GateReason]                # worst first
    counts: dict[str, int]                   # weights + citation statuses, zero-filled


# ---------- passport view (what was checked at issue, for people) ----------

class SourceSnapshot(BaseModel):
    """A source record's state when the passport was issued."""
    record_id: str
    title: str
    system: str
    status: str
    counted: bool                            # counted as evidence for this document at issue
    why_not: str = ""                        # evidence.why_not_evidence at issue


class PassportChecks(BaseModel):
    """The detail behind a passport's summary counts, stored at issue and hashed into the passport."""
    citations: list[CitationResult] = Field(default_factory=list)
    assessment: Assessment | None = None
    gate: GateResult | None = None
    sources: list[SourceSnapshot] = Field(default_factory=list)


CheckStatus = Literal["ok", "attention", "problem", "not_run"]


class CheckSummary(BaseModel):
    id: str                                  # citations | evidence | sources | gate | review | integrity | retention | since
    name: str
    status: CheckStatus
    summary: str                             # one line
    details: dict[str, Any] = Field(default_factory=dict)


class PassportView(BaseModel):
    record_id: str
    title: str
    tier: Tier
    gate: GateStatus | None
    filed: datetime
    model_returned: str
    reviewer: str | None
    document_type: str | None
    at_issue: bool                           # full detail stored at issue; False = summary counts only (older passports)
    disposed: bool
    checks: list[CheckSummary]


class RecordSummary(BaseModel):
    """What a person reads first: one headline, its status, the four grouped checks and the policy line.
    The wording is made here, once, for every UI."""
    record_id: str
    headline: str
    status: CheckStatus
    checks: list[CheckSummary]               # Evidence, References, Filing, Since filing (view.four_checks)
    policy_line: str


# ---------- disposal ----------

class DisposalItem(BaseModel):
    record_id: str
    tier: Tier
    app_id: str
    model_returned: str
    created: datetime
    due: date                                # created + retention_days[tier]
    on_hold: bool = False                    # model under recall (faulty/withdrawn) → cannot be destroyed
    hold_reason: str = ""
    reason: str = ""                         # every row: "T0 log, 12 days past retention" or "Held: model … under recall"


class DisposalEntry(BaseModel):
    record_id: str
    tier: Tier
    created: datetime
    disposed_at: datetime
    approved_by: str
    authority: str
    reason: str
    hash_retained: str                       # the passport hash stays so the chain still verifies


# ---------- recall ----------

class ModelRegistryEntry(BaseModel):
    model_id: str
    provider: str
    status: ModelStatus = "active"
    effective_from: date | None = None
    reason: str = ""
    marked_by: str | None = None


class RecallItem(BaseModel):
    record_id: str
    tier: Tier
    function: str
    created: datetime
    reviewer: str | None
    queued: bool = False


class RecallResult(BaseModel):
    model_id: str
    entry: ModelRegistryEntry
    counts: dict[Tier, int]
    items: list[RecallItem]


class SourceRecallResult(BaseModel):
    """Recall by source record: every retained AI output that relied on a record now superseded or withdrawn."""
    record_id: str
    record: SourceRecord
    counts: dict[Tier, int]
    items: list[RecallItem]


# ---------- source health (ROT) ----------

class SourceHealth(BaseModel):
    record_id: str
    title: str
    system: str
    labels: list[RotLabel] = Field(default_factory=list)
    eligible: bool                           # counts as evidence when weighing claims
    notes: list[str] = Field(default_factory=list)   # one per label, e.g. "superseded by POL-HARDSHIP-v4"
    purpose: str = ""                        # the record's intended use, shown as "Intended use"
    not_for: list[str] = Field(default_factory=list)       # document types it must not be relied on for
    review_due: date | None = None
    overdue: bool = False                    # past review_due; still counts as evidence (the IM decides)


class SourceHealthReport(BaseModel):
    total: int
    eligible: int
    counts: dict[RotLabel, int]
    overdue: int = 0                         # records past their review date (not a ROT label: they still count)
    items: list[SourceHealth]                # flagged records first


class ReliabilityDrag(BaseModel):
    record_id: str
    title: str
    labels: list[RotLabel] = Field(default_factory=list)
    why: str                                 # why it does not count as evidence, e.g. "superseded by REC-..."
    outputs: int                             # retained outputs that list it as a source


class ReliabilityReport(BaseModel):
    """How much of the retained AI output still rests on current authoritative records (Andrea's question)."""
    retained: int                            # T1-T3 passports not disposed
    with_sources: int                        # of those, outputs that list at least one source record
    sources_ok: int                          # ... whose every source record still counts as evidence
    share: float | None                      # sources_ok / with_sources; None when nothing lists a source
    claim_checked: int                       # retained outputs with an evidence check recorded on the passport
    claim_supported: int                     # ... where every claim was supported by authoritative records
    drag: list[ReliabilityDrag] = Field(default_factory=list)   # top sources pulling the share down
    overdue: list[ReliabilityDrag] = Field(default_factory=list)  # sources relied on that are past their review date


class ChainReport(BaseModel):
    ok: bool
    checked: int
    first_break: str | None = None           # record id where the chain breaks
    detail: str = ""


class LLMResult(BaseModel):
    text: str
    model_requested: str
    model_returned: str
    input_tokens: int = 0
    output_tokens: int = 0


# ---------- information-manager dashboard (read-only; see dashboard.py) ----------

class KpiTile(BaseModel):
    id: str                                  # filed_approved | needs_review | narrow_evidence | recall_suggested
    label: str
    count: int
    total: int                               # what the count is out of (passports, or models for recall_suggested)
    percent: float | None                    # 0-100; None when total is 0 ("none yet")
    display: str                             # "12 of 40 (30%)" or "none yet"
    plain: str                               # plain words saying what it counts
    not_counted: int = 0                     # left out of `total` on purpose (e.g. T0 logs that need no review)
    not_counted_label: str = ""


class ModelSignal(BaseModel):
    model_id: str
    status: ModelStatus = "active"           # registry status
    passports: int
    references_checked: int                  # found + mismatch + not_found across its retained passports
    references_not_found: int
    rate: float | None                       # not_found / checked; None when nothing was checked
    suggested: bool                          # rate >= threshold and checked >= min refs. A signal, never a recall
    plain: str


class RecentPassport(BaseModel):
    record_id: str
    title: str
    filed: datetime
    function: str
    tier: Tier
    gate: GateStatus | None
    status: str                              # a status phrase in plain words


class SupportedStatement(BaseModel):
    record_id: str                           # the passport it sits on
    claim_id: str
    text: str
    filed: datetime
    source_record_ids: list[str]             # the authoritative records that support it


class AuthorshipCounts(BaseModel):
    ai: int
    human: int
    passports_counted: int                   # passports with the statement detail stored at issue
    plain: str


class RotCounts(BaseModel):
    total: int
    eligible: int
    overdue: int
    counts: dict[RotLabel, int]
    plain: str


class DisposalDue(BaseModel):
    count: int
    held_by_recall: int
    authority: str
    plain: str


class FunctionRow(BaseModel):
    function: str
    total: int
    filed_approved: int
    needs_review: int
    narrow_evidence: int
    on_suggested_model: int                  # passports made by a model the recall signal flags


class WeekCount(BaseModel):
    week_start: date                         # Monday of the week
    filed: int
    approved: int


class GateByType(BaseModel):
    document_type: str | None                # None: filed without a document type (older passports)
    name: str
    ready: int
    attention: int
    blocked: int
    not_recorded: int


class ModelRow(BaseModel):
    model_id: str
    provider: str
    status: str                              # registry status, or "not registered"
    filed: int                               # passports that name it as the model that answered
    in_recall_queue: int                     # of those, with an open entry in the review queue


class BiasCounts(BaseModel):
    ok: int
    attention: int
    not_run: int
    label: str


class RecordIndexRow(BaseModel):
    """One row of the Records list, for filters and search; statuses decided by the same rules as /view and /dashboard."""
    record_id: str
    title: str
    case_id: str | None                      # from the filed document, else from its source records
    tier: Tier
    function: str
    created: datetime
    gate: GateStatus | None
    status: Literal["filed", "needs_person", "changed", "disposed", "log_only"]
    status_label: str
    changed_since: bool                      # the passport view's live "Since filing" check is a problem
    document_type: str | None


class DraftReview(BaseModel):
    """A draft sent to a person before filing, because the gate said it needs one. Never a passport, never filed.
    For a pasted (ad hoc) draft only the title and a hash of the text are kept: nothing pasted is stored."""
    id: str                                  # DR-000001
    document_id: str | None                  # a known document, or None for a pasted draft
    title: str
    body_hash: str | None = None             # sha256 of a pasted body (its text is never stored)
    document_type: str
    status: Literal["open", "closed"] = "open"
    gate: GateStatus                         # the server's own gate result (attention or blocked)
    reasons: list[str]                       # the gate's reasons, as the server computed them
    requested_by: str
    note: str = ""
    created: datetime


class QueueCounts(BaseModel):
    open: int
    closed: int
    label: str
    drafts_open: int = 0                     # drafts sent for a person's review before filing (not passports)


class DashboardReport(BaseModel):
    kpis: list[KpiTile]
    model_signals: list[ModelSignal]
    recent: list[RecentPassport]             # the last 10 filed
    recent_supported: list[SupportedStatement]   # up to 10 latest statements supported by authoritative records
    authorship: AuthorshipCounts
    rot: RotCounts
    disposal_due: DisposalDue
    by_function: list[FunctionRow]
    filed_by_week: list[WeekCount] = Field(default_factory=list)   # the last 8 weeks to the latest passport
    gate_by_type: list[GateByType] = Field(default_factory=list)
    by_model: list[ModelRow] = Field(default_factory=list)
    bias: BiasCounts | None = None           # passports by Bias check status (same rule as the passport view)
    queue: QueueCounts | None = None
    generated_at: datetime
    policy_version: str
