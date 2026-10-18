"""Filing gate: thresholds from the policy applied to the engine's output. Pure function, no LLM."""

from __future__ import annotations

from .models import (Assessment, CitationResult, DocumentType, GateReason, GateResult, Review, Tier)

WEIGHTS = ("supported", "weak", "unsupported", "contradicted")
CITE_STATUSES = ("found", "mismatch", "not_found", "not_checked")
_ORDER = {"blocked": 0, "attention": 1, "ready": 2}


def _n(k: int, noun: str) -> str:
    return f"{k} {noun}" + ("" if k == 1 else "s")


def _refs(citations: list[CitationResult], status: str) -> str:
    return ", ".join(f"[{c.citation.n}]" for c in citations if c.status == status)


def evaluate(assessment: Assessment | None, citations: list[CitationResult], review: Review | None,
             dtype: DocumentType, tier: Tier) -> GateResult:
    counts = {k: 0 for k in (*WEIGHTS, *CITE_STATUSES)}
    if assessment:
        for v in assessment.verdicts:
            counts[v.weight] += 1
    for c in citations:
        counts[c.status] += 1
    q, checks = dtype.quality, dtype.checks
    reasons: list[GateReason] = []

    def add(status: str, text: str) -> None:
        reasons.append(GateReason(status=status, text=text))

    if "evidence" in checks:
        if counts["unsupported"] > q.max_unsupported:
            add("blocked", f"{_n(counts['unsupported'], 'unsupported claim')}; this document type allows {q.max_unsupported}.")
        if counts["contradicted"] > q.max_contradicted:
            add("blocked", f"{_n(counts['contradicted'], 'contradicted claim')}; this document type allows {q.max_contradicted}.")
        if q.max_weak is not None and counts["weak"] > q.max_weak:
            add("attention", f"{_n(counts['weak'], 'weakly supported claim')}; this document type allows {q.max_weak}.")
        total = sum(counts[w] for w in WEIGHTS)
        if q.min_supported_share is not None and total and counts["supported"] / total < q.min_supported_share:
            add("attention", f"{counts['supported']} of {total} claims are supported ({counts['supported'] / total:.0%}); "
                             f"this document type needs at least {q.min_supported_share:.0%}.")
    if "citations" in checks:
        if q.citations_not_found_blocks and counts["not_found"]:
            add("blocked", f"{_n(counts['not_found'], 'citation')} not found ({_refs(citations, 'not_found')}); "
                           "this document type does not allow unverifiable references.")
        if q.citations_mismatch_attention and counts["mismatch"]:
            add("attention", f"{_n(counts['mismatch'], 'citation')} with details that do not match "
                             f"({_refs(citations, 'mismatch')}); a person should check them.")
    if q.require_reviewer and tier in ("T2", "T3"):
        if review is not None and review.decision == "rejected":
            add("blocked", f"The reviewer ({review.reviewer}) rejected this document.")
        elif review is None:
            add("attention", "Needs a named reviewer before filing.")

    reasons.sort(key=lambda r: _ORDER[r.status])
    if not reasons:
        bits = []
        if "evidence" in checks:
            bits.append(f"{counts['supported']} supported, {counts['weak']} weak, "
                        f"{counts['unsupported']} unsupported, {counts['contradicted']} contradicted")
        if "citations" in checks:
            bits.append(f"{counts['not_found']} citations not found")
        if q.require_reviewer and tier in ("T2", "T3") and review:
            bits.append(f"reviewed by {review.reviewer}")
        reasons = [GateReason(status="ready", text=f"Meets the bar for {dtype.name}: " + "; ".join(bits) + ".")]
    return GateResult(document_type=dtype.id, status=reasons[0].status, reasons=reasons, counts=counts)


def summary_line(result: GateResult) -> str:
    label = {"ready": "Ready to file", "attention": "Needs attention", "blocked": "Blocked"}[result.status]
    return f"{label}: " + " ".join(r.text for r in result.reasons)
