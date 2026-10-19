# 01 · Build and enhancements

**Goal:** a demo that runs one path perfectly, offline-safe, by Monday 14:30, plus the few enhancements
that strengthen the pitch. Code lives in `prototype/record-check/`.

## State

**Done (17 Oct):** engine (citations, evidence, passport + hash chain, recall, disposal with recall hold,
policy studio + filing gate), Streamlit console with six tabs, FastAPI wrapper enforcing the gate,
seed data (2 cases, 4 documents, 40 passports, 4 sector presets), 62 offline tests. Haiku
(`claude-haiku-5-5`) for claim splitting and profile suggestions; live Crossref/OpenAlex with cache.

**Done (19 Oct, from session 1 feedback):** ROT in the engine. `draft` record status; weak verdicts say why
each source does not count (superseded by X / a draft / not from an authoritative system);
`sources.health()` labels redundant, obsolete, trivial and draft records (`GET /sources/health`);
recall by source record: `mark_superseded` + `recall_by_record` (`POST /recall/record`). Seed adds a draft
policy v5, a shared-drive copy of the delegation instrument, and a reissued debt notice (REC-2026/004912).
Demo: mark REC-2026/004790 superseded by REC-2026/004912 → 13 outputs (4 T2) relied on it; the agent note's
"$4,860" claim turns weak. Gap EC-SRC-10 recorded. Console: **Sources** tab (ROT tiles and flags, mark superseded, recall by record, queue T2); `web/` types updated by the web chat.

**Done (19 Oct, builder): Postgres port (V2.3).** `DATABASE_URL` set → Postgres (Neon), else SQLite (local, tests).
Self-seeding under an advisory lock; chain writes serialised with `pg_advisory_xact_lock`; policy stored in the DB;
reconnects after Neon drops an idle connection; standalone reads never left idle in transaction. Tested against a
real local Postgres (`tests/test_postgres.py`, 9 passed: concurrent writers keep one chain, write on one connection
read on another, lock released on refusal, API write then read). Normal suite `150 passed, 13 xfailed`, offline.
Also fixed a V0 console bug: **Issue passport** referenced an undefined `pol` and would have crashed. Next: S3, S1, S2.

**Specs ready to build (planner, 19 Oct 11:50; plan in `workstreams/README.md`). Builder: do these in order, then
hand to the deployer.**

**S1 · Intended use on records (plan A5).** Answers session 1's "is a document being used against its original
intent?" with a records control. No sentiment analysis, no LLM.
- `models.py` first: `SourceRecord.purpose: str = ""` (plain words, e.g. "Discussion paper for consultation; not
  policy, not for decisions about individuals") and `SourceRecord.not_for: list[str] = []` (policy document-type
  ids this record must not be relied on for, e.g. `["decision-letter"]`).
- `evidence.py`: `assess(..., document_type: str | None = None)` passes it to `weigh`. A linked record whose
  `not_for` holds the document type does not count as evidence for that document. `why_not_evidence` returns
  "its intended use excludes <type name>: <purpose>". With no document type, behaviour is unchanged.
- `reassess` and `api/main.py` (`/check` and `/passport`) pass `document_type` through, so the passport's gate
  sees the same verdicts as `/check`. Re-read `api/main.py` first: the web chat edits it.
- `sources.py`: no new ROT label. `SourceHealth` carries `purpose` and `not_for` so the Sources tab can show an
  "Intended use" column.
- Seed (invented): one current, authoritative Policy-library record, e.g. a hardship working-group discussion
  paper with a distinctive proposal, `not_for: ["decision-letter"]`. Words chosen so it links to no existing
  seed claim (check: run every seed document before and after, and the verdicts must be identical). Add one
  sentence somewhere the demo can show it (ad hoc body in Check is fine): weak under `decision-letter`,
  supported under `briefing`.
- Tests offline: both document types; no type = unchanged; API `/check` with a type; `/passport` agrees with
  `/check`. Add `EC-SRC-11`… rows to `EDGE_CASES.md` and fix its summary counts.
- Console: "Intended use" column in the Sources tab; the Check trace shows the reason with no extra work.
- Done when: `uv run pytest -q` green, the seed demo gates are unchanged (summary Blocked, eligibility note
  Ready), `ARCHITECTURE.md` contracts are updated, and this State section is updated.

**S2 · Stage database (plan A3), revised for the Postgres port (V2.3).** Goal, whatever `db.py` becomes: the stage
demo runs against its **own** database target with the new seed records, and one command resets only that
target; the DB other chats share is never reseeded. Policy lives wherever V2.3 puts it (in the DB), so the
reset covers it too. Locally on SQLite: `RECORDCHECK_DB=data/stage.sqlite` (git-ignored). On Neon: a separate
branch or database for the stage, never the shared one. Tests stay offline and keyless (CLAUDE.md rule 5).
Document it in `README.md` and `workstreams/05-demo-ops.md`. **Build after the Postgres port lands.**

**S3 · Console smoke test of the demo path.** The "Issue passport" button raised NameError (undefined `pol`)
and no test caught it. Add `tests/test_console.py` using `streamlit.testing.v1.AppTest` on a temp DB: load
every tab with no exception, then click through the stage path (Check the summary → eligibility note →
reviewer → Issue passport; Recall mark + queue; Sources mark superseded + queue; Disposal approve). Offline,
a few seconds. Then a UI break fails `pytest` instead of failing on stage.

**Next, in priority order:**
1. **Printed passport.** Export a one-page passport PDF (the six groups, tier, hash, policy version) so
   judges can hold a record of an AI-assisted decision. Button on the Passport tab. (reportlab or
   weasyprint; keep it dependency-light.)
2. ~~Recall honours "faulty from"~~ **Dropped 19 Oct (Hasim):** recall stays over-inclusive by design (EC-REC-05); the IM triages.
3. **Sidebar truth.** Show the real model id (`llm.MODEL`) and "cache + live" state in the sidebar.
4. **Policy guardrails.** Warn on bars looser than the preset; show the policy hash on the Register tab;
   write policy diffs (not just a summary) to the audit log.
5. **UI polish for the stage:** bigger type on the gate banner and the recall tiles; shorten metric
   labels that truncate ("Citations f…"); click a sentence to open its trace (currently a selectbox).
6. **Contradiction rules beyond household** (e.g. employment status from the file note), each as an
   explicit rule with a reason sentence.
7. Hosting: a named Cloudflare tunnel on a stable domain + QR code (see 05).

## Read first
`prototype/record-check/ARCHITECTURE.md` (contracts), `README.md` there, then the module you touch.
Concept and tiers: `ideas/concept-records-gateway.md`. Policy studio: `ideas/concept-policy-studio.md`.

## Rules that bite
- Change `models.py` first when a shape changes, then the module, then tests. Hashes use
  `exclude_none`, so adding optional fields is safe; renaming fields is not.
- Tests stay offline and keyless (`tests/conftest.py` strips the key). Anything touching the API or
  network is monkeypatched or `skipif`.
- No LLM decides a weight, tier, gate or record. It splits text and suggests profiles only.
- Wording rules in `CLAUDE.md` §7. No emoji in the UI.
- Subagents on Sonnet; review their diffs. Feature freeze Monday 14:30.

## Done when
The demo path (Setup → Check: Blocked → fix/eligibility note: Ready → Passport → Recall: 14/3 →
Disposal: holds) clicks through twice without error on the venue laptop, offline, and a backup video exists.
