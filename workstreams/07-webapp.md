# 07 · Production web app (Vercel), V1 → V4

**Goal:** turn Record Check into a web app that can go to production on Vercel, without ever losing a
working demo. Built in versions; each one is logged in [`docs/versions.md`](../docs/versions.md) and
tagged in git. The webapp comes first; the IM rules framework (V3) gets room in the design from day one.

**Owner:** Hasim (dev and prod for the team). **Stack (decided 19 Oct):** Next.js (TypeScript) on Vercel
→ the existing Python engine behind FastAPI, deployed as Vercel Python functions → Postgres (Neon via the
Vercel marketplace). Streamlit stays as the stage demo until V2 reaches parity.

## How every version is built

1. Read `prototype/record-check/ARCHITECTURE.md` and the module you touch. Shapes change in `models.py` first.
2. `uv run pytest -q` stays green and offline. The edge-case register (`EDGE_CASES.md`) is the coverage
   map: fixing a ❌ flips its strict xfail, so move the row to ✅ in the same change.
3. **Ponytail check** (`~/ponytail`, rules in its `AGENTS.md`): before building, climb the ladder (need it?
   exists already? stdlib? platform? installed dep?). After building, run a ponytail-review pass on the
   diff and act on it. Deliberate shortcuts carry a `ponytail:` comment naming the ceiling.
4. Log the version in `docs/versions.md`, tag it (`v1`, `v2`, …), update this brief's State.

## Versions

### V0 · Pre-event prototype (frozen)
Streamlit console + FastAPI + SQLite, written 17–18 Oct before the event. Tag it as it stands so the
pre-built-code question can be answered either way: "V0 was the rehearsal, V1+ was built on the day."

### V1 · Demo-safe hardening + API on Vercel (Mon 19 Oct, by the 14:30 freeze)
1. **Fix the five demo gaps** from `EDGE_CASES.md`: negation (EC-EVI-09); empty or unassessed document
   gates ready (EC-GAT-01/02); API skips the gate without `document_type` and accepts a lower tier
   (EC-API-06/08, EC-PAS-09); `not_checked` citations ignored by the gate (EC-GAT-14); self-review (EC-GAT-10).
2. **Link Vercel** (Hasim): `npm i -g vercel`, then `! vercel login`, then `vercel link` at the repo root.
3. **Deploy the API** to Vercel as a Python function. Data: seed SQLite into `/tmp` on cold start.
   `ponytail:` resets per instance; fine for a read-mostly demo, Postgres in V2 removes the ceiling.
   Verify against Vercel's current Python/FastAPI docs before relying on any config detail.
4. Streamlit demo unchanged; the click-through from `01-build.md` still passes twice.

### V2 · Next.js console at demo parity (start Mon in parallel; switch only at parity)
1. `web/` Next.js App Router app. One page per current tab: Setup, Check, Passport, Recall, Disposal,
   Register. Same wording rules (CLAUDE.md §7), no emoji.
2. **One contract, not two:** generate TypeScript types from FastAPI's OpenAPI schema (`models.py` →
   OpenAPI → TS). No hand-written duplicate types.
3. **Postgres** replaces SQLite behind `db.py`. Passport chain writes run in one transaction with an
   advisory lock (the chain needs serial writes; SQLite hid this). Schema as a plain SQL file.
4. **Server-side assessment:** `/passport` recomputes the assessment instead of trusting the client's
   (EC-API-07). Policy applied on `/check` too (EC-API-10).
5. Smoke test the demo path end to end in a browser (one Playwright script). Preview deploy per branch,
   `main` = production.
6. **Parity gate:** the full demo path clicks through on the Vercel URL twice. Only then does the stage
   demo switch from Streamlit.

### V2.x · Minimal layout and dashboard (decided 19 Oct; Streamlit has it first)
Hasim's call: Streamlit is the stage UI today, and the web app follows the same layout so there's one design.
The trimmed Streamlit console is the reference, and `recordcheck/view.py` holds the shared wording.
1. **Records:** one page with a left rail of records and the selected record on the right. The headline status
   (Ready / Blocked / Needs review and why) comes first, then **four check lines** from `view.four_checks()`:
   Evidence, References, Filing, Since filing. **Then the passport shown as a visible document card** (six groups, plain labels;
   Hasim, 19 Oct: "you need to see the passport"), with Download PDF as a small button. No metric row.
2. **Information manager:** three tabs, **Dashboard, Recall, Setup**. Recall includes "mark source superseded".
   Setup has only its three questions plus Save. Sources, Disposal and Register stay in the API and are hidden
   from the nav. Bring them back behind a flag for Q&A, as `RECORDCHECK_SHOW_ALL` does in Streamlit.
3. **Dashboard** from `GET /dashboard` (types already regenerated):
   - a row of four KPI cards with a plain-words line under each number
   - a recall banner when a model is suggested
   - last 10 filed, and risk by business function
   - small panels for supported statements, AI vs human statements, and sources/disposal
   No KPI maths in the client.
4. **Colours:** blue = in order, orange = needs a person, solid orange = blocked or changed, grey = not run.
   No red, green or emoji.
5. **Production data:** the Neon DB still holds the old seed. The dashboard's model recall flag needs the new
   citation counts in `data/seed/passports.json`. Reset the stage branch on purpose (`scripts/stage.py reset
   --database-url … --yes`), never as a side effect.

**Planner review, 19 Oct (Hasim's answers):** (1) the passport is a **visible card** in both UIs, not collapsed;
(2) the dashboard tile "Bias risk signals" is renamed **"Narrow-evidence signals"** (rests on one source, or on weak,
draft or superseded records). In the pitch: narrow evidence is one way bias gets in; never call it a bias detector.
Chunk A also restores the visible passport card in Streamlit and renames the tile (key, label, API field).
Dispatch: A → builder (-88); B, C and deploy → deployer (-ed). Production reset: the deployer confirms with Hasim
in its own chat right before resetting Neon `main`.

**Planner update, 19 Oct 13:45:** Hasim had Streamlit rebuilt to his design canvas
(https://claude.ai/artifact/Ub6wrz62KzniTx24bKxWDs). The Records page lists the **individual checks** (Citations,
Evidence, Sources, Filing gate, Review, Integrity, Retention, Since filing; older records: At filing, Integrity,
Retention, Since filing), each opening to its detail, **not** the four grouped lines. Web chunk B follows: the
headline from `/summary`, the check list and the details from `/view` (`checks`), then the visible passport card.
`four_checks` stays in the API for the dashboard and older callers. Colours stay the team rule (blue / orange /
solid orange / grey; no red or green); the canvas has been recoloured to match.

**V2.x build plan (planning pass, 19 Oct; the web chat builds and deploys):**
- **A · API:**
  - Add a `RecordSummary` model.
  - Add `view.headline()` (moved from Streamlit's `_headline`) and `view.summary()`.
  - Add `GET /passport/{id}/summary`, declared *before* the greedy `/passport/{id:path}` catch-all. It returns the headline, its status, the four checks and the policy line.
  - Gate: `uv run pytest -q`, then `npm run types`.
  - **Remove the TypeScript `headline()` and `HEAD_COLOURS` from `web/app/page.tsx`.** Check wording comes only from Python.
- **B · Shell, colours, Records:**
  - `lib/ui.tsx` gets the Streamlit colour pairs: blue `#d6e6fb/#1e3a8a`, orange `#fde8b8/#7a4a00`, solid orange `#c2410c/#fff`, grey `#e5e7eb/#374151`. Remap every red or green map. To find them, grep `#15803d|#b91c1c|#14532d|#7f1d1d|#d1f0dc|#f8d0d0`.
  - Nav: Records / Check a document / Information manager (Dashboard, Recall, Setup). Disposal, Register and Passport detail appear only with `NEXT_PUBLIC_SHOW_ALL=1` (set at build time).
  - Records page: the headline and four collapsed check lines come from `/summary`, the detail from `/view` (`details.parts`). The passport is a **visible card**, not collapsed; the PDF is a small button. An unknown `?id=` shows "not found".
  - Gate: `npm run build`.
- **C · Dashboard, Recall, Setup:**
  - `app/dashboard/page.tsx` from `GET /dashboard`, with no client maths.
  - Recall keeps "mark source superseded" visible and collapses the registry and audit.
  - Setup shows only the three questions behind the flag; the PUT body stays the full policy.
- **Deploy:**
  1. Preview: seed the Neon `preview` branch with `scripts/stage.py reset`, then `vercel deploy --scope the-record-breakers`, then `vercel curl` on `/api/dashboard`, `/api/passport/REC-2026/002444/summary` and the pages.
  2. Promote, then **reset production (Neon `main`) with `scripts/stage.py reset --database-url <main pooled URL> --yes`. Hasim approved this on 19 Oct.** Pull the URL with `vercel env pull` into a temp file, never print it, and delete it after.
- **Risks:**
  - The CLI deploy uploads the working tree, including other chats' work in progress. Run `git status` and the tests right before deploying.
  - `NEXT_PUBLIC_SHOW_ALL` must be unset in production.
- **Cut if short on time:** the Streamlit `_headline` swap (keep a `ponytail:` duplicate), the extra Setup trim, the Recall collapse.

### V3a · Web app as the main product, plus integrations (planner, 19 Oct 14:30; Hasim: "improvements on the main one and API integration")
Hasim's answers: the main one is the **web app**; integration means **a records-system connector** and **more live data
sources**. Order below. Each item: engine to the builder (-88), web and deploy to the deployer (-ed), planner reviews.

**Web app (the main one)**
- **W1 · Web becomes the stage UI.** Parity check against the Streamlit stage path v2 (steps 1–7 in 05): every step
  clickable on the web, including source health and the reliability figure. Then a Vercel "stage" environment on the Neon
  `stage` branch with its own stable URL (the deployer offered this). Update 05 to present from the web.
- **W2 · Setup strictness picker** (known gap: LEVELS not in the API). Expose the levels via `GET /policy/levels`, then add
  the picker on the web.
- **W3 · Show where each check came from.** Every citation row says its source and when it was checked: "Crossref, live,
  19 Oct 14:20", "Federal Register of Legislation, offline copy of 19 Oct", "not checked: register did not respond". This
  makes live data visible and honest. Engine: `CitationResult.checked_at` plus the existing `source`.
- **W5 · One top menu (Hasim, 14:40).** Replace the two tabs plus sub-tabs with one top bar that reaches every
  important page in one click: **Records · Check a document · Dashboard · Recall · Setup**, with a small divider
  before the information-manager items (Dashboard, Recall, Setup). A **More** menu on the right holds Disposal and
  Register, reachable but out of the way (drop the `NEXT_PUBLIC_SHOW_ALL` gate for these two). The current page is
  marked (`aria-current`). At phone width the bar wraps or becomes a menu button. "Check a document" stays a button on
  Records too.
- **W4 · Judges' phones:** the stage URL works at phone width, with a QR code on the last slide.

**More live data sources** (engine; all offline by default, live behind `RECORDCHECK_ONLINE`, cached, with a timeout → `not_checked`)
- **D1 · Retractions (Crossref, verified 14:30).** For a `found` reference with a DOI, query
  `/works?filter=updates:<DOI>`. Any notice of type `retraction` → `mismatch` with "Retracted on <date> (notice <DOI>)";
  `expression_of_concern` → `mismatch` with "Expression of concern". Closes EC-CIT-14. One extra call per DOI, cached.
- **D2 · Authors (no new API).** Compare cited authors with Crossref's authors (surnames) → `mismatch` "cited as X; the
  record lists Y". Closes EC-CIT-15.
- **D3 · Regulations and instruments (FRL, same API as L1).** ⚠️ Check that `collection` holds legislative instruments
  before building; then extend L1's lookup to instruments named in references.
- **Merge L1 first** (sequence in 01-build). D1–D3 build on it.
- **Engine order (Hasim, 14:35):** L1 merge → **G1** → D1 → W2 levels → W3 checked_at → D2 → I1 → I2 → D3, then M1, G2, G4.

**Records-system connector** (engine; waits for the connector research in progress)
- **I1 · Connector contract:** `RecordSource` (list and get authoritative records, with status, superseded-by, purpose,
  review date) and `PassportSink` (write a filed passport back as a record or metadata). The seed DB is the first adapter.
  The engine never calls a vendor API directly.
- **I2 · One real adapter**, chosen from the research. Demo it against a real or locally run server if one exists for
  free; otherwise against recorded responses, and say so on stage.
- **I2 decision (planner, 14:45; research in `research/records-connectors-2026-10-19.md`): a Content Manager adapter
  on recorded fixtures.** Content Manager is what the judges and the OpenText venue know, and it is the only option
  with no outside dependency in ~3 hours (Graph needs a tenant; Alfresco and RecordPoint access are unverified).
  Field and operation names come from Kapish's "Content Manager Power Connect" connector on Microsoft Learn (publisher
  Kapish Services Pty Ltd; the planner re-checked Find Records, Create Record, Attach Electronic File, Finalise,
  RecordNumber, RecordTitle, RecordDateRegistered, RecordRecordType, RecordOwnerLocation, RecordRetentionSchedule),
  **not** the official ServiceAPI schema. Build:
  1. **Read mapper** (RecordSource): fixture search results → `SourceRecord` (RecordNumber → id, RecordTitle → title,
     RecordRecordType → record type, RecordDateRegistered → created, RecordOwnerLocation → owner,
     RecordRetentionSchedule → disposal). Content Manager has no standard current/superseded field: make it a
     **declared mapping rule** in the adapter config (e.g. a named field or a "superseded by" relationship), not a guess.
     Fixtures include a superseded policy and a record with a retention schedule.
  2. **Write mapper** (PassportSink): a filed passport → a "Create Record" request plus the passport JSON as an
     attached electronic file, written to a local outbox and request log. No network.
  3. Tests offline; one row each in EDGE_CASES. Mark the fixtures `"shape": "assumed"` unless the team gets a real
     ServiceAPI Record response from the OpenText mentors (ask today; it would replace the assumed shape).
  Fallback only after a 15-minute smoke test: Alfresco Community in Docker over the CMIS browser binding.
- **I3 · Wording:** "Record Check reads your authoritative records where they already live and files the passport back
  there." On stage: "a contract test against Content Manager-shaped records". **Never** "integrated with" or "connected
  to OpenText Content Manager", "one CMIS adapter reads every system", "Content Manager has a public sandbox", "the
  official ServiceAPI schema", "Purview has an isRecord flag", or "Objective has an open API".

### V3b · Demo-ready UI: Record Passport (Hasim, 19 Oct 15:00; plan by the deployer, for the planner to review)
Hasim's list: a main landing page, an easy-to-follow directory, a logo, a colour scheme (green for acceptance), the
name **Record Passport**, trial documents only for the presentation plus another mode (**separate URLs**), a visible
**bias check**, more on the dashboard, and fewer steps. Decisions he made today: green / amber / red / grey (each with
an icon, so it never relies on colour alone), the row is called "Bias check", and the modes live on separate URLs.

**Two URLs, one codebase** (a build-time `NEXT_PUBLIC_MODE`; no new project code paths beyond what's listed)
- **Presentation:** `record-check-stage.vercel.app` (project `record-check-stage`, Neon `stage`). `MODE=demo`:
  the document picker shows only the trial documents; a persistent "Demo: invented data" banner; a presenter-only
  **Reset demo** action (calls a new guarded `POST /stage/reset`, or the deployer runs `stage.py`, see U8); no Disposal
  or Register in More.
- **Working app:** `record-check.vercel.app` (Neon `main`). Full menus, plus **Try your own document**: paste a title,
  text and references and run the same checks (`/check` already takes `title`/`body`/`references`). The QR code on the
  last slide points here.

**Web (deployer), in order**
- **U1 · Name and logo.** "Record Passport" everywhere: tab title, header, PDF heading (engine), slides. Logo: an inline
  SVG mark (a passport booklet with a check), in one colour so it prints; favicon from the same mark (fixes the 404).
- **U2 · Colour scheme.** Green `#d1f0dc/#14532d` = supported, ready, in order; amber `#fde8b8/#7a4a00` = needs a
  person; red `#f8d0d0/#7f1d1d` (solid `#b91c1c/#fff` for Blocked) = blocked, contradicted, not found; grey = not run.
  Icons ✓ ! ✕ – on every status. One map in `lib/ui.tsx`; Streamlit mirrors it (builder).
- **U3 · Landing page `/`.** One sentence ("Every AI-assisted output that becomes a record gets a passport: what it
  rests on, who approved it, and what changed since"), three entry cards (Check a document · Records · Information
  manager), a four-step strip (Check → Gate → Passport → Recall), and live counts from `/dashboard`. Records moves to
  `/records`; old links redirect.
- **U4 · Directory.** The top bar groups: **Work** (Check a document, Records) | **Information manager** (Dashboard,
  Recall, Setup) | More. Every page gets a title and a one-line "what this page is for" caption; Check → passport →
  Records keeps the user on one path with a "Next" link at each step.
- **U5 · Bias check row.** A visible row in "Checks done on this record": "Bias check: evidence rests on 4 independent
  current sources" (green) or "Bias check: narrow evidence, rests on one source" (amber), with the detail listing the
  sources. **Wording guard (Hasim chose the name; the rest stays honest):** never "unbiased", "bias-free" or "no bias
  found". The detail explains it checks how broad and how current the evidence is, which is one way bias gets in.
  Engine needs a per-passport `bias` check in `/view` (builder, B1 below).
- **U6 · Dashboard additions** (all from the API, no client maths): filed per week (last 8 weeks), gate outcomes by
  document type, by model (filed, recalled), bias-check results, review queue (open/closed), overdue reviews, and the
  reliability card (done). Each tile links to the filtered Records list.
- **U7 · Streamlining.** Issue passport goes straight to the passport. Empty, loading and error states on every page.
  Phone width checked on each page. Remove "Passport detail" (the Records page is the passport). Setup: three questions,
  plus the strictness picker once `GET /policy/levels` ships (W2).
- **U8 · Presenter reset.** A guarded reset for the stage URL only (a secret header from Vercel env), so a rehearsal can
  restart from the slide, not a terminal. Only if the builder agrees; otherwise the deployer resets via `stage.py`.

**Engine (builder)**
- **B1 · Bias check** in `view.checks`: id `bias`, status ok (≥2 independent current authoritative sources),
  attention (one source, or any weak, draft or superseded), not_run (no sources); details list the sources and why.
  Reuse the narrow-evidence logic from the dashboard. The row label is "Bias check".
- **B2 · Dashboard series:** `filed_by_week`, `gate_by_type`, `by_model`, `bias_results`, `queue`, with plain labels.
- **B3 · Name:** "Record Passport" in the PDF and the console header; colours U2 in Streamlit.
- **B4 · (optional) `POST /stage/reset`**, guarded by an env secret and enabled only when `RECORDCHECK_STAGE=1`.

**Planner review (15:10):**
1. **B1 wording: count, don't claim independence.** Two records from the same case system aren't independent. The ok
   line reads "Bias check: rests on 4 current authoritative sources across 3 systems"; ok needs ≥2 sources from
   ≥2 systems; one system or one source → amber "narrow evidence". The guard words stand.
2. **"Try your own document" is check-only.** It runs `/check` and shows the result; it never files a passport into
   the production DB (no auth, public URL). A banner: "Don't paste personal or sensitive information; nothing you paste
   is stored." Confirm `/check` stores nothing for ad hoc bodies (citation cache entries hold only reference text).
3. **Builder order** (G1 stays ahead, per Hasim): L1 merge → G1 → B3 → B1 → W2 levels → B2 → B4 → D3 → M1 → G2 → G4.
4. **Name change:** README, the pitch brief and the slides say Record Passport; `CLAUDE.md` still says Record Check
   (Hasim edits that file himself).

**Order:** L1 merge and deploy → U1 + U2 (small, visible) → U3 + U4 → B1 → U5 → B2 → U6 → U7 → U8. Each step is
deployed to preview, then to the stage URL, then promoted. Cut if short: U8, then U6's weekly series.

### V3 · IM rules framework (after parity; design room reserved now)
The IM configures the engine for any sector or document; no code per sector.
1. **Information asset register** as the source of authoritative systems, modelled on OVIC's Sample IAR
   Template V2.0 (`reference/Sample-IAR-Template-V2.0.xlsx`): asset name, owner, custodian, location,
   status (current / non-current), BIL integrity, disposal class. Import an IAR spreadsheet; an asset's
   status and integrity level decide whether its records count as authoritative 💭.
2. **Field rules** per asset: "a claim about *X* is checked against field *Y* (equals / within range /
   dates overlap)". Generalises the single occupants rule; closes EC-EVI-12, 14, 16, 18, 19.
3. Document types and quality bars (exist), with validation (EC-POL-07). Every policy change versioned;
   the passport records the policy hash it was judged against (exists).
4. LLM may suggest rules; the IM confirms every one (existing rule: no LLM sets a threshold or weight).

### V4 · Production hardening
Auth and roles (IM, author, reviewer; enforces separation of duties properly), API keys for systems that
plug in, secrets only in Vercel env, chain-head anchoring (EC-PAS-03), backups and retention of the DB
itself, error monitoring, rate limits, remaining ❌ rows closed or accepted in writing.

## State
- **19 Oct:** plan written. Edge-case register built (129 rows: 93 ✅, 31 ❌, 5 ⛔, `115 passed, 31 xfailed`).
  V0 not yet tagged; Vercel CLI not yet installed. Next: V0 tag (needs Hasim's OK to commit), then V1.1.
- **19 Oct, V1.1 backend safety (uncommitted):** the gate now runs inside `passport.build`, so no caller can
  skip it; `/passport` re-derives citations and verdicts server-side (pulled forward from V2.4, with EC-API-10).
  Closed 18 gaps: EC-GAT-01/02/10/11/14, EC-PAS-04/09/10, EC-API-06/07/08/10, EC-EVI-07, EC-DIS-09, EC-POL-07,
  EC-LLM-03/04/05; added EC-LLM-10, EC-API-14/15/16. Register: 115 ✅, 13 ❌, 5 ⛔; `137 passed, 13 xfailed`.
  Seed demo gates unchanged. Still open from V1.1: negation (EC-EVI-09). V0 is tagged at `3f66ba2`, so the register
  and edge tests land with V1.
- **19 Oct, V0 tagged and V1.2–1.3 done (uncommitted):** local tag `v0` → `3f66ba2`. Repo root linked to
  Vercel project `record-check` (team The Record Breakers). Deploy config is three files: `vercel.json`
  (Services: service `api`, root `prototype/record-check`, public at `/api/*`), `.vercelignore` (allowlist;
  keeps `.env`, local DBs and tests out of the upload, since Vercel doesn't skip `.env` by default) and
  `prototype/record-check/api/vercel_app.py` (mounts `api.main:app` under `/api`, points `RECORDCHECK_DB` and
  `RECORDCHECK_POLICY` at `/tmp`, `ponytail:` comment on the per-instance reset). No engine or test change, no new dep.
  Preview: `https://record-check-f1i0nmho6-the-record-breakers.vercel.app` (protected; test with
  `vercel curl /api/health --deployment <url> --scope the-record-breakers`). Smoke test passed: `/api/health`,
  `POST /api/check` on `DOC-2026/0412-summary` (identical to local), `/api/chain/verify` (40, intact), `/api/docs`.
  Caveats: (1) the project's first deploy was auto-assigned to **production**, so `https://record-check.vercel.app`
  serves V1 publicly (production isn't behind Vercel Authentication); (2) CLI deploys upload the working tree,
  so the preview includes the uncommitted V1.1 engine changes; (3) the Vercel MCP is signed in to the personal
  scope only (403 on the team), so use the CLI until it's re-authorised. V2: add `"web": {"root": "web"}`, a final
  `{"source": "/(.*)", "destination": {"service": "web"}}` rewrite and `!/web` in `.vercelignore`.
- **19 Oct, V2 first slice: Check page live on preview (uncommitted).** Hasim chose to leave the production URL public.
  The Vercel MCP is now authorised for the team. API additions in `api/main.py` (additive, the backend chat
  agreed): `GET /documents`, `GET /records`, `GET /policy`; `/check` takes an optional `document_type` and then
  returns `gate` (before review). Test `test_read_endpoints_and_check_gate`; `138 passed, 13 xfailed`.
  `web/`: Next.js 16.4.2, one client page (`app/page.tsx`, ~200 lines) that reproduces the Streamlit Check tab:
  document and type selectors, counts, gate pill and reasons, citations, sentence highlights (click or keyboard
  opens the trace) and the trace table. TS types are generated from the OpenAPI schema (`npm run types` → `openapi.json`,
  `lib/api.d.ts`, both committed so the Vercel build needs no Python); the only extra dep is `openapi-typescript`
  (dev). Dev runs `uvicorn api.main:app --port 8000` + `npm run dev`; a dev-only rewrite proxies `/api/*`.
  `vercel.json` now has services `api` + `web` (`/api/(.*)` → api, then `/(.*)` → web). Preview:
  `https://record-check-i8i1lsgge-the-record-breakers.vercel.app`, clicked through in a browser: the summary gives
  Blocked (8 reasons) and the contradicted HUMAN sentence traces to REC-2026/003540; the eligibility note gives Ready to file.
  `web/AGENTS.md` is written by `next dev` itself; commit it.
  **Next V2 slices:** File as record / Passport (POST /passport), then Recall, Disposal, Register, Setup (these
  need API endpoints for disposal, register and policy save). The backend chat's `/passport` contract, to follow:
  send claims exactly as /check returned them (the server re-checks citations and re-weighs, and mismatched verdicts → 422);
  409 = blocked with `detail = {gate, reasons}` (the gate always runs, even without document_type); 422 = refused (tier below the
  rules, reviewer == event.user, duplicate record_id, unknown type, blank reviewer). The /check gate preview passes
  no author, so self-review only shows at /passport. Bound Policy inputs to QualityBar (no negatives, shares 0–1,
  `citations_not_checked_attention`).
- **19 Oct, engine chat added source-record endpoints:** `GET /sources/health` (SourceHealthReport: redundant,
  obsolete, trivial and draft labels, flagged first) and `POST /recall/record` (`{record_id, mark?: {superseded_by, reason, by}}`
  → SourceRecallResult; 404 unknown, 422 bad replacement). RecordStatus gains `draft`. Demo: mark REC-2026/004790
  superseded by REC-2026/004912 → 13 outputs (4 T2). `web/` types regenerated (`npm run types`), and the build still passes;
  `147 passed, 14 xfailed`. These are candidates for the Register and Recall pages. Vercel reseeds `/tmp` on each cold
  start, so the next deploy has the new seed records; the local `data/recordcheck.sqlite` needs `db.seed(conn, force=True)`.
- **19 Oct, V2 all six tabs on preview (uncommitted; this chat is the deploy agent).** API: console endpoints added to
  `api/main.py` (`/passports`, `/models`, `/recall/queue`, `/audit`, `/disposal/due|approve|register`, `/presets`,
  `PUT /policy`, `/policy/preset`, `/policy/suggest`); `/passport` uses the type's default tier as the floor. Tests
  `test_console_endpoints` and `test_passport_tier_floor_is_document_type_default`; `149 passed, 14 xfailed`. Web: shared
  `lib/ui.tsx` (api helper, colours, pills) and a nav in the layout; pages `/setup`, `/` (Check + File as record), `/passport`,
  `/recall` (model recall + recall by source record), `/disposal`, `/register` (+ source record health). Two Sonnet
  subagents built the pages; `next build` is clean. Preview `https://record-check-cob70njbl-the-record-breakers.vercel.app`,
  browser click-through: Setup renders; summary Blocked with Issue disabled; eligibility Ready → passport
  REC-2026/005113 (T2) issued; Recall 14 (3 T2); Disposal 6 due; Register renders. **Fails:** the filed passport was gone
  seconds later (`GET /api/passport/REC-2026/005113` 404, list back to 40), because SQLite in `/tmp` is per instance. So
  Check → Passport and any IM change (policy save, mark faulty, disposal) cannot be relied on across requests on Vercel.
  Fix: Postgres (V2.3, Neon via the Marketplace), awaiting Hasim's OK to provision. Also: the Passport page silently
  falls back to the first record when `?id=` isn't found; it should say "not found".

## Done when
V2 runs the demo path on the Vercel production URL, the Streamlit console is retired to a fallback, and
every version from V0 has an entry in `docs/versions.md` and a git tag.
- **19 Oct, production deploy:** built locally (engine `149 passed, 14 xfailed`; `next build` clean), deployed
  preview `record-check-3heuq1r7m`, smoke-tested (web 200; `/check` gate blocks the seed summary; tier downgrade
  422; forged `supported` verdicts 409; chain ok, 40), promoted to production. `record-check.vercel.app` now runs
  the backend-safety engine and the web chat's `web/` as of that moment. Still uncommitted.
- **19 Oct, negation (EC-EVI-09) fixed:** "does not / doesn't / never / no longer … alone" now reads as not alone
  (supported by 2 occupants; contradicted by 1). Change is in `recordcheck/evidence.py` only. Suite `150 passed,
  13 xfailed`. V1.1's five demo gaps are all closed. Handed to the deploy agent.
- **19 Oct, deploy agent:** promoted `record-check-cob70njbl` (all six tabs) to production on Hasim's OK. Prod check:
  all pages 200, the summary gate is blocked, the chain is ok (40). The negation fix is deployed to preview `record-check-75slj8pja`
  (smoke test: c1 supported, c2 contradicted; demo summary unchanged); promoted to production on Hasim's OK, and the prod
  check passed (negation, summary blocked, chain ok 40, all six pages 200). **Neon:** Hasim approved;
  `vercel integration add neon --plan free_v3 -m region=iad1 -m auth=false --name record-check-db` was
  provisioned once Hasim accepted the terms: store `record-check-db` (free, iad1), connected to Production and Preview
  (`DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `PG*`, `POSTGRES_*`). The current code ignores it until the `db.py` port
  lands; deploys are on hold until the engine chat says it's green. The install also added `.agents/`, `.claude/skills/`
  (Neon agent skills) and `skills-lock.json` at the repo root, which are not uploaded. The engine port of `db.py` to Postgres is requested from the backend-safety chat.
- **19 Oct, V2.3 Postgres on Neon (preview):** the builder's port (db.py adapter, schema files, chain under advisory
  lock, policy in the DB) is deployed to preview `record-check-iuhlvqqxb`. Smoke test: self-seed on first request, chain
  ok 40; passport REC-2026/005113 filed and read back 200 ×6; policy PUT v2 → v3, persisted on 3 reads; chain ok 41.
  `api/vercel_app.py` comment updated (the /tmp lines are now only a fallback without DATABASE_URL). **Caveat:**
  Preview and Production share one Neon database, so preview writes (this smoke passport, policy v3) are production data.
  Reset before the stage (S2), or give previews a Neon branch.
  **Promoted to production** on Hasim's OK. Prod check: chain ok 41, REC-2026/005113 200 ×3, policy v3, summary gate
  blocked, all six pages 200. `record-check.vercel.app` now keeps writes.
- **19 Oct, deploy agent: S1 + S2 + S3 + B3 + B2 on production.** On Hasim's OK, reset the shared Neon DB with
  `scripts/stage.py reset --database-url … --yes` (URL pulled to a temp file and deleted after; never printed): 40
  passports, 20 records, policy v2, chain ok 40. Then promoted preview `record-check-bwbhk2ign`. Prod checks: S1 sentence
  weak for decision-letter (intended use excludes it) and supported for briefing; summary Blocked 2/2/2/1; negation ok;
  B3 `/api/passport/REC-2026/002444.pdf` 200 application/pdf; B2 `/api/sources/reliability` 29/29; six pages 200.
  Suite `170 passed, 11 skipped, 13 xfailed`. Production DB = stage data now: no test writes against it. Not yet
  in web/: the PDF link on Passport, the B2 figure, the intended-use columns (types regenerated).
- **19 Oct, deploy agent: held for the Neon preview branch** (Hasim chose one shared `preview` branch; Production keeps
  `main` = stage data; needs `npx neonctl auth` from Hasim). Queued: S4, G3, P1, P2 (builder), relied_on (`/check` returns
  `relied_on`; `/passport` sets `source_record_ids` from the evidence) and **P3 web passport-first UI**: `/` = Records
  (picker, passport header, 8 checks as expanders from `/passport/{id}/view`, PDF link, all records), `/check` = Check a
  document (now sends `relied_on`), and an Information manager sub-nav (Setup, Recall, Disposal, Register, Passport detail).
  Browser-tested locally (filed → lands on Records with full checks; seed passports show "summary counts only").
  Suite `191 passed, 11 skipped, 13 xfailed`; `next build` clean.
- **19 Oct, deploy agent: Neon preview branch live.** Neon project `quiet-feather-33630786` (org "Vercel: The Record
  Breakers"): branch `preview` (br-purple-king-b8aj35v5) created from `main`. The Vercel store is now connected to
  **Production only** (`main` = stage data); Preview has its own sensitive `DATABASE_URL` (pooled, preview branch).
  Reseed the preview branch any time: `stage.py reset --database-url "$(npx neonctl connection-string preview
  --project-id quiet-feather-33630786 --pooled)" --yes`. Isolation verified: a passport filed on preview
  `record-check-5zoaakszy` reads 200 there, 404 on prod; preview chain 41, prod 40. Bundle smoke on that preview
  (commit 561c21a + P4 web): relied_on overrides a forged source; P1 view at_issue true; G3 overdue 1; S4 government
  cite not_checked; summary Blocked 2/2/2/1; 7 pages 200. Promote waits for Hasim.
  Also added (Hasim's request): Neon MCP at project scope via OAuth (`.mcp.json`, no key in the file) and skill
  `neon-postgres-branches` (`.claude/skills/`, `skills-lock.json`).
  **Promoted to production** on Hasim's OK, then reset the prod `main` branch with stage.py (40 passports, 20 records,
  policy v2, chain ok 40). Prod check: G3 overdue 1 (REC-2026/004809); B2 share 1.0; summary Blocked 2/2/2/1 with
  `relied_on`; P1 view 8 checks; 40 passports; the preview test passport is 404 on prod; 7 pages 200.
- **19 Oct, deploy agent: V2.x B + C live on production** (built to Hasim's design canvas,
  `docs/demo/design-passport-view.dc.html`; team colours blue/orange/solid orange/grey per decisions.md). Records = list +
  passport hero (headline from `/summary`, filed-by line, PDF button) + visible six-group passport + "Checks done on this
  record" as individual rows from `/view`; unknown id → not found. Nav: Records · Information manager (Dashboard, Recall,
  Setup; Disposal/Register/Passport detail only with `NEXT_PUBLIC_SHOW_ALL=1`, unset in prod). New `/dashboard` (no client
  maths, "Narrow-evidence signals"); Recall leads with "Mark a source superseded"; Setup = three questions. Check page takes
  function and prompt from the document; web reads stored naive-UTC times as UTC (local display). Builder fixed the
  aware/naive recall 500 in the engine. Preview `record-check-e3l8sqqhp` (preview branch reseeded) clicked through:
  summary Blocked + Issue disabled, eligibility Ready → REC-2026/005113 → lands in Records with 8 checks; Dashboard, Recall,
  Setup render; `/recall/record` 004790→004912 gives 13 (4 T2). Promoted, then reset prod `main` (Hasim pre-approved): 40
  passports, chain ok; summary Blocked 2/2/2/1; preview passport 404 on prod; pages 200. Suite `209 passed, 11 skipped,
  13 xfailed`. Known gap: Setup has no strictness picker (LEVELS not in the API).
- **19 Oct 14:33, deploy agent: demo path clicked through twice on production** (Hasim asked). Both runs, no errors
  or 4xx/5xx: Setup renders → Check: summary **Blocked**, Issue disabled → eligibility note **Ready to file** →
  passport issued (REC-2026/005113, then 005114; T2) → lands in Records: "Ready to file" headline, PDF button, 8 check
  rows → Recall: northstar-7 marked faulty, **14 affected / 3 T2**, 3 queued (run 2: 0 new, 3 already queued) →
  Disposal: 3 due / **3 on hold** → back on the passport, Since filing OK (its model, northstar-8, isn't recalled).
  Chain ok (43). These runs wrote to prod `main`: 2 passports, northstar-7 faulty, 3 queue entries. A third passport,
  REC-2026/005115 (03:34 UTC), was filed by someone else in the same minute. The parity gate ("clicks through twice
  on the Vercel URL") is met for the web app; offline use and the backup video are separate (05-demo-ops).
  Then, on Hasim's OK, reset prod `main` with stage.py: 40 passports, chain ok, northstar-7 active, queue empty,
  005113 gone (404).
