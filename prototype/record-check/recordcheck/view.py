"""The passport as people see it: the record and the checks done on it, each with a one-line summary and its detail.

Everything shown is what was checked AT ISSUE (stored with the passport and hashed into it), except "Since filing",
which is the one live check. Older passports carry summary counts only and say so. No LLM.
"""

from __future__ import annotations

from datetime import date

from . import db, passport
from .disposal import HELD_STATUSES
from .evidence import is_evidence, why_not_evidence
from .models import CheckSummary, Passport, PassportChecks, PassportView, Policy

WEIGHTS = ("supported", "weak", "unsupported", "contradicted")
TIER_WORDS = {"T0": "transitory log", "T1": "retained output", "T2": "informs a decision", "T3": "agent action"}
SUMMARY_ONLY = "Filed before checks were stored with passports: summary counts only."


def _type_name(policy: Policy | None, type_id: str | None) -> str:
    if not type_id:
        return "an unspecified document type"
    d = next((d for d in policy.document_types if d.id == type_id), None) if policy else None
    return d.name if d else type_id


def _n(k: int, noun: str) -> str:
    return f"{k} {noun}" + ("" if k == 1 else "s")


def _stored(conn, p: Passport) -> tuple[PassportChecks | None, bool]:
    """(checks, intact). None when the passport predates stored checks or was disposed."""
    if not p.process.checks_hash:
        return None, True
    row = conn.execute("SELECT hash, payload FROM passport_checks WHERE record_id=?", (p.record.id,)).fetchone()
    if row is None:
        return None, False
    checks = PassportChecks.model_validate_json(row["payload"])
    return checks, passport.checks_hash(checks) == p.process.checks_hash == row["hash"]


def _citations(p: Passport, ch: PassportChecks | None) -> CheckSummary:
    c = p.process.citation_summary
    total = sum(c.values())
    if not total:
        return CheckSummary(id="citations", name="Citations", status="not_run", summary="No references were checked.")
    nf, mm, nc = c.get("not_found", 0), c.get("mismatch", 0), c.get("not_checked", 0)
    status = "problem" if nf else "attention" if (mm or nc) else "ok"
    bits = [f"{c.get('found', 0)} found"] + ([f"{nf} not found"] if nf else []) + \
           ([f"{mm} with details that do not match"] if mm else []) + ([f"{nc} for a person to confirm"] if nc else [])
    details = {"items": [{"n": r.citation.n, "reference": r.citation.raw, "status": r.status, "note": r.note,
                          "matched": r.matched_title, "doi": r.doi} for r in ch.citations]} if ch else {"note": SUMMARY_ONLY}
    return CheckSummary(id="citations", name="Citations", status=status,
                        summary=f"{_n(total, 'reference')} checked: " + ", ".join(bits) + ".", details=details)


def _evidence(p: Passport, ch: PassportChecks | None) -> CheckSummary:
    e = p.process.evidence_summary
    total = sum(e.values())
    if not total:
        return CheckSummary(id="evidence", name="Evidence", status="not_run",
                            summary="No statements were weighed against records.")
    status = "problem" if (e.get("unsupported", 0) or e.get("contradicted", 0)) else \
             "attention" if e.get("weak", 0) else "ok"
    summary = (f"{e.get('supported', 0)} of {total} statements supported by authoritative records"
               + "".join(f"; {e[w]} {w}" for w in WEIGHTS[1:] if e.get(w)) + ".")
    if ch and ch.assessment:
        text = {c.id: c.text for c in ch.assessment.claims}
        details = {"method": ch.assessment.method, "items": [
            {"claim_id": v.claim_id, "text": text.get(v.claim_id, ""), "weight": v.weight, "reason": v.reason,
             "links": [{"record_id": l.record_id, "rule": l.rule, "note": l.note} for l in v.links]}
            for v in ch.assessment.verdicts]}
    else:
        details = {"note": SUMMARY_ONLY}
    return CheckSummary(id="evidence", name="Evidence", status=status, summary=summary, details=details)


def _sources(p: Passport, ch: PassportChecks | None) -> CheckSummary:
    if ch is None:
        ids = p.process.source_record_ids
        return CheckSummary(id="sources", name="Sources", status="not_run",
                            summary=(f"{_n(len(ids), 'source record')} listed; their state at issue was not recorded."
                                     if ids else "No source records listed."),
                            details={"note": SUMMARY_ONLY + " See Since filing for their state now.", "records": ids})
    if not ch.sources:
        return CheckSummary(id="sources", name="Sources", status="not_run", summary="No source records listed.")
    bad = [s for s in ch.sources if not s.counted]
    summary = (f"All {_n(len(ch.sources), 'source')} were current authoritative records at issue." if not bad else
               f"{len(bad)} of {_n(len(ch.sources), 'source')} did not count as evidence at issue: "
               + "; ".join(f"{s.record_id} ({s.why_not})" for s in bad[:3]) + ("..." if len(bad) > 3 else "") + ".")
    return CheckSummary(id="sources", name="Sources", status="attention" if bad else "ok", summary=summary,
                        details={"items": [s.model_dump() for s in ch.sources]})


def _gate(p: Passport, ch: PassportChecks | None, policy: Policy | None) -> CheckSummary:
    b, pd = p.business, p.paradata
    meta = {"policy_version": pd.policy_version, "policy_hash": pd.policy_hash, "document_type": b.document_type}
    if b.gate is None:
        return CheckSummary(id="gate", name="Filing gate", status="not_run",
                            summary="No filing gate recorded for this passport.", details=meta)
    label = {"ready": "Ready to file", "attention": "Filed with items needing attention", "blocked": "Blocked"}[b.gate]
    reasons = [r.text for r in ch.gate.reasons] if ch and ch.gate else []
    return CheckSummary(id="gate", name="Filing gate", status={"ready": "ok", "attention": "attention"}.get(b.gate, "problem"),
                        summary=f"{label} against the bar for {_type_name(policy, b.document_type)} "
                                f"({pd.policy_version}).",
                        details={**meta, "reasons": reasons} if reasons else {**meta, "note": SUMMARY_ONLY if not ch else ""})


def _review(p: Passport) -> CheckSummary:
    rv, tier = p.review, p.business.tier
    if rv is None:
        needed = tier in ("T2", "T3")
        return CheckSummary(id="review", name="Review", status="attention" if needed else "ok",
                            summary=("No named reviewer; a decision-informing or agentic record should have one."
                                     if needed else f"No review required at {tier}."))
    if rv.decision == "rejected":
        status, line = "problem", f"Rejected by {rv.reviewer}."
    else:
        status, line = "ok", f"{rv.decision.replace('_', ' ').capitalize()} by {rv.reviewer}, not the author ({p.agent.person})."
    return CheckSummary(id="review", name="Review", status=status, summary=line,
                        details={"reviewer": rv.reviewer, "decision": rv.decision,
                                 "reviewed_at": rv.reviewed_at.isoformat(), "note": rv.note})


def _integrity(conn, p: Passport, intact: bool, disposed: bool) -> CheckSummary:
    chain = passport.verify_chain(conn)
    own = disposed or passport.compute_hash(p) == p.integrity.hash
    ok = chain.ok and own and intact
    if ok:
        line = f"Hash verified; chain intact ({chain.checked} passports)." + (" Content disposed; hash retained." if disposed else "")
    elif not own:
        line = "This passport's content does not match its hash."
    elif not intact:
        line = "The checks stored at issue are missing or do not match the passport."
    else:
        line = f"Chain broken at {chain.first_break}."
    return CheckSummary(id="integrity", name="Integrity", status="ok" if ok else "problem", summary=line,
                        details={"algorithm": p.integrity.algorithm, "hash": p.integrity.hash,
                                 "prev_hash": p.integrity.prev_hash, "checks_hash": p.process.checks_hash,
                                 "chain": chain.detail})


def _retention(p: Passport, policy: Policy | None, disposed_at: str | None) -> CheckSummary:
    rules = policy.tier_rules if policy else passport.load_tier_rules()
    tier = p.business.tier
    days = rules.retention_days.get(tier)
    when = f"kept {days} days, then destroyed with approval" if days else "kept with the business record it supports"
    line = (f"Disposed on {disposed_at[:10]} under {rules.disposal_authority}; hash retained." if disposed_at else
            f"{tier} ({TIER_WORDS[tier]}): {when}.")
    return CheckSummary(id="retention", name="Retention", status="ok", summary=line,
                        details={"tier": tier, "disposal": p.business.disposal, "retention_days": days,
                                 "authority": rules.disposal_authority, "disposed_at": disposed_at})


def _since(conn, p: Passport, ch: PassportChecks | None, policy: Policy | None) -> CheckSummary:
    ids = list(dict.fromkeys(list(p.process.source_record_ids) + [s.record_id for s in (ch.sources if ch else [])]))
    counted_then = {s.record_id: s.counted for s in ch.sources} if ch else {}
    changed = []
    for rid in ids:
        r = db.get_record(conn, rid)
        if r is not None and policy is not None and r.authoritative and r.system not in policy.authoritative_systems:
            r = r.model_copy(update={"authoritative": False})
        if r is None or not is_evidence(r, p.business.document_type):
            if counted_then.get(rid, True):     # it counted at issue (or we don't know): this is a change
                changed.append({"record_id": rid, "why": why_not_evidence(r, p.business.document_type) if r else
                                "no longer in the records system", "superseded_by": r.superseded_by if r else None})
    model = next((m for m in db.get_model_registry(conn) if m.model_id == p.agent.model_returned), None)
    recalled = model is not None and model.status in HELD_STATUSES
    queued = conn.execute("SELECT COUNT(*) FROM review_queue WHERE record_id=? AND status='open'",
                          (p.record.id,)).fetchone()[0] > 0
    bits = [f"{c['record_id']} {c['why']}" for c in changed]
    if recalled:
        bits.append(f"model {model.model_id} marked {model.status}" + (f": {model.reason}" if model.reason else ""))
    if queued:
        bits.append("queued for re-review")
    status = "problem" if (changed or recalled) else "attention" if queued else "ok"
    summary = ("Nothing has changed since filing: its sources still count and its model is not under recall."
               if status == "ok" else "Since filing: " + "; ".join(bits) + ".")
    return CheckSummary(id="since", name="Since filing", status=status, summary=summary,
                        details={"sources_changed": changed, "model": p.agent.model_returned,
                                 "model_status": model.status if model else "not registered", "queued": queued,
                                 "recall": f"/recall?model_id={p.agent.model_returned}" if recalled else None,
                                 "live": True})


def view(conn, record_id: str, policy: Policy | None = None) -> PassportView | None:
    row = conn.execute("SELECT payload, disposed_at FROM passports WHERE record_id=?", (record_id,)).fetchone()
    if row is None:
        return None
    p = Passport.model_validate_json(row["payload"])
    disposed_at = row["disposed_at"]
    ch, intact = (None, True) if disposed_at else _stored(conn, p)
    checks = [_citations(p, ch), _evidence(p, ch), _sources(p, ch), _gate(p, ch, policy), _review(p),
              _integrity(conn, p, intact, bool(disposed_at)), _retention(p, policy, disposed_at)]
    if not disposed_at:
        checks.append(_since(conn, p, ch, policy))
    return PassportView(record_id=p.record.id, title=p.record.title, tier=p.business.tier, gate=p.business.gate,
                        filed=p.record.created, model_returned=p.agent.model_returned,
                        reviewer=p.review.reviewer if p.review else None, document_type=p.business.document_type,
                        at_issue=ch is not None, disposed=bool(disposed_at), checks=checks)


def view_all(conn, policy: Policy | None = None, as_of: date | None = None) -> list[PassportView]:
    """Every passport's view, newest first (for the Records list)."""
    ids = [r["record_id"] for r in conn.execute("SELECT record_id FROM passports ORDER BY seq DESC")]
    return [v for v in (view(conn, i, policy) for i in ids) if v is not None]
