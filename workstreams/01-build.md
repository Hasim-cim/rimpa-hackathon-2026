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

**Done (19 Oct, builder): S3 and S1.** S3: `tests/test_console.py` (AppTest, temp DB, offline) loads every tab
and clicks the stage path: summary Blocked, eligibility Ready, Issue passport (row written, chain ok), Recall mark
+ queue, Sources mark superseded + queue, Disposal approve. S1: `SourceRecord.purpose` / `not_for`; a record whose
intended use excludes the document type is not evidence for it (weak, with the purpose in the reason); `/check`,
`/passport`, the console Check tab and `reassess` pass the type; Sources tab has an **Intended use** table. Seed:
`POL-HARDSHIP-WG-2026` (invented discussion paper, `not_for: decision-letter`); every seed verdict and gate
unchanged (checked before and after). Demo sentence (ad hoc body in Check): "Repayment plans running longer than
five years attract an automatic partial waiver, capped at one third of the outstanding balance." → weak as a
decision letter, supported as a briefing. EC-SRC-11…15. Suite `160 passed, 13 xfailed`. 

**Done (19 Oct, builder): S2 stage database.** `db.reset(conn)` wipes every table (policy, disposal register and
review queue included) and reseeds. `scripts/stage.py reset` resets only `data/stage.sqlite` +
`data/stage-policy.json`, or with `--database-url … --yes` a Postgres stage branch; it never reads `DATABASE_URL`.
`tests/test_stage.py` (offline) and a Postgres reset test. Documented in 05 and the prototype README. Suite
`163 passed, 13 xfailed`.

**Done (19 Oct, builder): B3 printed passport.** `recordcheck/printout.py` (fpdf2): one A4 page with the six groups,
tier, gate at issue, model returned, policy version and hash, the passport hash and prev hash, and the chain checked
at print time; footer "Example data". Console: **Print passport (PDF)** on the Passport tab. API:
`GET /passport/{id}.pdf` (registered before the JSON route). Seed passports print "Evidence: no check recorded".
`tests/test_printout.py`: every seed passport is one page; long unicode text still one page; API PDF + JSON. Suite
`167 passed, 13 xfailed`.

**Done (19 Oct, builder): B2 reliability figure, with a changed definition.** No retained seed passport carries a
claim check (all 29 evidence summaries are empty), so "share whose evidence summary is all supported" would read
0 of 0 on stage. Headline instead: **retained AI outputs resting on current authoritative records** = outputs
whose source records all still count as evidence. Seed 29 of 29 (100%); after marking the debt notice
REC-2026/004790 superseded, 16 of 29 (55%), and "Sources pulling it down" lists the notice (superseded by
REC-2026/004912; relied on by 13 outputs). The claim-check share is shown alongside as "n of m fully supported"
("none yet" on the seed). `sources.reliability()`, a tile at the top of the Sources tab, `GET /sources/reliability`.
Wording: never "accurate". 3 tests. Suite `170 passed, 13 xfailed`. Next (after the 15:00 pitch): B4.

**Done (19 Oct, builder, Hasim's ask): S4 simple Policy studio + NAA test.** Setup is three questions and a save:
1 sector (radio + organisation; one button applies it), 2 document types (one **Strictness** choice per type:
Strict / Standard / Light, each equal to a Commonwealth preset bar; others show Custom and stay untouched; a tier;
a one-line plain summary of the bar; add a type by name), 3 systems that count as evidence. Exact thresholds,
apps and tiers, retention, guidance, the model's preset suggestion and reset sit under **Advanced**. Engine:
`policy.LEVELS`, `level_of`, `apply_level`, `new_type`, `describe`. Tests `tests/test_studio.py` click it.
**NAA finding 1 (fixed):** with live lookups on, a reference to NAA's own guidance page came back `not_found`
("possibly fabricated") and blocked filing; Crossref and OpenAlex do not index government pages. Now a non-DOI web
address or a government author → `not_checked`, "flagged for a person to confirm" (EC-CIT-18). Seed results unchanged.
**NAA finding 2 (open, needs Hasim):** claims about NAA rules read `unsupported` because no NAA guidance is held as an
authoritative record. Holding it as a Policy-library record makes them `supported` (tried in a scratch DB with the
verbatim quotes in `research/deep-research-2026-10-16.md`). There is no way to add a guidance record in the product yet.
**NAA finding 3 (open):** `not_for` names document-type ids, so a new strict type (e.g. "Agent action record") is not
covered by the discussion paper's `not_for: decision-letter`. Option: let `not_for` name a strictness level.
Suite `179 passed, 13 xfailed`.

**Done (19 Oct, builder): G3 review date.** `SourceRecord.review_due`. Past due (and current) → source health
`overdue` flag with "overdue for review since …" and an `overdue` count; it is deliberately **not** a ROT label and
still counts as evidence, so no verdict changes (the web Register page says ROT flags cannot support a claim, which
stays true). Reliability gains a separate `overdue` list (seed: file note REC-2026/004809, due 2026-09-30, relied
on by 10 outputs); the share does not move. Console: sixth tile "Overdue for review", a purple pill in Flagged
records, and the list under the reliability tile. Not built: "unless the policy says so" (a policy switch to
make overdue records weak). EC-SRC-16, 17. Next: G2, G1, G4 after 15:00.

**Done (19 Oct, builder): P1 + P2, passport-first.** P1: `passport.build` stores what was checked at issue
(`passport_checks`: citation results, per-claim verdicts, gate result, a snapshot of each source's state) and hashes it
into new passports (`process.checks_hash`; optional, so seed hashes and the chain are unchanged). `passport.view()` /
`view.py` gives 8 checks: Citations, Evidence, Sources, Filing gate, Review, Integrity, Retention, Since filing (the one
live check: a source superseded, the model marked faulty/withdrawn, or queued for re-review). Tampering with stored
checks shows as an Integrity problem; disposal deletes them. `GET /passport/{id}/view`. EC-PAS-13…17, `test_view.py`.
P2: console tabs are now **Records · Check a document · Information manager** (Setup, Sources, Recall, Disposal,
Register, Passport detail). Records opens one passport (header, Print PDF, the 8 checks as expanders with a status
word and one-line summary; problems open by default) with "All records" in a collapsed list ("Changed since filing"
pill). Issuing a passport in Check lands on it in Records. Seed passports say "summary counts only". Console smoke
test covers it. Suite `189 passed, 13 xfailed`.

**Done (19 Oct 12:58, builder): P4 readable console + passport card.** Two places in the sidebar: **Records**
(default) and **Information manager** (Setup, Sources, Recall, Disposal, Register; old Passport detail removed).
Records: a narrow clickable list on the left ("what, date" + status); on the right one plain headline (e.g. "Ready to
file: every statement is supported by authoritative records"; "Changed since filing: …"; "Older record: summary
only"), a who/when line, the **passport card** (six groups in plain words, fingerprints shortened in monospace),
then "Checks done on this record": status shown once, only checks that ran, unrecorded ones folded into one line,
details as sentences and small tables, hashes behind a "Technical details" toggle; PDF as a small secondary button.
"Check a document" opens the check flow and returns to the new passport. Opens the newest passport with stored
checks. Also: Retention summary gives tier words; filed times shown in local time. Stage path v2 test updated (and a
first-screen test). Screenshots: `docs/demo/records.png`, `docs/demo/im-sources.png`. Suite `191 passed, 13 xfailed`.

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

**Order after S1–S3 (planner, 12:00):** B3 then B2 before the 14:30 freeze (both additive; they change no
verdict); B4 after the 15:00 mentor pitch, because it changes verdicts and must be re-checked against the demo.
- **B3 · Printed passport:** one-page PDF of a passport (six groups, tier, gate result, model returned, policy
  version and hash, chain hash), a button on the Passport tab and `GET /passport/{id}.pdf`. Light dependency
  (reportlab or fpdf2). Says "example data". Test: the PDF builds for a seed passport, offline.
- **B2 · AI search reliability figure:** `sources.reliability(conn)` over retained (T1–T3, not disposed)
  passports: the share whose evidence summary is all `supported`, plus the five source records most often
  listed by passports that weren't, each with its source-health labels. Tile on the Sources tab and
  `GET /sources/reliability`. Wording: "supported by authoritative records", never "accurate" or "true".
- **B4 · Numbers in sentences linked by wording (EC-EVI-14, EC-SRC-10):** tonight. Re-run the seed gates after.

**Done (19 Oct, from `research/deep-research-im-tools-2026-10-19.md`): matching steps shown.** Presentation
only, no change to models, API or verdicts. `citations.match_stage(r)` and `evidence.claim_stage(v)` return
(step, strength) labels. Check tab: a steps legend ("your records, offline cache, Crossref/OpenAlex fuzzy match. No AI
judge decides a weight"), a Step · Strength line per citation, and a "Matched by" line per claim in Trace. Disposal tab
caption: "nothing is destroyed until a named person approves it" (an approval, not a content review). Demo values
on DOC-2026/0412-summary: c1 supported by exact field match (REC-2026/004811); citation [4] offline cache,
similarity 0.31, "not found; possibly fabricated". No LLM stage in matching; say so if asked. Suite `174 passed,
11 skipped, 13 xfailed`.

**Passport-first UI (Hasim, 19 Oct 12:50). Ahead of G1–G4.** What the engine has and what the UI shows are
different things. People see **the record passport and the checks done on it**; each check opens to its detail.
Everything else (Setup, Sources, Recall, Disposal, Register) moves out of the main view into an
"Information manager" area.
- **P1 · Engine: one view, both UIs.** `passport.view(conn, record_id) -> PassportView` (models first):
  header (title, tier, gate status, filed date, model returned, reviewer, document type) and
  `checks: list[CheckSummary]`, each `{id, name, status: ok|attention|problem|not_run, summary (one line),
  details}`. Checks, in order: **Citations** (n found / not found / to confirm) · **Evidence** (supported, weak,
  unsupported, contradicted, with each sentence and its records) · **Sources** (all current authoritative, or
  which are superseded, draft, outside their intended use) · **Filing gate** (result against the document
  type's bar; policy version and hash) · **Review** (named reviewer, not the author) · **Integrity** (hash and
  chain verified) · **Retention** (tier, retention, disposal authority) · **Since filing** (live: a source
  superseded or a model under recall since issue, with the recall link). `GET /passport/{id}/view`.
  The details must be what was checked **at issue**, not a re-run: today the passport stores only summary counts,
  so store the per-claim verdicts and citation results with it (e.g. a `passport_checks` table holding the
  payload and its hash, the hash referenced from new passports). **Seed passports' hashes and the chain must
  still verify**: seed passports show summary-only details and say so. "Since filing" is the only live check.
- **P2 · Streamlit:** the first tab is **Records**: a list of passports (newest first, gate and tier pills,
  "since filing" alert icon), then one passport opened with the checks as collapsed expanders, each with a
  status pill and its one-line summary. Check a document → file → you land on its passport. The other tabs sit
  under an "Information manager" section. Reuse the existing renderers inside the expanders.
- **P3 · Web (deployer/web chat):** the same view from `/passport/{id}/view`, once P1 is deployed.
Done when: the suite is green (with P1 tests: the view for a new passport matches /check at issue; seed
passports still verify; "Since filing" flips when 004790 is superseded), the console smoke test covers the
Records tab, and the demo path starts and ends on a passport.

**P4 · Make the console readable (Hasim: "the view is becoming extremely confusing", 12:50). Ahead of G-items;
console only, no engine change.** What the planner found on a fresh stage DB:
nine top-level tabs (Records, Check a document, an "Information manager" label tab, Setup, Sources, Recall,
Disposal, Register, and the old Passport detail duplicating Records); the record opened by default is a seed
passport, so the first screen is four grey "Not run" checks; each check repeats its status inside; raw fields
("Live: True", "Queued: False", prev hash) and codes (T1) without words.
1. **Two places, not nine tabs.** Sidebar choice: **Records** (default) and **Information manager**. Records holds
   the passport view, with a "Check a document" button that opens the check flow and returns to the new passport.
   Information manager holds Setup, Sources, Recall, Disposal, Register as its own tabs. Remove the old Passport
   detail tab (the Records view replaces it).
2. **Open a full passport by default:** the newest passport with stored checks; if none, the list with a prompt
   "File a document to see its passport". Seed passports are labelled "Older record: summary only", and checks
   that were not recorded are collapsed into one line, not four grey rows.
3. **One headline per passport** in plain words, e.g. "Ready to file: every statement is supported by
   authoritative records", then one line: who filed it, when, which AI model, reviewed by whom.
4. **Checks as one tidy list:** icon + name + one-line result; status shown once (in the row), not again inside.
   Only checks that ran. Details in sentences ("Not queued for review"), never booleans. Hashes go under
   "Technical details" inside Integrity. Tier codes always with words ("T1: kept with the business record").
5. **Records list:** a compact table to pick from (title, date, status pill, alert icon), not a selectbox plus a
   separate expander table.
Done when: the stage-path test passes with the new layout, the first screen after filing the eligibility note
shows one headline and the check list with no "Not run" rows, and a screenshot of Records and of Information
manager → Sources is saved to `docs/demo/`.

**Live data and NAA metadata (planner, 19 Oct 13:40; research in `research/live-data-and-metadata-2026-10-19.md`).**
Order: **now (before the 14:30 freeze): fix the hard-coded function and case on Issue passport** (-46's bug: every
document is filed as "Debt waiver assessment", case 2026/0412; take them from the document and the event). Then
after the 15:00 mentor pitch, in this order: **L1 → G1 → M1 → G2 → G4** (L1 moved up 13:55: Hasim wants live, accurate data; 14:00 Hasim: start L1 now, isolated from the demo tree, merged after the 15:00 pitch. Uncommitted work means a worktree from HEAD lacks today's changes: either commit the green tree first, or build L1 in the main tree behind a switch that is off by default).
- **M1 · NAA Minimum Metadata Set on the passport.** `models.py` first: add Protective Marking (default
  "OFFICIAL"), Format (e.g. "text/plain"), Rights (default "none recorded"), Disposal Class as a structured field
  (authority, class, action), and Identifier Scheme. A "Metadata (NAA Minimum Metadata Set)" group on the passport
  card, labelled with NAA's property names. New passports only; the seed chain must still verify (older passports
  show "not recorded"). AGRkMS marks Rights, Format and Integrity Check as conditional: don't label them mandatory.
  Levels confirmed on the live NAA page in a browser, 19 Oct (-46). The pitch line is cleared once M1 lands.
- **L1 · Live legislation check (Federal Register of Legislation).** `citations.py`: a reference of kind
  `legislation` is looked up at `https://api.prod.legislation.gov.au/v1/` (no key; 1–4 s): name normalised (strip
  "(Cth)" and section numbers), current version via `isCurrent eq true`, never filter on status. Results:
  in force → `found` with the note "Act found in force on the Federal Register of Legislation; the section is for
  a person to confirm"; repealed → `mismatch` with "repealed on <date>" (say "repealed"; say "replaced by" only if
  the register's record states it); not found → `not_checked`, never "possibly fabricated" (EC-CIT-18 holds).
  Offline fixtures from `research/live-api-evidence/frl/`, live behind the same switch as Crossref. Re-run the seed
  demo gates: citation [1] in the summary changes from not_checked to found, so update the script's numbers.
  Optional, only if time remains: a demo document citing the 1922 Act.
  **Pre-plan test results (-46, 13:50; `research/live-data-and-metadata-2026-10-19.md` addendum, `probe.py`):**
  normalise by stripping "(Cth)" and everything from "s/sch/pt <n>", then exact `name eq` (7 of 7 real Acts resolved).
  `name eq` also hits `nameHistory`: show both names ("cited as Social Security Act 1947; the register lists it as
  Social Services Consolidation Act 1947, repealed"). Wrong year: `contains` on the stem, keep collection == Act
  client-side, compare years → `mismatch` ("the register has Privacy Act 1988"). **The API rate-limits** (calls went
  from 1.4 s to 7–12 s, then timeouts after ~25 calls), so: a per-title cache in `citation_cache`, an 8 s timeout
  that falls back to `not_checked` ("The register did not respond"), fixtures prefetched for every demo citation, and
  no cold live call on stage. Generate fixtures slowly, after the API has rested.
  **Test pass (-46, 14:10):** green; live spot checks agree. The wrong-year case does **not** work live (`contains`
  with `$top=10` misses the 1988 Act), so its fixture is dropped and we don't claim wrong-year detection on stage.
  **Merge sequence after the 15:00 pitch (planner, 14:15):** (1) Hasim says go and the main tree is committed
  (suite green first); (2) the builder merges `l1-legislation` (ba28055), adds the EDGE_CASES rows and the
  ARCHITECTURE contract, re-runs the suite and the stage-path test; (3) the builder hands to the deployer, who
  deploys preview → promote; (4) reset the stage branch and rehearse step 2 with the new [1] line.
  **No match is never "possibly fabricated" (planner, overrides the test note):** it could be state legislation, a
  regulation or a misnaming. It reads `not_checked` with "No Commonwealth Act of this name on the Federal Register
  of Legislation; a person should confirm (it may be state legislation or misnamed)". "Possibly fabricated" stays
  for scholarly references not found in Crossref or OpenAlex.
- Not building: data.gov.au (dataset metadata, not records), NAA RecordSearch (no API), Trove (key takes a week).

**Garbage-in specs (planner, 19 Oct 12:40; the frame is in `research/session-1-outcomes-2026-10-19.md`).
After B4. In this order:**
- **G1 · Facts must match, not just words** (folds in B4): when a claim links to a record by wording, compare
  the numbers and dates in the sentence with that record's fields. A mismatch can't be `supported` by that
  record; a clear field clash is `contradicted` with a reason naming the field. Closes EC-EVI-14, -16, -18 and
  EC-SRC-10 if it can be done cleanly. Re-check the seed demo gates after.
- **G2 · Records that disagree** (EC-EVI-12): two current authoritative records give different values for the
  field a claim relies on → the claim reads `weak` ("REC-A says 380, REC-B says 420; the source needs fixing"), and
  source health gets a `conflicting` flag listing both records. Fix the source, not the prompt.
- **G3 · Review date:** `SourceRecord.review_due: date | None`. Past due → source health flag "overdue for review"
  and a line in the reliability drag list. It does not change verdicts (the IM decides), unless the policy says so.
  Invented seed: one record overdue.
- **G4 · Dropped qualifiers** (only if G1–G3 are green): the linked source sentence has "not", "except", "only"
  or "draft" and the claim drops it → `weak` with the source sentence quoted. Deterministic rules; no LLM, no
  sentiment.
Same rules as before: `models.py` first, seed invented, tests offline, EDGE_CASES rows and counts, hand to the
deployer when green. Wording: "supported by authoritative records", never "true" or "accurate".

**Done (19 Oct): minimal layout and dashboard engine.**
- **Console trimmed** to the Records page (headline, four check lines from `view.four_checks()`, collapsed
  passport) and an Information manager side (Recall with mark-superseded folded in, and Setup with its three
  questions). `RECORDCHECK_SHOW_ALL=1` brings back Sources, Disposal and Register. Status colours are blue,
  orange and grey only.
- **Dashboard engine:** `recordcheck/dashboard.py` `report()`, served by `GET /dashboard`. The four KPIs are
  approved; needs a person; bias risk signals (fixed rules: one source or one system, a weak, draft or
  superseded record, or a not_for match); and recall suggested.
- **Recall threshold:** policy `recall_signal_threshold` 0.30, with `recall_signal_min_refs` 10. These are
  excluded from `policy_hash`.
- **Seed:** 9 passports gained citation counts through `scripts/seed_citation_counts.py`, which also re-hashes
  the chain. northstar-7 now shows 5 of 15 references not found (33%), so recall is suggested. Passports filed
  before the gate existed count as approved when a named reviewer approved them.
- **Shared DBs:** the local DB and Neon still hold the old seed. Reset the stage DB to see the flag.
- **Dashboard screen:** first Information manager tab (Dashboard, Recall, Setup), reading only `dashboard.report()`. Suite `204 passed`.
- Suite: `203 passed, 11 skipped, 13 xfailed`.

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

**Done (19 Oct 13:37, builder): Streamlit rebuilt to Hasim's mockup** (claude.ai design canvas "Record Check: records").
Header: logo, "Record Check", "Example data" pill, Records | Information manager switch (top, not the sidebar).
Records: left card (Records, blue "Check a document", rows with title, status pill, date, how long it is kept,
"(changed)" marker); right article: RECORD PASSPORT + id, title, coloured headline box ("Ready to file: …"), who line,
the passport card (six groups as in the mockup), the older-record note, then "Checks done on this record": one row
per check with a ✓ ! ✕ – mark, name and summary; opened rows show key-value lines and, for Evidence, sentence cards.
Full records list the eight engine checks; older records fold into At filing, Integrity, Retention, Since filing.
Information manager: reliability card ("29 of 29", pulling it down), then the tabs with the mockup's one-line
descriptions. Colours follow the team rule (blue/orange/grey, no red or green), not the mockup's green/red.
`.streamlit/config.toml` sets primary blue. Fixed with it: Issue passport took function "Debt waiver assessment" and
case 2026/0412 for every document; now from the document (-46 finding 1). Double full stop in the four-check
evidence line (finding 4). Note: the console no longer uses `view.four_checks`; `/summary` (web) still does.
Screenshots: `docs/demo/records.png`, `docs/demo/im-dashboard.png`. Suite `207 passed, 13 xfailed`.

**Built on branch `l1-legislation` (worktree `../rimpa-l1`, 19 Oct 14:20–14:40, builder), waiting for the merge after
the pitch.** Worktree suite `225 passed, 11 xfailed`. Commits:
- `4eb7f9a`, `ba28055` **L1** live legislation check (Federal Register of Legislation); tested by -46, offline + 3 live.
- `09230ae` **D1** retractions: Crossref `updated-by`, else `filter=updates:<DOI>`; closes EC-CIT-14.
- `216e27c` **D2** authors vs the index's surnames → mismatch naming both; closes EC-CIT-15.
- `7fd448e` **W3** `CitationResult.checked_at` + `citations.provenance()` ("Crossref, live, 19 Oct 14:20" / "offline copy").
- `f0dc7cf` **I1** `recordcheck/connectors.py`: `RecordSource`, `PassportSink`, seed-database adapters.
At the merge: add the L1, W3 and I1 rows to EDGE_CASES and ARCHITECTURE; move `FiledReceipt` into `models.py`; wire
`evidence.assess` through `RecordSource`; re-run the stage-path test. No seed demo result changes except L1's [1] → found.
Still main-tree: G1 (first after the merge), W2 `GET /policy/levels`, D3 (check `collection` live first), I2.
