"""Policy: what the information manager configures. The engine reads it; an LLM may only suggest a starting profile."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from . import llm, passport
from .db import ROOT, SEED_DIR
from .models import DocumentType, Policy, QualityBar, SectorPreset, SourceRecord

PRESETS_PATH = SEED_DIR / "policy_presets.json"
POLICY_PATH = Path(os.environ.get("RECORDCHECK_POLICY", ROOT / "data" / "policy.json"))
DEFAULT_PRESET = "commonwealth-agency"
DEFAULT_ORG = "Example Agency (prototype)"


def policy_path() -> Path:
    """Read the env var at call time so tests and deployments can redirect the file."""
    env = os.environ.get("RECORDCHECK_POLICY")
    return Path(env) if env else POLICY_PATH


# ---------- presets ----------

def load_presets() -> list[SectorPreset]:
    with open(PRESETS_PATH, encoding="utf-8") as f:
        return [SectorPreset(**p) for p in json.load(f)["presets"]]


def get_preset(preset_id: str) -> SectorPreset:
    for p in load_presets():
        if p.id == preset_id:
            return p
    raise KeyError(f"unknown sector preset: {preset_id}")


def from_preset(preset: SectorPreset, organisation: str, by: str) -> Policy:
    rules = passport.load_tier_rules()
    rules.retention_days = {**rules.retention_days, **preset.retention_days}
    return Policy(
        organisation=organisation, sector=preset.id, sector_name=preset.name,
        guidance=list(preset.guidance), document_types=[d.model_copy(deep=True) for d in preset.document_types],
        authoritative_systems=list(preset.authoritative_systems), tier_rules=rules,
        version="1", updated_by=by, updated_at=datetime.now(timezone.utc))


# ---------- persistence ----------

def save(policy: Policy, by: str, conn=None) -> Policy:
    """Bump the version, stamp who/when, write JSON. With a conn, the change is written to audit_log too."""
    try:
        n = int(policy.version)
    except ValueError:
        n = 0
    policy.version = str(n + 1)
    policy.updated_by = by
    policy.updated_at = datetime.now(timezone.utc)
    from . import db
    if db.database_url():
        # on Postgres the policy lives in the database: a file in /tmp would vanish with the instance
        store = conn if db.is_postgres(conn) else db.shared()
        db.upsert(store, "policy", "id", dict(id=1, payload=policy.model_dump_json(),
                                              updated_at=policy.updated_at.isoformat()))
        store.commit()
    else:
        p = policy_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(policy.model_dump_json(indent=2), encoding="utf-8")
    if conn is not None:
        from .passport import policy_hash
        bars = "; ".join(f"{d.id}: unsupported≤{d.quality.max_unsupported}, contradicted≤{d.quality.max_contradicted}, "
                         f"weak≤{'∞' if d.quality.max_weak is None else d.quality.max_weak}, reviewer={'yes' if d.quality.require_reviewer else 'no'}"
                         for d in policy.document_types)
        db.audit(conn, actor=by, action="policy.saved", subject=f"policy v{policy.version}",
                 detail=f"hash {policy_hash(policy)[:12]}; sector {policy.sector}; systems {len(policy.authoritative_systems)}; {bars}")
        conn.commit()
    return policy


def load() -> Policy:
    from . import db
    if db.database_url():
        row = db.shared().execute("SELECT payload FROM policy WHERE id=1").fetchone()
        if row:
            return Policy.model_validate_json(row["payload"])
    else:
        p = policy_path()
        if p.exists():
            return Policy.model_validate_json(p.read_text(encoding="utf-8"))
    pol = from_preset(get_preset(DEFAULT_PRESET), DEFAULT_ORG, by="Prototype default")
    return save(pol, by="Prototype default")


def reset() -> None:
    from . import db
    if db.database_url():
        store = db.shared()
        store.execute("DELETE FROM policy")
        store.commit()
    else:
        policy_path().unlink(missing_ok=True)


# ---------- strictness levels (the simple studio) ----------

class Level(BaseModel):
    id: Literal["strict", "standard", "light"]
    name: str
    use_for: str                             # plain words, shown next to the choice
    checks: list[Literal["citations", "evidence"]]
    quality: QualityBar


# Three named bars so an information manager picks one word instead of eight numbers. Each equals a bar the
# Commonwealth preset already ships, so choosing a level never invents a threshold. Exact numbers stay editable.
LEVELS: dict[str, Level] = {lv.id: lv for lv in (
    Level(id="strict", name="Strict", use_for="decisions about a person, a case or money",
          checks=["citations", "evidence"],
          quality=QualityBar(max_unsupported=0, max_contradicted=0, max_weak=1, min_supported_share=0.6,
                             citations_not_found_blocks=True, citations_mismatch_attention=True, require_reviewer=True)),
    Level(id="standard", name="Standard", use_for="advice, briefings and policy papers",
          checks=["citations", "evidence"],
          quality=QualityBar(max_unsupported=0, max_contradicted=0, max_weak=2, citations_not_found_blocks=True,
                             citations_mismatch_attention=True, require_reviewer=True)),
    Level(id="light", name="Light", use_for="working notes on a file",
          checks=["evidence"],
          quality=QualityBar(max_unsupported=1, max_contradicted=0, citations_not_found_blocks=True,
                             citations_mismatch_attention=False, require_reviewer=False)),
)}


def level_of(dtype: DocumentType) -> str | None:
    """The level whose bar and checks this type matches exactly, or None (a custom bar)."""
    return next((lv.id for lv in LEVELS.values()
                 if lv.quality == dtype.quality and sorted(lv.checks) == sorted(dtype.checks)), None)


def apply_level(dtype: DocumentType, level: str) -> DocumentType:
    lv = LEVELS[level]
    return dtype.model_copy(update={"quality": lv.quality.model_copy(), "checks": list(lv.checks)})


def new_type(name: str, level: str, tier: str, existing: list[DocumentType]) -> DocumentType:
    """A document type from a name and a level; the id is made from the name. ValueError on a blank or taken name."""
    name = " ".join(name.split())
    tid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not tid:
        raise ValueError("Give the document type a name.")
    if any(d.id == tid or d.name.casefold() == name.casefold() for d in existing):
        raise ValueError(f"A document type called {name!r} already exists.")
    return apply_level(DocumentType(id=tid, name=name, default_tier=tier), level)


def describe(dtype: DocumentType) -> str:
    """The bar in one plain sentence, for people who will never read the thresholds."""
    q, parts = dtype.quality, []
    if "evidence" in dtype.checks:
        un = "any unsupported claim" if q.max_unsupported == 0 else f"more than {q.max_unsupported} unsupported claim" \
             + ("s" if q.max_unsupported != 1 else "")
        parts.append(f"Blocked by {un} or {'any contradicted claim' if q.max_contradicted == 0 else f'more than {q.max_contradicted} contradicted'}")
        if q.max_weak is not None:
            parts.append("a closer look at any weak claim" if q.max_weak == 0
                         else f"a closer look after {q.max_weak} weak claim{'s' if q.max_weak != 1 else ''}")
        if q.min_supported_share is not None:
            parts.append(f"at least {q.min_supported_share:.0%} of claims supported")
    else:
        parts.append("Claims are not checked against records")
    if "citations" in dtype.checks:
        parts.append("references looked up" + ("; an unfindable one blocks" if q.citations_not_found_blocks else ""))
    parts.append("a named reviewer at T2 and T3" if q.require_reviewer else "no reviewer required")
    return "; ".join(parts) + "."


# ---------- lookups ----------

def doc_type(policy: Policy, type_id: str) -> DocumentType | None:
    return next((d for d in policy.document_types if d.id == type_id), None)


def authoritative(policy: Policy, record: SourceRecord) -> bool:
    """A record is evidence only if it is flagged authoritative AND its system is on the IM's list."""
    return record.authoritative and record.system in policy.authoritative_systems


# ---------- LLM suggestion (never decides anything) ----------

class Suggestion(BaseModel):
    """What suggest() returns: the preset to start from and the organisation name the model inferred.
    The preset's `description` is replaced by the model's rationale. The IM must still confirm."""
    preset: SectorPreset
    organisation: str


class _SuggestOut(BaseModel):
    preset_id: Literal["commonwealth-agency", "state-agency", "health-service", "local-council"]
    organisation: str
    rationale: str


def suggest(description: str) -> Suggestion | None:
    """Ask the model which preset fits. Returns None if the LLM is off, the text is empty, or anything fails."""
    if not description.strip() or not llm.available():
        return None
    try:
        presets = load_presets()
        menu = "\n".join(f"- {p.id}: {p.name}. {p.description}" for p in presets)
        prompt = ("Pick the sector preset that best fits this organisation, give the organisation's name if the "
                  "text states one (else a short generic label), and a one-sentence rationale. You only suggest "
                  f"a starting point; a records professional will confirm.\n\nPRESETS:\n{menu}\n\nDESCRIPTION:\n{description}")
        resp = llm._client().messages.parse(
            model=llm.MODEL, max_tokens=1024, messages=[{"role": "user", "content": prompt}], output_format=_SuggestOut)
        out = resp.parsed_output
        if out is None:
            return None
        preset = get_preset(out.preset_id).model_copy(update={"description": out.rationale})
        return Suggestion(preset=preset, organisation=out.organisation.strip() or DEFAULT_ORG)
    except Exception:
        return None
