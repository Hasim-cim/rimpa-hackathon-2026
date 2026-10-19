"""Shared data models. This file is the contract between modules; change shapes here first."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

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
    source: Literal["fixture", "crossref", "openalex", "none"] = "none"
    doi: str | None = None
    matched_title: str | None = None
    matched_year: int | None = None
    matched_venue: str | None = None
    score: float | None = None
    note: str = ""


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


class SourceHealthReport(BaseModel):
    total: int
    eligible: int
    counts: dict[RotLabel, int]
    items: list[SourceHealth]                # flagged records first


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
