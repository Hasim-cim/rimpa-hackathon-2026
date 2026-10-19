"""Claim splitting, deterministic linking rules, and weighing. The LLM never decides a weight."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable

from . import db, llm
from .models import (Assessment, Claim, ClaimLink, CitationResult, Document, Policy, SourceRecord, Verdict)

WEIGHTS = ("supported", "weak", "unsupported", "contradicted")

_STOP = set("""a an the of to in on and or for by with is are was were be been being has have had it its that this
which where would may can will than as at from not no other these those their there then so if into""".split())
# boilerplate words common to every hardship record; a phrase made of these alone is not distinctive
_GENERIC = {"delegate", "waive", "debt", "applicant", "case"}
_MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
_REF = re.compile(r"\[(\d+)\]")
_HOUSEHOLD = re.compile(r"\b(lives alone|living alone|alone|household)\b", re.I)
_ALONE = re.compile(r"\b(lives alone|living alone|alone)\b", re.I)
# "does not live alone", "doesn't live alone", "is not living alone", "never lived alone", "no longer lives alone"
_NOT_ALONE = re.compile(r"(?:\bnot|n't|\bnever|\bno longer)\s+(?:\w+\s+){0,2}?alone\b", re.I)


# ---------- splitting ----------

def _refs(text: str) -> list[int]:
    return [int(n) for n in _REF.findall(text)]


def _regex_split(body: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\[])", body.strip())
    return [p.strip() for p in parts if p.strip()]


def _split(doc: Document, use_llm: bool | None) -> tuple[list[Claim], str]:
    if doc.claims:
        return list(doc.claims), "seed"
    if use_llm is None:
        use_llm = llm.available()
    texts, method = _regex_split(doc.body), "sentence-split"
    if use_llm:
        try:
            got = _verbatim(llm.split_claims(doc.body), doc.body)
        except Exception:  # network, quota, malformed output: the check still runs, on plain sentences
            got = []
        if got and _covers(got, texts):
            texts, method = got, f"llm:{llm.LAST_MODEL_RETURNED or llm.MODEL}"
    claims = [Claim(id=f"c{i}", text=t, author=doc.default_author, position=i, citation_refs=_refs(t))
              for i, t in enumerate(texts, 1)]
    return claims, method


def _squash(text: str) -> str:
    return " ".join(text.split())


def _verbatim(claims: list[str], body: str) -> list[str]:
    """Keep only claims the model copied from the document; an invented sentence is never weighed."""
    flat = _squash(body)
    return [c for c in claims if _squash(c) in flat]


def _covers(claims: list[str], sentences: list[str]) -> bool:
    """Every sentence must contain at least one claim, so a model cannot drop a sentence from the check."""
    sq = [_squash(c) for c in claims]
    return all(any(c in _squash(s) or _squash(s) in c for c in sq) for s in sentences)


def split_claims(doc: Document, use_llm: bool | None = None) -> list[Claim]:
    return _split(doc, use_llm)[0]


# ---------- linking ----------

def _tokens(text: str) -> list[str]:
    text = re.sub(r"(?<=\d),(?=\d)", "", text.lower())
    text = _REF.sub(" ", text)
    return [t for t in re.findall(r"[a-z0-9]+", text) if t not in _STOP and t not in _GENERIC]


def _amounts(text: str) -> set[int]:
    return {int(round(float(m.replace(",", "")))) for m in _MONEY.findall(text)}


def _numeric_fields(rec: SourceRecord) -> dict[str, int]:
    return {k: int(round(v)) for k, v in rec.fields.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)}


def _shared_phrase(claim_toks: list[str], rec_toks: list[str], n: int = 3) -> str | None:
    grams = {tuple(rec_toks[i:i + n]) for i in range(len(rec_toks) - n + 1)}
    starts = [i for i in range(len(claim_toks) - n + 1) if tuple(claim_toks[i:i + n]) in grams]
    best: tuple[int, int] | None = None   # (start, end) of the longest merged run of matching trigrams
    i = 0
    while i < len(starts):
        j = i
        while j + 1 < len(starts) and starts[j + 1] == starts[j] + 1:
            j += 1
        span = (starts[i], starts[j] + n)
        if best is None or span[1] - span[0] > best[1] - best[0]:
            best = span
        i = j + 1
    return " ".join(claim_toks[best[0]:best[1]]) if best else None


def link_claim(claim: Claim, records: list[SourceRecord], case_id: str | None = None) -> list[ClaimLink]:
    links: list[ClaimLink] = []
    amounts = _amounts(claim.text)
    claim_toks = _tokens(claim.text)
    for rec in records:
        rcase = rec.fields.get("case_id")
        if rcase is not None and rcase != case_id:   # no case on the document → only shared records
            continue

        def add(rule: str, note: str) -> None:
            links.append(ClaimLink(claim_id=claim.id, record_id=rec.id, rule=rule, note=note))

        hit = [(k, v) for k, v in _numeric_fields(rec).items() if v in amounts]
        if hit:
            k, v = hit[0]
            add("case_id+amount", f"${v:,} in the claim equals field '{k}' of {rec.id}")
        phrase = _shared_phrase(claim_toks, _tokens(rec.content))
        if phrase:
            add("keyphrase", f"shared phrase '{phrase}' appears in {rec.id}")
        if _HOUSEHOLD.search(claim.text) and "occupants" in rec.fields:
            add("household", f"claim describes the household; {rec.id} records occupants = {rec.fields['occupants']}")
    return links


# ---------- weighing ----------

def is_evidence(rec: SourceRecord, document_type: str | None = None) -> bool:
    """Current, authoritative, and (when the document type is known) not excluded by the record's intended use."""
    return rec.authoritative and rec.status == "current" and not (document_type and document_type in rec.not_for)


def weigh(claim: Claim, links: list[ClaimLink], records, citations: Iterable[CitationResult] = (),
          document_type: str | None = None, type_name: str | None = None) -> Verdict:
    recs = records if isinstance(records, dict) else {r.id: r for r in records}
    cits = {c.citation.n: c for c in citations}
    linked = list(dict.fromkeys(l.record_id for l in links if l.record_id in recs))
    good = [r for r in linked if is_evidence(recs[r], document_type)]

    def verdict(weight: str, reason: str) -> Verdict:
        return Verdict(claim_id=claim.id, weight=weight, links=links, reason=reason)

    # contradiction: a current authoritative record's field disagrees with the claim
    if _ALONE.search(claim.text):
        negated = bool(_NOT_ALONE.search(claim.text))
        for rid in good:
            occ = recs[rid].fields.get("occupants")
            if not isinstance(occ, (int, float)) or isinstance(occ, bool):
                continue
            if not negated and occ > 1:
                return verdict("contradicted",
                               f"The claim says the applicant lives alone, but {rid} records {int(occ)} occupants.")
            if negated and occ == 1:
                return verdict("contradicted",
                               f"The claim says the applicant does not live alone, but {rid} records 1 occupant.")

    missing = [n for n in claim.citation_refs if n in cits and cits[n].status == "not_found"]
    ns = ", ".join(f"[{n}]" for n in missing)
    if missing and good:
        return verdict("supported",
                       f"Supported by current authoritative record(s) {', '.join(good)}. "
                       f"Citation {ns} could not be found, so the content holds but the reference must be fixed.")
    if missing:
        return verdict("unsupported",
                       f"Citation {ns} could not be found in Crossref or OpenAlex, so the claim has no verifiable source.")
    ext = [n for n in claim.citation_refs if n in cits and cits[n].status in ("found", "mismatch")]
    if not linked:
        if ext:
            return verdict("weak", "Rests on an external source that exists, not on an organisational record. "
                                   "A person should confirm it is appropriate authority.")
        return verdict("unsupported", "No authoritative record was found that supports this statement.")
    if good:
        return verdict("supported", f"Supported by current authoritative record(s) {', '.join(good)}.")

    return verdict("weak", "Only supported by records that cannot count as evidence: "
                           + ", ".join(f"{r} ({why_not_evidence(recs[r], document_type, type_name)})"
                                       for r in linked) + ".")


def why_not_evidence(rec: SourceRecord, document_type: str | None = None, type_name: str | None = None) -> str:
    """Why a record does not count as evidence, in the information manager's terms; "" if it does."""
    if rec.authoritative and rec.status == "current" and document_type and document_type in rec.not_for:
        use = f": {rec.purpose}" if rec.purpose else ""
        return f"its intended use excludes {type_name or document_type}{use}"
    if rec.status == "superseded":
        return f"superseded by {rec.superseded_by}" if rec.superseded_by else "superseded"
    if rec.status == "draft":
        return "a draft, not the approved version"
    if rec.status == "disposed":
        return "disposed"
    if not rec.authoritative:
        return "not from an authoritative system"
    return ""


# ---------- assess ----------

def summary(verdicts: Iterable[Verdict]) -> dict[str, int]:
    out = {w: 0 for w in WEIGHTS}
    for v in verdicts:
        out[v.weight] += 1
    return out


def assess(doc: Document, conn, citations: Iterable[CitationResult] = (), use_llm: bool | None = None,
           policy: Policy | None = None, document_type: str | None = None) -> Assessment:
    """With a document type, a record whose intended use excludes that type (`not_for`) is not evidence for it."""
    citations = list(citations)
    records = db.get_records(conn)
    if policy is not None:
        # records from systems the information manager has not listed are not evidence; copies, DB untouched
        records = [r if (r.system in policy.authoritative_systems or not r.authoritative)
                   else r.model_copy(update={"authoritative": False}) for r in records]
    recs = {r.id: r for r in records}
    claims, method = _split(doc, use_llm)
    dtype = next((d for d in policy.document_types if d.id == document_type), None) if policy and document_type else None
    name = dtype.name if dtype else document_type
    verdicts = [weigh(c, link_claim(c, records, doc.case_id), recs, citations, document_type, name) for c in claims]
    return Assessment(document_id=doc.id, claims=claims, verdicts=verdicts,
                      assessed_at=datetime.now(timezone.utc), method=method)


def reassess(assessment: Assessment, conn, citations: Iterable[CitationResult] = (),
             policy: Policy | None = None, document_type: str | None = None) -> Assessment:
    """Re-weigh a caller-supplied assessment on the server: keep its claims, recompute every link and weight.
    A verdict sent over the API is never trusted as sent."""
    ids = [c.id for c in assessment.claims]
    if len(set(ids)) != len(ids) or sorted(ids) != sorted(v.claim_id for v in assessment.verdicts):
        raise ValueError("assessment verdicts do not match its claims; send the claims as /check returned them")
    known = db.get_document(conn, assessment.document_id)
    claims = [c.model_copy(update={"citation_refs": _refs(c.text)}) for c in assessment.claims]
    doc = Document(id=assessment.document_id, title=known.title if known else "", body="",
                   case_id=known.case_id if known else None, claims=claims)
    return assess(doc, conn, citations, use_llm=False, policy=policy,
                  document_type=document_type).model_copy(update={"method": assessment.method})


# ---------- display ----------

_RULE_WORDS = {"case_id+amount": "exact field match", "keyphrase": "shared phrase", "household": "field check"}
_WEIGHT_WORDS = {
    "supported": "supported by authoritative records",
    "weak": "weak: only an external source, or a record that cannot count as evidence",
    "unsupported": "no authoritative record found",
    "contradicted": "contradicted by a current record",
}


def claim_stage(v: Verdict) -> tuple[str, str]:
    """(stage, strength) for display: which linking rules matched which records, and the weight in words.
    Presentation only: the strength comes from v.weight as weigh() set it, never recomputed."""
    if v.links:
        by_rule: dict[str, list[str]] = {}
        for l in v.links:
            ids = by_rule.setdefault(_RULE_WORDS.get(l.rule, l.rule), [])
            if l.record_id not in ids:
                ids.append(l.record_id)
        stage = "Step 1: checked against records, " + "; ".join(f"{rule} ({', '.join(ids)})" for rule, ids in by_rule.items())
    else:
        stage = "Step 1: no record linked"
    return stage, _WEIGHT_WORDS.get(v.weight, "not weighed; a person confirms")


def relied_on(assessment: Assessment, conn, policy: Policy | None = None, document_type: str | None = None) -> list[str]:
    """The records an output's claims rest on: linked records that count as evidence for this document. A record that
    matched only on wording but does not count (superseded, a draft, outside its intended use) is not a source."""
    out: list[str] = []
    for rid in dict.fromkeys(l.record_id for v in assessment.verdicts for l in v.links):
        r = db.get_record(conn, rid)
        if r is None:
            continue
        if policy is not None and r.authoritative and r.system not in policy.authoritative_systems:
            r = r.model_copy(update={"authoritative": False})
        if is_evidence(r, document_type):
            out.append(rid)
    return sorted(out)

