# 05 · Demo, hosting and backup

**Goal:** the demo cannot fail on stage. Offline first, hosted second, video third.

## State

**Done:** app runs offline from seed data; live lookups and the LLM are optional upgrades; Cloudflare
*quick* tunnel tested (`cloudflared tunnel --url http://localhost:8511`; URL changes each run and dies
with the laptop). Keys in `prototype/record-check/.env`: Anthropic (about $5 credit; Haiku costs cents),
OpenAlex free key, `RECORDCHECK_ONLINE=true`.

**Next:**
1. **Demo script, click by click** (write it in this file): Setup → Check (hardship summary, decision
   letter: Blocked) → document: eligibility note (Ready) → reviewer, Issue passport → Passport tab →
   Recall: mark northstar-7 faulty, 14 / 3, queue → Disposal: 6 due, 3 held, approve 3 → chain verified.
   Note what to say at each click and the fallback if a step fails.
2. **Offline mode for the stage:** set `RECORDCHECK_ONLINE=false` and pre-warm the citation cache; or
   keep online and let a network error read as "not checked" (never "not found"). Decide and test both.
3. **Reset script:** one command that deletes `data/recordcheck.sqlite*` and `data/policy.json` and
   restarts the app, so each rehearsal starts clean.
4. **Hosting for judges' phones:** a *named* Cloudflare tunnel on a domain Hasim controls, stable URL,
   QR code on the last slide. Fallback: the quick tunnel started on the morning.
5. **Backup video** of the full path, on two devices, plus screenshots of each tab in `docs/demo/`.
6. **Venue laptop checklist:** HDMI adaptor, hotspot, `uv sync` done, `.env` present, fonts/zoom set for
   a projector (browser zoom 125%, Streamlit wide mode).

## Read first
`prototype/record-check/README.md`, `team/03 Game plan.md` (Monday timeline, rules for the day).

## Rules that bite
Share the tunnel URL with the team only: anyone with the link spends the API credit. Never commit `.env`.

## Done when
Two clean run-throughs on the venue laptop with Wi-Fi off; video on two devices; QR code resolves.
