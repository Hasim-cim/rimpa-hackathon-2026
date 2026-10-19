"""Schema, connection and seed loader. JSON columns hold the pydantic payloads.

SQLite by default (local runs and the tests: offline, no setup). With DATABASE_URL set, Postgres through `PgConn`, a
thin adapter with the same `execute`/`commit` surface as sqlite3, so the engine's SQL (`?` parameters, rows read by
name or position) runs unchanged on both.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

from .hashing import sha256
from .models import AIEvent, Document, ModelRegistryEntry, Passport, SourceRecord

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "data" / "seed"
DEFAULT_DB = ROOT / "data" / "recordcheck.sqlite"
HERE = Path(__file__).resolve().parent

# advisory-lock keys: one writer at a time for the passport chain, and for first-connect schema + seed
CHAIN_LOCK = 4_120_001
SEED_LOCK = 4_120_002


def db_path() -> Path:
    return Path(os.environ.get("RECORDCHECK_DB", DEFAULT_DB))


def database_url() -> str | None:
    """Postgres when set (Neon on Vercel). Read at call time so tests can unset it."""
    return os.environ.get("DATABASE_URL") or None


# ---------- Postgres adapter ----------

class _Row(tuple):
    """sqlite3.Row-alike: index by position or by column name, and keys()."""

    def __new__(cls, names: list[str], values):
        row = super().__new__(cls, values)
        row._names = names
        return row

    def __getitem__(self, k):
        return super().__getitem__(self._names.index(k) if isinstance(k, str) else k)

    def keys(self) -> list[str]:
        return list(self._names)


def _row_factory(cursor):
    names = [d.name for d in cursor.description] if cursor.description else []
    return lambda values: _Row(names, values)


def _is_plain_read(sql: str) -> bool:
    head = sql.lstrip().upper()
    return head.startswith("SELECT") and "PG_ADVISORY" not in head


class PgConn:
    """One psycopg connection behind the sqlite3 surface the engine uses. Thread-safe (calls are serialised).
    Reconnects when Neon has dropped an idle connection, but only between transactions: a write that was half
    done is never silently replayed."""

    def __init__(self, url: str):
        self.url = url
        self._mu = threading.RLock()
        self._c = None
        self._connect()

    def _connect(self) -> None:
        import psycopg
        # prepare_threshold=None: no server-side prepared statements, so Neon's pooled (pgbouncer) URL works
        self._c = psycopg.connect(self.url, row_factory=_row_factory, prepare_threshold=None, connect_timeout=10)

    def execute(self, sql: str, params=()):
        import psycopg
        from psycopg.pq import TransactionStatus
        if params:
            sql = sql.replace("%", "%%").replace("?", "%s")
        with self._mu:
            for attempt in (0, 1):
                if self._c.closed:
                    self._connect()
                between = self._c.info.transaction_status == TransactionStatus.IDLE
                try:
                    cur = self._c.execute(sql, tuple(params) if params else None)
                    if between and _is_plain_read(sql):
                        self._c.commit()   # results are already buffered; never leave a read idle in transaction
                    return cur
                except psycopg.OperationalError:
                    try:
                        self._c.close()
                    finally:
                        self._connect()
                    if attempt or not between:
                        raise
                except Exception:
                    self._c.rollback()   # Postgres aborts the whole transaction on an error; start clean
                    raise

    def commit(self) -> None:
        with self._mu:
            self._c.commit()

    def rollback(self) -> None:
        with self._mu:
            if not self._c.closed:
                self._c.rollback()

    def close(self) -> None:
        with self._mu:
            self._c.close()


_shared: PgConn | None = None
_shared_mu = threading.Lock()


def shared() -> PgConn:
    """One process-wide Postgres connection, schema and seed ready, for code that is given none (the policy store)."""
    global _shared
    with _shared_mu:
        if _shared is None or _shared.url != database_url():
            _shared = open_db()
        return _shared


def is_postgres(conn) -> bool:
    return isinstance(conn, PgConn)


def lock(conn, key: int) -> None:
    """Serialise writers until the next commit or rollback. Postgres: a transaction-scoped advisory lock (safe behind
    a transaction pooler). SQLite: BEGIN IMMEDIATE, which takes the file's write lock."""
    if is_postgres(conn):
        conn.execute("SELECT pg_advisory_xact_lock(?)", (key,))
    elif not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")


def upsert(conn, table: str, key: str, row: dict) -> None:
    """INSERT, or UPDATE on a key clash. The ON CONFLICT form works on SQLite (3.24+) and Postgres."""
    cols = ", ".join(row)
    sets = ", ".join(f"{c}=excluded.{c}" for c in row if c != key)
    conn.execute(f"INSERT INTO {table}({cols}) VALUES ({','.join('?' * len(row))}) ON CONFLICT({key}) DO UPDATE SET {sets}",
                 tuple(row.values()))


# ---------- connection and schema ----------

def connect(path: Path | None = None):
    """Postgres when DATABASE_URL is set and no explicit path is given; SQLite otherwise."""
    url = database_url()
    if url and path is None:
        return PgConn(url)
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, detect_types=0, check_same_thread=False)  # Streamlit and FastAPI use worker threads
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init(conn) -> None:
    if is_postgres(conn):
        lock(conn, SEED_LOCK)   # two cold starts must not both create the schema
        for stmt in (HERE / "schema.postgres.sql").read_text(encoding="utf-8").split(";"):
            if stmt.strip() and not all(l.strip().startswith("--") or not l.strip() for l in stmt.splitlines()):
                conn.execute(stmt)
        conn.commit()
        return
    conn.executescript((HERE / "schema.sqlite.sql").read_text(encoding="utf-8"))
    # databases made before disposal existed: disposed passports keep their row, hash and chain position
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
    lock(conn, SEED_LOCK)   # a fresh Postgres seeds once, even when several instances start together
    if force:
        for t in ("records", "documents", "ai_events", "passports", "model_registry", "review_queue", "audit_log"):
            conn.execute(f"DELETE FROM {t}")
    elif is_seeded(conn):
        conn.commit()
        return {}

    counts: dict[str, int] = {}

    records = [SourceRecord(**r) for r in _load("records.json")]
    for r in records:
        r.hash = r.hash or sha256(r.content)
        upsert(conn, "records", "id", dict(id=r.id, status=r.status, authoritative=int(r.authoritative),
                                           created=r.created.isoformat(), payload=r.model_dump_json()))
    counts["records"] = len(records)

    docs = [Document(**d) for d in _load("documents.json")]
    for d in docs:
        upsert(conn, "documents", "id", dict(id=d.id, case_id=d.case_id, payload=d.model_dump_json()))
    counts["documents"] = len(docs)

    for m in _load("model_registry.json"):
        e = ModelRegistryEntry(**m)
        upsert(conn, "model_registry", "model_id", dict(
            model_id=e.model_id, provider=e.provider, status=e.status,
            effective_from=e.effective_from.isoformat() if e.effective_from else None, reason=e.reason, marked_by=e.marked_by))
    counts["model_registry"] = len(_load("model_registry.json"))

    # Past AI events and their passports. Seeded passports are pre-hashed in the file so the chain is stable;
    # passport.py appends to this chain at runtime.
    events = [AIEvent(**e) for e in _load("ai_events.json")]
    for e in events:
        upsert(conn, "ai_events", "id", dict(id=e.id, app_id=e.app_id, created=e.created.isoformat(),
                                             model_returned=e.model_returned, payload=e.model_dump_json()))
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
    upsert(conn, "passports", "record_id", dict(
        record_id=p.record.id, event_id=p.event_id, tier=p.business.tier, model_returned=p.agent.model_returned,
        created=p.record.created.isoformat(), hash=p.integrity.hash, prev_hash=p.integrity.prev_hash, seq=seq,
        payload=p.model_dump_json()))


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
