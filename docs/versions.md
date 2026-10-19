# Versions

One row per version of Record Check. Plan and steps: [`workstreams/07-webapp.md`](../workstreams/07-webapp.md).
Each version is tagged in git (`v0`, `v1`, …). "Built" says when, so the pre-built-code question can be
answered for any version.

| Version | Built | What it is | Tests | Tag | Status |
|---|---|---|---|---|---|
| V0 | 17–18 Oct (before the event) | Streamlit console, FastAPI wrapper, SQLite; engine with citations, evidence, passport + chain, recall, disposal, Policy studio + filing gate. Edge-case register added 19 Oct | 115 passed, 1 skipped, 31 xfailed (gaps) | — | To tag |
| V1 | 19 Oct (event day) | Backend safety: gate enforced inside the engine, API re-derives citations and verdicts, tier floor, separation of reviewer and author, 18 gaps closed. **API on Vercel (preview):** `https://record-check-f1i0nmho6-the-record-breakers.vercel.app/api/…` (Vercel Authentication on; use `vercel curl`). `/health`, `/check` on the seed draft (same result as local: citations not_checked/found/mismatch/not_found; 2 supported, 2 weak, 2 unsupported, 1 contradicted), `/chain/verify` (40 passports, intact) and `/docs` work, offline, no API key. SQLite resets per instance. Negation (EC-EVI-09) fixed after this; all five V1.1 demo gaps closed | 150 passed, 1 skipped, 13 xfailed | | In progress |
| V2 | 19 Oct → | Next.js console on Vercel; Postgres; server-side assessment. **All six tabs** (Setup, Check + File as record, Passport, Recall, Disposal, Register) on **production** (passport-first since 19 Oct: Records · Check a document · Information manager) `https://record-check.vercel.app` (promoted from preview `record-check-cob70njbl`). **Postgres (Neon, iad1) live on production:** writes persist across instances (passport and policy round-trips checked); Preview and Production share one DB, reset to stage seed on 19 Oct. Also live: intended use on records (S1), stage DB reset (S2), console smoke test (S3), printed passport PDF (B3), reliability figure (B2), simple Policy studio (S4), review-date flag (G3), passport view with checks stored at issue (P1–P4), relied-on sources set server-side. Previews run on a separate Neon branch. Negation fix (EC-EVI-09) live on production | 150 passed, 1 skipped, 13 xfailed | | In progress |
| V3 | After parity | IM rules framework: information asset register (OVIC IAR model) + field rules | | | Planned |
| V4 | After the event | Auth and roles, API keys, chain-head anchoring, monitoring, backups | | | Planned |
