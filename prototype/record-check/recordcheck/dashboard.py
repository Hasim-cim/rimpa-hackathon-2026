"""Information-manager dashboard: one read-only report over the passports, models, sources and disposal queue.

No LLM, no writes. It reuses the engine's own readers (passport list, source health, disposal due, review queue,
stored checks) and adds only the counting. Every flag here is a signal for the information manager to look at;
nothing on this page recalls a model, blocks a record or changes one.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime, timezone

from . import db, disposal, recall, sources
from .evidence import is_evidence
from .models import (AuthorshipCounts, DashboardReport, DisposalDue, FunctionRow, KpiTile, ModelSignal, Passport,
                     Policy, RecentPassport, RotCounts, SourceRecord, SupportedStatement)
from .policy import authoritative
from .view import _stored

APPROVED = ("approved", "approved_with_edits")
RECENT = 10


# ---------- small helpers ----------

def _pct(n: int, total: int) -> float | None:
    return round(100 * n / total, 1) if total else None


def _show(n: int, total: int, noun: str = "") -> str:
    """'12 of 40 (30%)', or 'none yet' with nothing to count (never a division by zero)."""
    if not total:
        return "none yet"
    return f"{n} of {total}{noun} ({round(100 * n / total)}%)"


def _tile(id_: str, label: str, n: int, total: int, plain: str, noun: str = "") -> KpiTile:
    return KpiTile(id=id_, label=label, count=n, total=total, percent=_pct(n, total), display=_show(n, total, noun),
                   plain=plain)


# ---------- per-passport tests ----------

def _filed_approved(p: Passport) -> bool:
    # gate None: filed before the gate existed, so the named reviewer's approval is the test
    return p.business.gate in ("ready", None) and p.review is not None and p.review.decision in APPROVED


def _attention(p: Passport, queued: set[str]) -> list[str]:
    """Why a person needs to look, in plain words. Empty when nothing does."""
    ev, cit = p.process.evidence_summary, p.process.citation_summary
    why: list[str] = []
    if ev.get("contradicted", 0):
        why.append("a statement is contradicted by a record")
    if ev.get("unsupported", 0):
        why.append("a statement is unsupported")
    if cit.get("not_found", 0):
        why.append("a reference was not found")
    if p.business.gate in ("blocked", "attention"):
        why.append(f"the filing gate says {p.business.gate}")
    if p.record.id in queued:
        why.append("it is in the review queue")
    return why


def _weak_reason(rec: SourceRecord | None, policy: Policy, doc_type: str | None) -> bool:
    if rec is None:
        return True                                   # a source that is not in the records system
    return (not authoritative(policy, rec) or rec.status in ("draft", "superseded")
            or bool(doc_type and doc_type in rec.not_for))


def _rests_on(ids: list[str], recs: dict[str, SourceRecord], policy: Policy, doc_type: str | None) -> bool:
    """Fixed rules for a narrow-evidence signal on one statement (or one passport, for older ones): it rests on a single
    record, or on records from a single system, or on a weak, draft, superseded or wrong-use record."""
    ids = list(dict.fromkeys(ids))
    if not ids:
        return False
    systems = {recs[i].system for i in ids if i in recs}
    return len(ids) == 1 or len(systems) <= 1 or any(_weak_reason(recs.get(i), policy, doc_type) for i in ids)


def _narrow_evidence(p: Passport, checks, recs: dict[str, SourceRecord], policy: Policy) -> bool:
    doc_type = p.business.document_type
    if checks is not None and checks.assessment is not None:
        for v in checks.assessment.verdicts:
            claim = next((c for c in checks.assessment.claims if c.id == v.claim_id), None)
            if claim is not None and claim.author != "ai":
                continue
            if _rests_on([l.record_id for l in v.links], recs, policy, doc_type):
                return True
        return False
    return _rests_on(p.process.source_record_ids, recs, policy, doc_type)


def _status(p: Passport, queued: set[str]) -> str:
    why = _attention(p, queued)
    if p.review is not None and p.review.decision == "rejected":
        return "Rejected by " + p.review.reviewer
    if why:
        return "Needs a person: " + why[0]
    if _filed_approved(p):
        return "Filed and approved by " + p.review.reviewer
    if p.business.tier == "T0":
        return "Log entry only"
    if p.review is not None:
        return "Reviewed by " + p.review.reviewer
    return "Filed, no review recorded"


# ---------- the report ----------

def _signals(passports: list[Passport], registry, policy: Policy) -> list[ModelSignal]:
    thr, floor = policy.recall_signal_threshold, policy.recall_signal_min_refs
    status = {e.model_id: e.status for e in registry}
    checked: dict[str, int] = defaultdict(int)
    missing: dict[str, int] = defaultdict(int)
    made: dict[str, int] = defaultdict(int)
    for p in passports:
        m = p.agent.model_returned
        c = p.process.citation_summary
        made[m] += 1
        checked[m] += c.get("found", 0) + c.get("mismatch", 0) + c.get("not_found", 0)
        missing[m] += c.get("not_found", 0)
    out = []
    for m in sorted(set(made) | set(status)):
        n, nf = checked[m], missing[m]
        rate = nf / n if n else None
        flag = rate is not None and n >= floor and rate >= thr
        if flag:
            line = (f"Recall suggested: {m}, {round(100 * rate)}% of its references not found "
                    f"({nf} of {n} checked)." + (f" Already marked {status[m]}." if status.get(m, "active") != "active" else "")
                    + " The information manager decides.")
        elif n < floor:
            line = f"{n} references checked so far; a flag needs at least {floor}."
        else:
            line = f"{round(100 * rate)}% of {n} checked references not found; below the {round(100 * thr)}% signal."
        out.append(ModelSignal(model_id=m, status=status.get(m, "active"), passports=made[m], references_checked=n,
                               references_not_found=nf, rate=rate, suggested=flag, plain=line))
    return out


def report(conn: sqlite3.Connection, policy: Policy) -> DashboardReport:
    gone = {e.record_id for e in disposal.register(conn)}
    passports = [p for p in db.get_passports(conn) if p.record.id not in gone]
    queued = recall.open_queue_ids(conn)
    recs = {r.id: r for r in db.get_records(conn)}
    total = len(passports)
    stored = {p.record.id: (_stored(conn, p) if p.process.checks_hash else (None, True)) for p in passports}
    checks = {rid: (c if ok else None) for rid, (c, ok) in stored.items()}

    signals = _signals(passports, db.get_model_registry(conn), policy)
    flagged = {s.model_id for s in signals if s.suggested}

    approved = [_filed_approved(p) for p in passports]
    needs = [bool(_attention(p, queued)) for p in passports]
    narrow = [_narrow_evidence(p, checks[p.record.id], recs, policy) for p in passports]

    pct = lambda x: f"{round(100 * x)}%"  # noqa: E731
    if flagged:
        by_id = {s.model_id: s for s in signals}
        recall_plain = "Recall suggested: " + "; ".join(
            f"{m}, {pct(by_id[m].rate)} of its references not found" for m in sorted(flagged)) + \
            ". The information manager decides."
    else:
        recall_plain = (f"No recall suggested. A model is flagged at {pct(policy.recall_signal_threshold)} or more "
                        f"of at least {policy.recall_signal_min_refs} checked references not found.")
    kpis = [
        _tile("filed_approved", "Filed with a passport and approved", sum(approved), total,
              "Passports a named reviewer approved (with or without edits), with the filing gate at ready or filed before the gate existed."),
        _tile("needs_review", "Need a person: contradicted, unsupported or a reference not found", sum(needs), total,
              "Passports with a contradicted or unsupported statement, a reference not found, a gate result of "
              "blocked or attention, or an open entry in the review queue."),
        _tile("narrow_evidence", "Narrow-evidence signals: rests on one source, or on weak, draft or superseded records",
              sum(narrow), total,
              "Passports with a statement that rests on one record or one system, on a record that is not "
              "authoritative, is a draft or is superseded, or on a record not meant for that document type. "
              "A signal to look at, not a finding."),
        _tile("recall_suggested", "Recall suggested", len(flagged), len(signals), recall_plain, noun=" models"),
    ]

    recent = [RecentPassport(record_id=p.record.id, title=p.record.title, filed=p.record.created,
                             function=p.business.function, tier=p.business.tier, gate=p.business.gate,
                             status=_status(p, queued)) for p in passports[::-1][:RECENT]]

    statements: list[SupportedStatement] = []
    ai = human = counted = 0
    for p in passports[::-1]:
        ch = checks[p.record.id]
        if ch is None or ch.assessment is None:
            continue
        counted += 1
        a = ch.assessment
        ai += sum(c.author == "ai" for c in a.claims)
        human += sum(c.author == "human" for c in a.claims)
        by_claim = {c.id: c for c in a.claims}
        for v in sorted(a.verdicts, key=lambda v: -(by_claim[v.claim_id].position if v.claim_id in by_claim else 0)):
            if v.weight != "supported" or v.claim_id not in by_claim or len(statements) >= RECENT:
                continue
            ids = [i for i in dict.fromkeys(l.record_id for l in v.links)
                   if i in recs and is_evidence(recs[i].model_copy(update={"authoritative": authoritative(policy, recs[i])}),
                                                p.business.document_type)]
            statements.append(SupportedStatement(record_id=p.record.id, claim_id=v.claim_id,
                                                 text=by_claim[v.claim_id].text, filed=p.record.created,
                                                 source_record_ids=ids))
    authorship = AuthorshipCounts(
        ai=ai, human=human, passports_counted=counted,
        plain=(f"{ai} AI-written and {human} human-written statements, from the {counted} passports that store "
               "their statement detail." if counted else "none yet: no passport stores its statement detail."))

    h = sources.health(conn, policy)
    rot = RotCounts(total=h.total, eligible=h.eligible, overdue=h.overdue, counts=h.counts,
                    plain=(f"{h.total - h.eligible} of {h.total} source records do not count as evidence "
                           f"(redundant {h.counts['redundant']}, obsolete {h.counts['obsolete']}, "
                           f"trivial {h.counts['trivial']}, draft {h.counts['draft']}); {h.overdue} past their review date."
                           if h.total else "none yet: no source records."))

    due = disposal.due_for_disposal(conn, rules=policy.tier_rules)
    held = sum(i.on_hold for i in due)
    disposal_due = DisposalDue(count=len(due), held_by_recall=held, authority=policy.tier_rules.disposal_authority,
                               plain=(f"{len(due)} log entries are past their retention period; {held} are held because "
                                      f"their model is under recall. Disposal needs the information manager's approval "
                                      f"under: {policy.tier_rules.disposal_authority}."))

    rows: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0])
    for p, a, n, b in zip(passports, approved, needs, narrow):
        r = rows[p.business.function]
        r[0] += 1
        r[1] += a
        r[2] += n
        r[3] += b
        r[4] += p.agent.model_returned in flagged
    by_function = [FunctionRow(function=f, total=r[0], filed_approved=r[1], needs_review=r[2], narrow_evidence=r[3],
                               on_suggested_model=r[4]) for f, r in sorted(rows.items())]

    return DashboardReport(kpis=kpis, model_signals=signals, recent=recent, recent_supported=statements,
                           authorship=authorship, rot=rot, disposal_due=disposal_due, by_function=by_function,
                           generated_at=datetime.now(timezone.utc), policy_version=policy.version)
