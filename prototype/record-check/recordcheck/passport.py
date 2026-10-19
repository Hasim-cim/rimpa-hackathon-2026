"""Tier rules, passport builder and hash chain."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

from . import db
from . import gate as gatemod
from .hashing import sha256
from .models import (
    Policy,
    AIEvent, Assessment, ChainReport, CitationResult, GateResult, Passport, PassportChecks, SourceSnapshot, naive_utc, PassportAgent, PassportBusiness,
    GateStatus, PassportIntegrity, PassportParadata, PassportProcess, PassportRecord, Review, Tier, TierRules,
)

TIER_ORDER: dict[str, int] = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}
CITATION_KEYS = ("found", "mismatch", "not_found", "not_checked")
EVIDENCE_KEYS = ("supported", "weak", "unsupported", "contradicted")
ID_RE = re.compile(r"^REC-2026/(\d+)$")


def load_tier_rules(path: Path | str | None = None) -> TierRules:
    p = Path(path) if path else db.SEED_DIR / "tier_rules.json"
    with open(p, encoding="utf-8") as f:
        return TierRules(**json.load(f))


def _app_name(event: AIEvent, rules: TierRules) -> str:
    name = rules.app_names.get(event.app_id)
    return name.split(" (")[0] if name else event.app_id


def classify_with_reason(event: AIEvent, rules: TierRules) -> tuple[Tier, str]:
    known = event.app_id in rules.app_defaults
    tier: Tier = rules.app_defaults.get(event.app_id, "T0")
    name = _app_name(event, rules)
    parts = [f"Default {tier} for {name}" if known else f"Default {tier} (unregistered app {event.app_id})"]

    def bump(to: Tier, why: str) -> None:
        nonlocal tier
        if TIER_ORDER[to] > TIER_ORDER[tier]:
            tier = to
            parts.append(f"{why} → {to}")

    if event.exported_to_document:
        bump(rules.escalations.get("exported_to_document", "T1"), "output filed into a document")
    if event.decision_flag:
        bump(rules.escalations.get("decision_flag", "T2"), "used in a decision")
    if any(tc.side_effect for tc in event.tool_calls):
        bump(rules.escalations.get("side_effect_tool_call", "T3"), "agent took an action with side effects")
    return tier, "; ".join(parts) + "."


def classify(event: AIEvent, rules: TierRules) -> Tier:
    return classify_with_reason(event, rules)[0]


def next_record_id(conn: sqlite3.Connection) -> str:
    """max existing id (passports and source records) + 1, as REC-2026/NNNNNN."""
    top = 0
    for table, col in (("passports", "record_id"), ("records", "id")):
        for r in conn.execute(f"SELECT {col} FROM {table}"):
            m = ID_RE.match(r[0])
            if m:
                top = max(top, int(m.group(1)))
    return f"REC-2026/{top + 1:06d}"


class GateBlocked(ValueError):
    """Raised when a passport is requested for a document the filing gate blocked. Enforced here, not only in the UI."""

    def __init__(self, message: str, result: GateResult | None = None):
        super().__init__(message)
        self.result = result


class TierBelowRules(ValueError):
    """Raised when a caller sets a tier lower than the rules give: a T3 agent action must not be filed as transitory."""


class SelfReview(ValueError):
    """Raised when the reviewer is the person who produced the AI-assisted output."""


class DuplicateRecord(ValueError):
    """Raised when a record id is already in the chain; replacing a passport would break it."""


def policy_hash(policy: "Policy") -> str:
    """Hash of the policy *content*: version, author and timestamp excluded, so an unchanged bar hashes the same."""
    return sha256(policy.model_dump(mode="json", exclude={"version", "updated_by", "updated_at", "recall_signal_threshold", "recall_signal_min_refs"}))


def compute_hash(p: Passport) -> str:
    # exclude_none so that adding optional fields to the schema later does not change old hashes:
    # a record package must stay verifiable for as long as the record is kept
    d = p.model_dump(mode="json", exclude_none=True)
    d["integrity"]["hash"] = ""
    return sha256(d)


def build(event: AIEvent, *, tier: Tier, assessment: Assessment | None = None,
          citations: list[CitationResult] | tuple = (), review: Review | None = None,
          conn: sqlite3.Connection, rules: TierRules | None = None, record_id: str | None = None,
          document_type: str | None = None, gate: GateStatus | None = None,
          policy: "Policy | None" = None) -> Passport:
    """With a policy, the filing gate is run here against the given document type (or, with none, the strictest
    default bar over whatever was supplied), so no caller can skip it; `gate` is then ignored."""
    if policy is not None:
        rules = rules or policy.tier_rules
    rules = rules or load_tier_rules()
    classified, reason = classify_with_reason(event, rules)
    if TIER_ORDER[tier] < TIER_ORDER[classified]:
        raise TierBelowRules(f"Tier {tier} is below the {classified} the rules give ({reason}) A tier can be raised, "
                             "never lowered.")
    if tier != classified:
        reason = f"Tier {tier} set by the information manager (rules gave {classified}). {reason}"
    if review is not None and not review.reviewer.strip():
        raise ValueError("A review needs the reviewer's name.")
    if review is not None and gatemod.same_person(review.reviewer, event.user):
        raise SelfReview(f"{review.reviewer} produced this output and cannot also review it.")
    result: GateResult | None = None
    if policy is not None:
        if document_type is None:
            dtype = gatemod.baseline_type(evidence=assessment is not None, citations=bool(citations))
        else:
            dtype = next((d for d in policy.document_types if d.id == document_type), None)
            if dtype is None:
                raise ValueError(f"unknown document type {document_type!r}")
        result = gatemod.evaluate(assessment, list(citations), review, dtype, tier, author=event.user)
        gate = result.status
        if gate == "blocked":
            raise GateBlocked(gatemod.summary_line(result), result)
    elif gate == "blocked":
        raise GateBlocked(f"{document_type or 'document'} is blocked by policy; fix the document or change the bar.")

    cit = {k: 0 for k in CITATION_KEYS}
    for c in citations:
        cit[c.status] = cit.get(c.status, 0) + 1
    ev = {k: 0 for k in EVIDENCE_KEYS}
    if assessment:
        for v in assessment.verdicts:
            ev[v.weight] = ev.get(v.weight, 0) + 1

    checks = PassportChecks(citations=list(citations), assessment=assessment, gate=result,
                            sources=_snapshot(conn, event, assessment, policy, document_type))

    # one writer at a time from here to the commit: the id, prev_hash and seq all depend on the chain's head,
    # and on Postgres several instances may write at once
    db.lock(conn, db.CHAIN_LOCK)
    try:
        p = _append(conn, event, tier, reason, rules, review, record_id, document_type, gate, policy, cit, ev, checks)
    except BaseException:
        conn.rollback()
        raise
    return p


def _snapshot(conn, event: AIEvent, assessment: Assessment | None, policy, document_type) -> list[SourceSnapshot]:
    """Each source the output relied on, as it stood at issue (judged by the policy in force). Every record a claim
    matched, counted or not, stays visible in the stored assessment."""
    from . import evidence
    ids = list(event.source_record_ids)
    out = []
    for rid in dict.fromkeys(ids):
        r = db.get_record(conn, rid)
        if r is None:
            out.append(SourceSnapshot(record_id=rid, title="(not in the records system)", system="", status="missing",
                                      counted=False, why_not="not found in the records system"))
            continue
        if policy is not None and r.authoritative and r.system not in policy.authoritative_systems:
            r = r.model_copy(update={"authoritative": False})
        out.append(SourceSnapshot(record_id=r.id, title=r.title, system=r.system, status=r.status,
                                  counted=evidence.is_evidence(r, document_type),
                                  why_not=evidence.why_not_evidence(r, document_type)))
    return out


def checks_hash(checks: PassportChecks) -> str:
    return sha256(checks.model_dump(mode="json", exclude_none=True))


def _append(conn, event, tier, reason, rules, review, record_id, document_type, gate, policy, cit, ev,
            checks: PassportChecks) -> Passport:
    if record_id is not None and db.get_passport(conn, record_id) is not None:
        raise DuplicateRecord(f"{record_id} is already in the chain.")
    rid = record_id or next_record_id(conn)
    p = Passport(
        record=PassportRecord(
            id=rid, title=f"{event.function or 'AI-assisted output'} ({_app_name(event, rules)})",
            created=naive_utc(event.created), ai_generated=True, final_document=event.exported_to_document,
            content_hash=sha256(event.output.encode("utf-8")),
        ),
        agent=PassportAgent(person=event.user, ai_system=_app_name(event, rules),
                            model_requested=event.model_requested, model_returned=event.model_returned,
                            provider=event.provider),
        business=PassportBusiness(function=event.function, tier=tier, tier_reason=reason,
                                  disposal=rules.retention[tier], document_type=document_type, gate=gate),
        process=PassportProcess(prompt=event.prompt, system_prompt=event.system_prompt,
                                source_record_ids=list(event.source_record_ids),
                                citation_summary=cit, evidence_summary=ev, tool_calls=list(event.tool_calls),
                                checks_hash=checks_hash(checks)),
        review=review,
        integrity=PassportIntegrity(hash="", prev_hash=db.latest_passport_hash(conn)),
        paradata=PassportParadata(
            use_register_id=f"USE-{event.app_id}",
            policy_version=(f"policy v{policy.version} ({policy.sector})" if policy else rules.policy_version),
            policy_hash=(policy_hash(policy) if policy else None)),
        event_id=event.id,
    )
    p.integrity.hash = compute_hash(p)
    db.insert_passport(conn, p)
    db.upsert(conn, "passport_checks", "record_id",
              dict(record_id=rid, hash=p.process.checks_hash, payload=checks.model_dump_json()))
    db.audit(conn, actor=event.user, action="passport.issued", subject=rid,
             detail=f"tier {tier}; hash {p.integrity.hash[:12]}")
    conn.commit()
    return p


def verify_chain(conn: sqlite3.Connection) -> ChainReport:
    prev: str | None = None
    n = 0
    disposed = 0
    register = {r["record_id"]: r["hash_retained"] for r in conn.execute("SELECT record_id, hash_retained FROM disposal_register")}
    for row in conn.execute("SELECT record_id, hash, prev_hash, payload, disposed_at FROM passports ORDER BY seq"):
        p = Passport.model_validate_json(row["payload"])
        rid = p.record.id
        is_disposed = bool(row["disposed_at"])  # content destroyed by design: trust the stored hash, still check the links
        if is_disposed and register.get(rid) != row["hash"]:
            return ChainReport(ok=False, checked=n, first_break=rid, detail=f"{rid}: marked disposed but the disposal register has no matching approval.")
        if p.integrity.hash != row["hash"] or (not is_disposed and compute_hash(p) != p.integrity.hash):
            return ChainReport(ok=False, checked=n, first_break=rid, detail=f"{rid}: stored hash does not match the recomputed hash (content altered).")
        if p.integrity.prev_hash != prev:
            return ChainReport(ok=False, checked=n, first_break=rid, detail=f"{rid}: prev_hash does not match the preceding passport (record missing, reordered or replaced).")
        prev = p.integrity.hash
        n += 1
        disposed += is_disposed
    detail = f"{n} passports verified; chain intact."
    if disposed:
        detail = f"{n} passports verified; chain intact; {disposed} disposed entries retained as hash stubs."
    return ChainReport(ok=True, checked=n, detail=detail)


def view(conn, record_id: str, policy: "Policy | None" = None):
    """The passport and the checks done on it, for people (see view.py). None for an unknown record."""
    from . import view as viewmod
    return viewmod.view(conn, record_id, policy)

