"""Policy: what the information manager configures. The engine reads it; an LLM may only suggest a starting profile."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from . import llm, passport
from .db import ROOT, SEED_DIR
from .models import DocumentType, Policy, SectorPreset, SourceRecord

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
    p = policy_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(policy.model_dump_json(indent=2), encoding="utf-8")
    if conn is not None:
        from . import db
        from .passport import policy_hash
        bars = "; ".join(f"{d.id}: unsupported≤{d.quality.max_unsupported}, contradicted≤{d.quality.max_contradicted}, "
                         f"weak≤{'∞' if d.quality.max_weak is None else d.quality.max_weak}, reviewer={'yes' if d.quality.require_reviewer else 'no'}"
                         for d in policy.document_types)
        db.audit(conn, actor=by, action="policy.saved", subject=f"policy v{policy.version}",
                 detail=f"hash {policy_hash(policy)[:12]}; sector {policy.sector}; systems {len(policy.authoritative_systems)}; {bars}")
        conn.commit()
    return policy


def load() -> Policy:
    p = policy_path()
    if p.exists():
        return Policy.model_validate_json(p.read_text(encoding="utf-8"))
    pol = from_preset(get_preset(DEFAULT_PRESET), DEFAULT_ORG, by="Prototype default")
    return save(pol, by="Prototype default")


def reset() -> None:
    policy_path().unlink(missing_ok=True)


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
