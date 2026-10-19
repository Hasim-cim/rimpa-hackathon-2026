"""Connector contract (I1): where authoritative records come from, and where a filed passport goes back to.

The engine reads records through a RecordSource and files passports through a PassportSink, so it never calls a vendor
API directly; a records system plugs in as one adapter. The seed database is the first adapter of both. A real adapter
(I2) is chosen from the connector research and is not named as supported until it has run against the real system.
No LLM.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from . import db
from .models import Passport, SourceRecord


class FiledReceipt(BaseModel):
    """What a records system says after it takes a passport back: where it now lives."""
    record_id: str                           # the passport's record id
    system: str                              # the records system that holds it now
    location: str                            # that system's own reference (container, path, URI)
    filed_at: datetime


@runtime_checkable
class RecordSource(Protocol):
    """Authoritative records where they already live: status, superseded-by, purpose and review date included."""
    name: str

    def list_records(self) -> list[SourceRecord]: ...

    def get_record(self, record_id: str) -> SourceRecord | None: ...


@runtime_checkable
class PassportSink(Protocol):
    """Files a passport back into the records system, as a record or as metadata on the record it describes."""
    name: str

    def file(self, passport: Passport) -> FiledReceipt: ...


class SeedDbSource:
    """The prototype's own database as a RecordSource (local SQLite or Neon)."""
    name = "Record Check database"

    def __init__(self, conn):
        self.conn = conn

    def list_records(self) -> list[SourceRecord]:
        return db.get_records(self.conn)

    def get_record(self, record_id: str) -> SourceRecord | None:
        return db.get_record(self.conn, record_id)


class SeedDbSink:
    """The prototype's own database as a PassportSink. The passport is already in the chain (passport.build writes it);
    filing it back means a receipt and an audit entry, as a records system would give."""
    name = "Record Check database"

    def __init__(self, conn):
        self.conn = conn

    def file(self, passport: Passport) -> FiledReceipt:
        if db.get_passport(self.conn, passport.record.id) is None:
            raise KeyError(f"{passport.record.id} is not in the chain; issue it with passport.build first")
        receipt = FiledReceipt(record_id=passport.record.id, system=self.name,
                               location=f"passports/{passport.record.id}", filed_at=datetime.now(timezone.utc))
        db.audit(self.conn, actor="Record Check", action="passport.filed_back", subject=passport.record.id,
                 detail=f"{receipt.system}: {receipt.location}")
        self.conn.commit()
        return receipt
