# Record Check — architecture and module contracts

Prototype for the RIMPA Global Hackathon 2026. Planning repo: `~/repos/rimpa-hackathon-2026`
(read `ideas/concept-records-gateway.md` and `ideas/scorecard.md` for the why).

**One sentence:** records management decides what to trust by evidence, not by whether AI touched it.

## The demo path (what must work)

1. A caseworker's AI-assisted *hardship assessment summary* (case 2026/0412) is submitted.
   - **Citations:** each reference is looked up (Crossref, then OpenAlex). One is fabricated → `not_found`.
   - **Evidence:** each sentence is traced to authoritative records → `supported / weak / unsupported / contradicted`.
     An AI sentence can be green; a human sentence can be red. That is the point.
2. The author fixes it, a reviewer signs off, and it is filed as **T2** with a **passport** (record package + hash chain).
3. "Six months later": the model is marked faulty → **Recall** lists 14 affected records, 3 of them T2, and queues them.

Everything must run **offline** from seed data and cached lookups. Live Crossref/OpenAlex and the LLM are
upgrades when the network and an API key are available, never requirements.

## Layout

```
recordcheck/            the engine (importable package, no UI code)
  models.py             pydantic models — THE contract between modules. Don't change shapes without updating this file.
  db.py                 connection (SQLite, or Postgres via DATABASE_URL), seed loader; schema.*.sql
  hashing.py            canonical JSON + sha256
  citations.py          reference extraction and lookup (Crossref, OpenAlex, fixture cache)
  evidence.py           claim splitting (LLM or seed), linking rules, weighing
  passport.py           tier rules, package builder, hash chain
  recall.py             model registry, recall by model, recall by source record
  sources.py            source health: ROT (redundant, obsolete, trivial) and drafts across the records
  disposal.py           retention periods, due list, approved destruction (content destroyed, hash stub kept)
  llm.py                Anthropic client wrapper; returns text + the model id the API actually returned
api/main.py             FastAPI wrapper over the engine (the "any system can plug in" story)
app/streamlit_app.py    the console the judges see
data/seed/              authoritative records, the draft, past passports, citation fixtures, tier rules
tests/                  pytest; every module has tests that run offline
```

## Module contracts

All functions take and return the pydantic models in `recordcheck/models.py`. `db.connect()` returns a
`sqlite3.Connection` with `row_factory = sqlite3.Row`; the DB file path comes from `RECORDCHECK_DB`
(default `data/recordcheck.sqlite`). With `DATABASE_URL` set it returns a `db.PgConn` instead: psycopg behind the
same `execute`/`commit`/`rollback` surface, rows read by name or position, `?` parameters, so engine SQL is
written once. Upserts go through `db.upsert` (ON CONFLICT, valid on both). Schema is plain SQL:
`schema.sqlite.sql`, `schema.postgres.sql` (same tables). `db.init(conn)` creates tables, `db.seed(conn)` loads
`data/seed/`; both take an advisory lock, so a fresh Postgres seeds itself once even with several instances.
`passport.build` takes `db.lock(conn, CHAIN_LOCK)` (Postgres `pg_advisory_xact_lock`, SQLite `BEGIN IMMEDIATE`)
from reading the chain head to the commit, and rolls back on refusal. On Postgres the policy is a row in `policy`,
not a file. Tests run on SQLite (conftest drops `DATABASE_URL`); `tests/test_postgres.py` opts in with
`RECORDCHECK_TEST_DATABASE_URL`.

### citations.py
```python
def extract_references(text: str) -> list[Citation]            # regex over a "References" block; [n] markers
def lookup(c: Citation, *, online: bool | None = None, conn=None) -> CitationResult   # conn: also read/write the citation_cache table
    # order: fixture cache (data/seed/citation_fixtures.json) → Crossref → OpenAlex.
    # online=None means "use RECORDCHECK_ONLINE env var, default false".
    # Legislation/cases (no journal, has "Act", "(Cth)", "v", "[yyyy]") → not_checked with a note.
    # Never raises on network failure: returns not_checked with the error in `note`.
def check_document(text: str, **kw) -> list[CitationResult]
```
Statuses: `found` (title similarity ≥ 0.85 and year within ±1), `mismatch` (title found, year/venue differ),
`not_found`, `not_checked`. A network error is `not_checked`, never `not_found`: a dropped connection must not read as "possibly fabricated". Record `source` as `fixture|crossref|openalex|none`. Never say true/false.

### evidence.py
```python
def split_claims(doc: Document, *, use_llm: bool | None = None) -> list[Claim]
    # If the seed document already carries claims (doc.claims), return them. Else, if use_llm and a key
    # exists, call llm.split_claims(); else fall back to sentence splitting. Author defaults to doc.default_author.
    # LLM output is kept only if every claim is verbatim in the body and every sentence contains a claim;
    # on any error or failed check, sentence splitting is used. The model cannot add or drop a claim.
def link_claim(claim: Claim, records: list[SourceRecord], case_id: str | None = None) -> list[ClaimLink]
    # Deterministic rules only. Match on: case_id in record.fields, keywords/numbers shared with record.content,
    # money amounts, date ranges. Return why each link matched in ClaimLink.note.
    # A record with a case_id links only to a document of that case; with no case on the document, only
    # shared records (no case_id) can link.
def weigh(claim: Claim, links: list[ClaimLink], records: dict[str, SourceRecord], citations: list[CitationResult] = ()) -> Verdict
    # supported: ≥1 link to a record that is authoritative AND status=current and no contradiction
    # weak: links only to superseded/non-authoritative records; or no links but a referenced citation was found/mismatch
  #       (an external source exists, but it is not an organisational record)
    # contradicted: a current authoritative record's fields disagree with a number/fact in the claim
    # unsupported: no links; or the claim rests on a citation whose status is not_found
def assess(doc: Document, conn, citations: list[CitationResult] = (), use_llm: bool | None = None, policy=None) -> Assessment
def reassess(assessment: Assessment, conn, citations=(), policy=None) -> Assessment
    # server side: keep the caller's claims, recompute every link and weight. ValueError if verdicts ≠ claims.
```
The LLM may only *split text into claims*. It never decides a weight.

### passport.py
```python
def load_tier_rules(path=...) -> TierRules                       # data/seed/tier_rules.json
def classify(event: AIEvent, rules: TierRules) -> Tier           # default tier of event.app_id, then escalations
def build(event: AIEvent, *, tier: Tier, assessment: Assessment | None, citations, review: Review | None, conn, rules: TierRules | None = None, record_id: str | None = None, document_type=None, gate=None, policy=None) -> Passport
    # Refuses (ValueError subclasses): TierBelowRules (tier lower than classify gives; raising is allowed),
    # SelfReview (reviewer is event.user), DuplicateRecord (record_id already in the chain), blank reviewer.
    # With a policy, runs gate.evaluate itself (document type, or with none the strictest default bar over what
    # was supplied) and raises GateBlocked(result) on blocked; the caller's `gate` is then ignored.
    # fills the six groups, computes hash over canonical JSON of everything except integrity.hash,
    # prev_hash = hash of the latest passport in the DB (chain). Persists to `passports` and `audit_log`.
def verify_chain(conn) -> ChainReport                            # recompute hashes, report first break if any;
    # a row marked disposed must match a disposal_register entry with the same retained hash
```
Tiers: `T0` transitory, `T1` retained output, `T2` decision-informing, `T3` agentic action.
Escalations (from tier_rules.json): `exported_to_document → ≥T1`, `decision_flag → ≥T2`, `tool_calls with side effects → T3`.

### recall.py
```python
def mark_model(conn, model_id: str, status: Literal["withdrawn","faulty"], effective_from: date, reason: str, by: str) -> None
def recall(conn, model_id: str) -> RecallResult               # T1–T3 passports whose agent.model_returned == model_id, tier desc, date desc
def queue_for_review(conn, record_ids: list[str], by: str, reason: str) -> int   # writes review_queue + audit_log, returns count
def mark_superseded(conn, record_id: str, superseded_by: str | None, reason: str, by: str) -> None
    # the source changed; it stops counting as evidence at once. KeyError unknown record; ValueError blank
    # name or a replacement that is not another existing record. Audited as record.marked_superseded.
def recall_by_record(conn, record_id: str) -> SourceRecallResult  # T1–T3 passports listing the record as a source
```

### sources.py
```python
def health(conn, policy: Policy | None = None) -> SourceHealthReport
    # per record: redundant (same content as another, ignoring case and spacing; the copy that counts as
    # evidence, then the earliest, is the original), obsolete (superseded or disposed), trivial (not
    # authoritative, or its system is not in the policy), draft. `eligible` = evidence.is_evidence.
```
Only `current` records from authoritative systems count as evidence (`evidence.is_evidence`). A weak verdict
names why each linked record does not count (`evidence.why_not_evidence`).

### disposal.py
```python
def due_for_disposal(conn, *, as_of: date | None = None, rules: TierRules | None = None) -> list[DisposalItem]
    # tiers with a fixed period in rules.retention_days (T0: 90 days); on_hold when the model is under recall
def approve_disposal(conn, record_ids, *, approved_by: str, reason: str, rules=None, as_of=None) -> list[DisposalEntry]
    # content destroyed: payload replaced by a stub, disposed_at set, disposal_register + audit_log written.
    # The passport row, seq, hash and prev_hash stay, so verify_chain still passes (disposed rows skip the recompute).
    # approved_by must name a person (ValueError if blank).
def register(conn) -> list[DisposalEntry]
```
Records must be disposable (why blockchain was parked) *and* the chain must stay verifiable. Both hold.

### llm.py
```python
MODEL = os.environ.get("RECORDCHECK_MODEL", "claude-opus-5-5")
def available() -> bool                                          # ANTHROPIC_API_KEY set
def complete(prompt: str, *, system: str = "") -> LLMResult      # text + model_returned (response.model) + usage
def split_claims(text: str) -> list[str]                         # structured output; returns sentences/claims verbatim
```
Use the official `anthropic` SDK (1.x). `client.messages.create(...)`. Always record `response.model` —
that is the "model returned" field the passport needs. Use `output_config` structured outputs for the split.

### api/main.py
`POST /check` (document → citations + assessment), `POST /passport` (event + review → passport),
`GET /passport/{record_id}`, `POST /recall` (model_id → RecallResult), `POST /recall/record` (record_id, optional
supersede mark → SourceRecallResult), `GET /sources/health` (SourceHealthReport under the saved policy), `GET /chain/verify`. Pydantic in, JSON out.
The API trusts no verdict or status from the caller: `/passport` looks every citation up again from its raw text
(`citations.recheck`), re-weighs the claims (`evidence.reassess`), and lets `passport.build` run the gate. 409 =
blocked (with reasons), 422 = refused (tier below the rules, self-review, inconsistent assessment, unknown type).
`/check` applies the saved policy, as the console does.

### app/streamlit_app.py
Tabs: **Check** (draft, citation list, highlighted sentences, click → trace panel), **Passport** (six groups, tier chip,
hash, "export JSON"), **Recall** (register, mark faulty, counts, queue), **Sources** (ROT health, mark a source superseded, recall by source record, queue), **Disposal** (due T0 entries, holds, approve destruction, register), **Register** (authoritative records, apps + default tiers).
Visual language: see `~/repos/rimpa-hackathon-2026` idea book — chips `supported/weak/unsupported/contradicted`,
tiers T0–T3, and the sentence highlights. Mark seeded data as "example data" in the UI.

## Conventions

- Python 3.12+, `uv run`, type hints, pydantic v2, `pytest` under `tests/` runs with no network and no API key.
- Never hardcode secrets. `ANTHROPIC_API_KEY`, `OPENALEX_API_KEY`, `RECORDCHECK_ONLINE`, `RECORDCHECK_DB` via env.
- Wording in UI and code: "supported by authoritative records", never "true". "not found", never "fake".
- All seed people, agencies, cases, records and references are invented. Keep it that way.
