"""SQLite schema, connection and seed loader. JSON columns hold the pydantic payloads."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from .hashing import sha256
from .models import AIEvent, Document, ModelRegistryEntry, Passport, SourceRecord

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "data" / "seed"
DEFAULT_DB = ROOT / "data" / "recordcheck.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
  id TEXT PRIMARY KEY, status TEXT NOT NULL, authoritative INTEGER NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY, case_id TEXT, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_events (
  id TEXT PRIMARY KEY, app_id TEXT NOT NULL, created TEXT NOT NULL, model_returned TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS passports (
  record_id TEXT PRIMARY KEY, event_id TEXT NOT NULL, tier TEXT NOT NULL, model_returned TEXT NOT NULL,
  created TEXT NOT NULL, hash TEXT NOT NULL, prev_hash TEXT, seq INTEGER NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_registry (
  model_id TEXT PRIMARY KEY, provider TEXT NOT NULL, status TEXT NOT NULL, effective_from TEXT, reason TEXT, marked_by TEXT);
CREATE TABLE IF NOT EXISTS review_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL, reason TEXT NOT NULL, queued_by TEXT NOT NULL,
  queued_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open');
CREATE TABLE IF NOT EXISTS citation_cache (
  key TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS disposal_register (
  record_id TEXT PRIMARY KEY, tier TEXT NOT NULL, created TEXT NOT NULL, disposed_at TEXT NOT NULL,
  approved_by TEXT NOT NULL, authority TEXT NOT NULL, reason TEXT NOT NULL, hash_retained TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, subject TEXT, detail TEXT);
"""


def db_path() -> Path:
    return Path(os.environ.get("RECORDCHECK_DB", DEFAULT_DB))


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, detect_types=0, check_same_thread=False)  # Streamlit and FastAPI use worker threads
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # disposed passports keep their row, hash and chain position; the content in payload is replaced by a stub
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(passports)")}
    if "disposed_at" not in cols:
        conn.execute("ALTER TABLE passports ADD COLUMN disposed_at TEXT")
    conn.commit()


def is_seeded(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM records").fetchone()[0] > 0


def _load(name: str):
    with open(SEED_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def audit(conn: sqlite3.Connection, actor: str, action: str, subject: str | None = None, detail: str = "", at: str | None = None) -> None:
    from datetime import datetime, timezone
    conn.execute(
        "INSERT INTO audit_log(at, actor, action, subject, detail) VALUES (?,?,?,?,?)",
        (at or datetime.now(timezone.utc).isoformat(timespec="seconds"), actor, action, subject, detail),
    )


def seed(conn: sqlite3.Connection, *, force: bool = False) -> dict[str, int]:
    """Load data/seed/*.json. Idempotent unless force=True (then wipes and reloads)."""
    if force:
        for t in ("records", "documents", "ai_events", "passports", "model_registry", "review_queue", "audit_log"):
            conn.execute(f"DELETE FROM {t}")
    elif is_seeded(conn):
        return {}

    counts: dict[str, int] = {}

    records = [SourceRecord(**r) for r in _load("records.json")]
    for r in records:
        r.hash = r.hash or sha256(r.content)
        conn.execute(
            "INSERT OR REPLACE INTO records(id,status,authoritative,created,payload) VALUES (?,?,?,?,?)",
            (r.id, r.status, int(r.authoritative), r.created.isoformat(), r.model_dump_json()),
        )
    counts["records"] = len(records)

    docs = [Document(**d) for d in _load("documents.json")]
    for d in docs:
        conn.execute("INSERT OR REPLACE INTO documents(id,case_id,payload) VALUES (?,?,?)", (d.id, d.case_id, d.model_dump_json()))
    counts["documents"] = len(docs)

    for m in _load("model_registry.json"):
        e = ModelRegistryEntry(**m)
        conn.execute(
            "INSERT OR REPLACE INTO model_registry VALUES (?,?,?,?,?,?)",
            (e.model_id, e.provider, e.status, e.effective_from.isoformat() if e.effective_from else None, e.reason, e.marked_by),
        )
    counts["model_registry"] = len(_load("model_registry.json"))

    # Past AI events and their passports. Seeded passports are pre-hashed in the file so the chain is stable;
    # passport.py appends to this chain at runtime.
    events = [AIEvent(**e) for e in _load("ai_events.json")]
    for e in events:
        conn.execute(
            "INSERT OR REPLACE INTO ai_events(id,app_id,created,model_returned,payload) VALUES (?,?,?,?,?)",
            (e.id, e.app_id, e.created.isoformat(), e.model_returned, e.model_dump_json()),
        )
    counts["ai_events"] = len(events)

    passports = [Passport(**p) for p in _load("passports.json")]
    for i, p in enumerate(passports):
        insert_passport(conn, p, seq=i + 1)
    counts["passports"] = len(passports)

    audit(conn, "system", "seed", None, json.dumps(counts))
    conn.commit()
    return counts


def insert_passport(conn: sqlite3.Connection, p: Passport, seq: int | None = None) -> None:
    if seq is None:
        seq = (conn.execute("SELECT COALESCE(MAX(seq),0) FROM passports").fetchone()[0] or 0) + 1
    conn.execute(
        "INSERT OR REPLACE INTO passports(record_id,event_id,tier,model_returned,created,hash,prev_hash,seq,payload) VALUES (?,?,?,?,?,?,?,?,?)",
        (p.record.id, p.event_id, p.business.tier, p.agent.model_returned, p.record.created.isoformat(),
         p.integrity.hash, p.integrity.prev_hash, seq, p.model_dump_json()),
    )


# ---------- readers ----------

def get_records(conn: sqlite3.Connection) -> list[SourceRecord]:
    return [SourceRecord.model_validate_json(r["payload"]) for r in conn.execute("SELECT payload FROM records ORDER BY id")]


def get_record(conn: sqlite3.Connection, record_id: str) -> SourceRecord | None:
    row = conn.execute("SELECT payload FROM records WHERE id=?", (record_id,)).fetchone()
    return SourceRecord.model_validate_json(row["payload"]) if row else None


def get_document(conn: sqlite3.Connection, doc_id: str) -> Document | None:
    row = conn.execute("SELECT payload FROM documents WHERE id=?", (doc_id,)).fetchone()
    return Document.model_validate_json(row["payload"]) if row else None


def get_documents(conn: sqlite3.Connection) -> list[Document]:
    return [Document.model_validate_json(r["payload"]) for r in conn.execute("SELECT payload FROM documents ORDER BY id")]


def get_event(conn: sqlite3.Connection, event_id: str) -> AIEvent | None:
    row = conn.execute("SELECT payload FROM ai_events WHERE id=?", (event_id,)).fetchone()
    return AIEvent.model_validate_json(row["payload"]) if row else None


def get_passport(conn: sqlite3.Connection, record_id: str) -> Passport | None:
    row = conn.execute("SELECT payload FROM passports WHERE record_id=?", (record_id,)).fetchone()
    return Passport.model_validate_json(row["payload"]) if row else None


def get_passports(conn: sqlite3.Connection) -> list[Passport]:
    return [Passport.model_validate_json(r["payload"]) for r in conn.execute("SELECT payload FROM passports ORDER BY seq")]


def latest_passport_hash(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT hash FROM passports ORDER BY seq DESC LIMIT 1").fetchone()
    return row["hash"] if row else None


def get_model_registry(conn: sqlite3.Connection) -> list[ModelRegistryEntry]:
    out = []
    for r in conn.execute("SELECT * FROM model_registry ORDER BY model_id"):
        out.append(ModelRegistryEntry(model_id=r["model_id"], provider=r["provider"], status=r["status"],
                                      effective_from=r["effective_from"], reason=r["reason"] or "", marked_by=r["marked_by"]))
    return out


def open_db(path: Path | None = None) -> sqlite3.Connection:
    """connect + init + seed in one call. What the app and API use."""
    conn = connect(path)
    init(conn)
    seed(conn)
    return conn
