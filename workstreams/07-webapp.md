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
