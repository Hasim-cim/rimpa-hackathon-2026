"""Claim splitting, deterministic linking rules, and weighing. The LLM never decides a weight."""

from __future__ import annotations

import json
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


def _split_key(body: str) -> str:
    """Cache key for a recorded AI split: the exact text and the model asked for."""
    from .hashing import sha256
    return f"split:{sha256(body.encode('utf-8'))}:{llm.MODEL}"


def recorded_split(conn, body: str) -> dict | None:
    """A split recorded earlier for this exact text and model: {claims, model_returned, at}, or None."""
    if conn is None:
        return None
    row = conn.execute("SELECT payload FROM citation_cache WHERE key=?", (_split_key(body),)).fetchone()
    return json.loads(row["payload"]) if row else None


def _record_split(conn, body: str, claims: list[str], model_returned: str) -> None:
    if conn is None:
        return
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db.upsert(conn, "citation_cache", "key", dict(key=_split_key(body), fetched_at=at,
              payload=json.dumps({"claims": claims, "model_returned": model_returned, "at": at})))
    conn.commit()


def _split(doc: Document, use_llm: bool | None, conn=None) -> tuple[list[Claim], str]:
    if doc.claims:
        return list(doc.claims), "seed"
    if use_llm is None:
        use_llm = llm.available()
    texts, method = _regex_split(doc.body), "sentence-split"
    if use_llm:
        rec = recorded_split(conn, doc.body)
        if rec:   # replay: the split really came from that model, when it was recorded
            texts, method = rec["claims"], f"llm:{rec['model_returned']} (recorded {rec['at'][:16].replace('T', ' ')} UTC)"
        else:
            try:
                got = _verbatim(llm.split_claims(doc.body), doc.body)
            except Exception:  # network, quota, malformed output: the check still runs, on plain sentences
                got = []
            if got and _covers(got, texts):
                returned = llm.LAST_MODEL_RETURNED or llm.MODEL
                texts, method = got, f"llm:{returned}"
                _record_split(conn, doc.body, got, returned)
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
        if amounts and not hit and rcase is not None:   # "$500 rent" and a case record holding rent_weekly (G1)
            topical = [k for k in _topic_fields(claim.text, rec)
                       if isinstance(rec.fields.get(k), (int, float)) and not isinstance(rec.fields.get(k), bool)]
            if topical:
                add("topic+field", f"claim gives an amount for {topical[0]}, which {rec.id} records")
        if _HOUSEHOLD.search(claim.text) and "occupants" in rec.fields:
            add("household", f"claim describes the household; {rec.id} records occupants = {rec.fields['occupants']}")
    return links



# ---------- facts must match, not just words (G1) ----------
# A sentence linked to a record by wording is only supported if its numbers, counts and dates are in a current
# authoritative record too. Deterministic: dollar amounts, "N days/weeks/months/years", "N adults/people/occupants",
# and dates written in full ("1 June 2026"). Month-only phrases ("June to August 2026") are not compared.

_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}
_FULL_DATE = re.compile(r"\b(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\s+(\d{4})\b", re.I)
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_QUANTITY = re.compile(r"\b(\d+)\s+(day|week|month|year)s?\b", re.I)
_NUMBER_WORDS = {w: i for i, w in enumerate(["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
                                             "nine", "ten"])}
_HEADCOUNT = re.compile(r"\b(\d+|" + "|".join(_NUMBER_WORDS) + r")\s+(adults?|people|persons?|occupants?)\b", re.I)
# topic words in a sentence -> the record fields that hold that fact (field names themselves also count)
FIELD_TOPICS = {"earnings": "amount_weekly", "wage": "amount_weekly", "wages": "amount_weekly",
                "income": "amount_weekly", "pay": "amount_weekly", "rent": "rent_weekly", "debt": "debt_amount",
                "utilities": "utilities_weekly", "occupants": "occupants", "household": "occupants"}


def _dates(text: str) -> set[str]:
    out = {f"{int(y):04d}-{_MONTHS[m.lower()]:02d}-{int(d):02d}" for d, m, y in _FULL_DATE.findall(text)}
    out |= {f"{y}-{m}-{d}" for y, m, d in _ISO_DATE.findall(text)}
    return out


def _record_dates(rec: SourceRecord) -> set[str]:
    return _dates(rec.content) | {str(v)[:10] for v in rec.fields.values() if isinstance(v, str) and _ISO_DATE.fullmatch(str(v)[:10])}


def _record_amounts(rec: SourceRecord) -> set[int]:
    return _amounts(rec.content) | {v for v in _numeric_fields(rec).values()}


def _quantities(text: str) -> set[tuple[int, str]]:
    return {(int(n), u.lower()) for n, u in _QUANTITY.findall(text)}


def _headcount(text: str) -> int | None:
    m = _HEADCOUNT.search(text)
    if not m:
        return None
    n = m.group(1).lower()
    return int(n) if n.isdigit() else _NUMBER_WORDS[n]


def _topic_fields(text: str, rec: SourceRecord) -> list[str]:
    words = set(re.findall(r"[a-z]+", text.lower()))
    named = {FIELD_TOPICS[w] for w in words if w in FIELD_TOPICS}
    named |= {k for k in rec.fields if any(part in words for part in k.split("_") if part not in ("amount", "weekly", "id"))}
    return [k for k in rec.fields if k in named]


def _field_for_amount(text: str, amt: int, rec: SourceRecord) -> str | None:
    """The record field this amount is about: the topic word nearest to the amount in the sentence ("$380 rent" →
    rent_weekly; "the $4,860 debt" → debt_amount). None when no topic word in the sentence names one of its fields."""
    spans = [m.span() for m in _MONEY.finditer(text)
             if int(round(float(m.group(1).replace(",", "")))) == amt]
    if not spans:
        return None
    best: tuple[int, str] | None = None
    for m in re.finditer(r"[a-z_]+", text.lower()):
        w = m.group(0)
        fields = {FIELD_TOPICS[w]} if w in FIELD_TOPICS else set()
        fields |= {k for k in rec.fields if w in k.split("_") and w not in ("amount", "weekly", "id")}
        fields &= set(rec.fields)
        if not fields:
            continue
        dist = min(abs(m.start() - s) if m.start() >= e else abs(s - m.end()) for s, e in spans)
        if best is None or dist < best[0]:
            best = (dist, sorted(fields)[0])
    return best[1] if best else None


def facts_check(claim: Claim, good: list[SourceRecord], other: list[SourceRecord]) -> tuple[str, str] | None:
    """(weight, reason) when a number, count or date in the sentence is not in a current authoritative record it links
    to; None when every fact is backed (or the sentence states none). Contradicted only on a clear field clash."""
    text = claim.text
    # dollar amounts
    for amt in sorted(_amounts(text)):
        if any(amt in _record_amounts(r) for r in good):
            continue
        for r in good:
            k = _field_for_amount(text, amt, r)       # pair the amount with the field it is about, not any field named
            v = r.fields.get(k) if k else None
            if (isinstance(v, (int, float)) and not isinstance(v, bool) and int(round(v)) != amt
                    and int(round(v)) not in _amounts(text)):   # a field matched by another amount here is not a clash
                return "contradicted", f"The claim says ${amt:,}, but {r.id} records {k} = {int(round(v)):,}."
        held = [r for r in other if amt in _record_amounts(r)]
        if held:
            return "weak", (f"${amt:,} rests only on records that cannot count as evidence: "
                            + ", ".join(f"{r.id} ({why_not_evidence(r)})" for r in held) + ".")
        if good:
            return "unsupported", f"${amt:,} is not in any current authoritative record it links to ({', '.join(r.id for r in good)})."
    # quantities with a unit: "28 days" against "21 days"
    for n, unit in sorted(_quantities(text)):
        held_units = [(r, q) for r in good for q in _quantities(r.content) if q[1] == unit]
        if held_units and not any(q[0] == n for _, q in held_units):
            r, q = held_units[0]
            return "contradicted", f"The claim says {n} {unit}s, but {r.id} says {q[0]} {unit}s."
    # head counts: "five adults" against occupants
    count = _headcount(text)
    if count is not None:
        for r in good:
            occ = r.fields.get("occupants")
            if isinstance(occ, (int, float)) and not isinstance(occ, bool) and int(occ) != count:
                return "contradicted", f"The claim says {count}, but {r.id} records occupants = {int(occ)}."
    # dates written in full
    claimed = _dates(text)
    if claimed and good:
        held_dates = set().union(*(_record_dates(r) for r in good))
        if held_dates:
            gone = sorted(claimed - held_dates)
            if gone:
                shown = ", ".join(gone)
                return "unsupported", f"{shown} is not in any current authoritative record it links to ({', '.join(r.id for r in good)})."
    return None

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

    # facts must match, not just words: numbers, counts and dates in a current authoritative record (G1)
    if linked:
        clash = facts_check(claim, [recs[r] for r in good], [recs[r] for r in linked if r not in good])
        if clash:
            return verdict(*clash)

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
    claims, method = _split(doc, use_llm, conn)
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

