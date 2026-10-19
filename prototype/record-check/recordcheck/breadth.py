"""How broad and how current the evidence is: the rule behind the passport's Bias check and the dashboard's
narrow-evidence signal, in one place so the two never disagree. Narrow evidence is one way bias gets in; this rule never
says a statement is unbiased. No LLM.
"""

from __future__ import annotations

from .evidence import why_not_evidence
from .models import Policy, SourceRecord
from .policy import authoritative

METHOD = "How broad and how current the evidence is; narrow evidence is one way bias gets in."


def weak_reason(rec: SourceRecord | None, policy: Policy | None, doc_type: str | None) -> str | None:
    """Why a source cannot count for this document, or None if it can."""
    if rec is None:
        return "not in the records system"
    if policy is not None and not authoritative(policy, rec):
        return "not from an authoritative system"
    if policy is None and not rec.authoritative:
        return "not from an authoritative system"
    if rec.status in ("draft", "superseded", "disposed") or bool(doc_type and doc_type in rec.not_for):
        return why_not_evidence(rec, doc_type) or rec.status
    return None


def narrow(ids: list[str], recs: dict[str, SourceRecord], policy: Policy | None,
           doc_type: str | None, strict: bool = False) -> str | None:
    """Why a statement (or an older passport) rests on narrow evidence, or None if it rests on two or more current
    authoritative sources across two or more systems. No sources at all is not narrow (nothing to judge)."""
    ids = list(dict.fromkeys(ids))
    if not ids:
        return None
    # A statement's links: judge the records it rests on; a wording-only match on a record that cannot count is not a
    # source (as evidence.relied_on). strict (a passport's declared sources): any source that cannot count is narrow.
    counted = [i for i in ids if weak_reason(recs.get(i), policy, doc_type) is None]
    if strict and len(counted) < len(ids):
        i = next(i for i in ids if i not in counted)
        return f"rests on a record that cannot count ({i}: {weak_reason(recs.get(i), policy, doc_type)})"
    if not counted:
        i = ids[0]
        return f"rests on a record that cannot count ({i}: {weak_reason(recs.get(i), policy, doc_type)})"
    ids = counted
    if len(ids) == 1:
        return f"rests on one source ({ids[0]})"
    systems = sorted({recs[i].system for i in ids})
    if len(systems) == 1:
        return f"all sources are from one system ({systems[0]})"
    return None


def rests_on(ids: list[str], recs: dict[str, SourceRecord], policy: Policy | None, doc_type: str | None,
             strict: bool = False) -> bool:
    """True when the evidence is narrow (the dashboard's signal)."""
    return narrow(ids, recs, policy, doc_type, strict) is not None
