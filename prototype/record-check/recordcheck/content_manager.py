"""Content Manager adapter (I2): a RecordSource and PassportSink over Content Manager-shaped records. No network.

This is a CONTRACT TEST against Content Manager-shaped records, not an integration with OpenText Content Manager. The
read side maps recorded fixtures (data/connectors/content_manager_records.json, marked "shape": "assumed") into
SourceRecords; the write side turns a filed passport into a Create Record request with the passport JSON as an
attached electronic file, written to a local outbox and request log. Property and operation names come from Kapish's
Content Manager Power Connect connector on Microsoft Learn, not the official ServiceAPI reference (see
research/records-connectors-2026-10-19.md). Swapping the fixtures for a live ServiceAPI is the step not taken here.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .connectors import FiledReceipt
from .db import ROOT
from .models import Passport, SourceRecord

FIXTURES = ROOT / "data" / "connectors" / "content_manager_records.json"
OUTBOX = ROOT / "data" / "outbox" / "content_manager"


class CMConfig(BaseModel):
    """How Content Manager's records map onto Record Check's. The rules are DECLARED here, never guessed: Content Manager
    has no standard current/superseded field, so the agency names the field it uses."""
    system: str = "Content Manager"                      # the name the policy lists as an authoritative system
    superseded_field: str = "SupersededBy"               # additional field naming the record that replaced this one
    draft_when_not_finalised: bool = True                # no RecordDateFinalized -> draft (does not count as evidence)
    case_field: str = "CaseNumber"                       # additional field holding the case id the linking rules use
    passport_record_type: str = "Record Check Passport"  # record type the passport is created as


def _date(v: str | None) -> date | None:
    return datetime.fromisoformat(v).date() if v else None


def to_source_record(r: dict[str, Any], cfg: CMConfig) -> SourceRecord:
    """One Content Manager record → a SourceRecord, by the declared rules."""
    extra = dict(r.get("Fields") or {})
    replaced_by = extra.pop(cfg.superseded_field, None)
    status = "superseded" if replaced_by else ("draft" if cfg.draft_when_not_finalised and not r.get("RecordDateFinalized")
                                               else "current")
    fields: dict[str, Any] = {k[0].lower() + k[1:] if k != cfg.case_field else "case_id": v
                              for k, v in extra.items() if v is not None}
    fields["record_type"] = r.get("RecordRecordType")
    fields["retention_schedule"] = r.get("RecordRetentionSchedule")
    return SourceRecord(id=r["RecordNumber"], title=r.get("RecordTitle") or r["RecordNumber"], system=cfg.system,
                        authoritative=True, status=status, superseded_by=replaced_by,
                        created=_date(r.get("RecordDateRegistered")) or date.today(),
                        created_by=r.get("RecordOwnerLocation") or "unknown", content=r.get("RecordNotes") or "",
                        fields=fields)


class ContentManagerSource:
    """RecordSource over Content Manager-shaped Find Records results (fixtures)."""
    name = "Content Manager (contract test, assumed shape)"

    def __init__(self, fixtures: Path = FIXTURES, cfg: CMConfig | None = None):
        self.cfg = cfg or CMConfig()
        data = json.loads(Path(fixtures).read_text(encoding="utf-8"))
        self.shape = data.get("shape", "unknown")
        self._records = [to_source_record(r, self.cfg) for r in data.get("Results", [])]

    def list_records(self) -> list[SourceRecord]:
        return list(self._records)

    def get_record(self, record_id: str) -> SourceRecord | None:
        return next((r for r in self._records if r.id == record_id), None)


def create_record_request(p: Passport, cfg: CMConfig, attachment: str) -> dict[str, Any]:
    """The Create Record (Document) request a filed passport becomes, with Attach Electronic File for its JSON."""
    return {
        "operation": "Create Record",
        "RecordRecordType": cfg.passport_record_type,
        "RecordTypedTitle": f"Record passport {p.record.id}: {p.record.title}",
        "RecordNotes": (f"Tier {p.business.tier}; filing gate {p.business.gate or 'not recorded'}; "
                        f"model {p.agent.model_returned}; hash {p.integrity.hash}"),
        "RecordExternalReference": p.record.id,
        "then": {"operation": "Attach Electronic File", "File": attachment},
    }


class ContentManagerSink:
    """PassportSink: writes the Create Record request and the passport JSON to a local outbox, plus a request log.
    Nothing is sent: on stage this is 'a contract test against Content Manager-shaped records'."""
    name = "Content Manager outbox (contract test)"

    def __init__(self, outbox: Path = OUTBOX, cfg: CMConfig | None = None):
        self.outbox = Path(outbox)
        self.cfg = cfg or CMConfig()

    def file(self, passport: Passport) -> FiledReceipt:
        self.outbox.mkdir(parents=True, exist_ok=True)
        stem = passport.record.id.replace("/", "-")
        attachment = f"{stem}.passport.json"
        (self.outbox / attachment).write_text(passport.model_dump_json(indent=2), encoding="utf-8")
        request = create_record_request(passport, self.cfg, attachment)
        (self.outbox / f"{stem}.create-record.json").write_text(json.dumps(request, indent=2), encoding="utf-8")
        now = datetime.now(timezone.utc)
        with open(self.outbox / "requests.log.jsonl", "a", encoding="utf-8") as log:
            log.write(json.dumps({"at": now.isoformat(), "record_id": passport.record.id,
                                  "operation": "Create Record", "attachment": attachment, "sent": False}) + "\n")
        return FiledReceipt(record_id=passport.record.id, system=self.name,
                            location=f"outbox/{stem}.create-record.json", filed_at=now)
