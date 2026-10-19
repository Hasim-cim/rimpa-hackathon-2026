# 05 · Demo, hosting and backup

**Goal:** the demo cannot fail on stage. Offline first, hosted second, video third.

## State

**Done:** app runs offline from seed data; live lookups and the LLM are optional upgrades; Cloudflare
*quick* tunnel tested (`cloudflared tunnel --url http://localhost:8511`; URL changes each run and dies
with the laptop). Keys in `prototype/record-check/.env`: Anthropic (about $5 credit; Haiku costs cents),
OpenAlex free key, `RECORDCHECK_ONLINE=true`.

**Stage path v2, passport-first (planner, 19 Oct 12:50). Supersedes item 1 below. Rehearse and time it.**
Start on a fresh stage DB (`scripts/stage.py` reset). All data is invented; say so once.

| # | Click | Say (one line) |
|---|---|---|
| 1 | **Records** (sidebar): the list of passports, the passport card, the checks | "Every AI-assisted output that became a record has a passport. This is what the information manager sees." |
| 2 | Red **Check a document** button: hardship summary, type *decision letter* → **Blocked** | "An AI sentence is green, a human sentence is red, and one reference is possibly fabricated. It can't be filed." |
| 3 | **Check**: eligibility note, type *case note*, name a reviewer → **Issue passport** → lands on its passport | "This one rests on current authoritative records." |
| 4 | Open the checks one by one: Citations, **Evidence** (4 of 4 supported, open a sentence and its records), Sources, Filing gate (Ready), Review, Integrity, Retention | "Every check that was done, and the evidence behind each, kept with the record." |
| 5 | Sidebar **Information manager** → **Sources**: reliability tile "30 of 30" (29 seed + the note just filed) → mark **REC-2026/004790** superseded by **REC-2026/004912** → tile drops to **17 of 30**, the notice named as the cause | "The debt notice was reissued. Yesterday's answers still rely on the old one." (knee-surgery line here, worded per the research file) |
| 6 | Recall by source: 13 outputs, 4 T2 → **Queue T2** | "Prevent, not treat: four decisions are queued for review before anyone relies on them again." |
| 7 | Back to **Records**: click a row whose status reads "Changed since filing" → **Since filing** check | "The passport itself now says its source changed." |
| 8 (if time) | Recall by model; Disposal: 3 held, approve the rest, chain verified | "Records stay disposable, and the chain still verifies." |

**Fallbacks:** if live lookups fail, references read "to confirm", never "possibly fabricated" (say so). If the console
fails, use the screenshots in `docs/demo/` and the backup video. **Check before rehearsal:** step 7 needs a passport
that lists 004790 as a source: pick it from the recall list in step 6.

**Next:**
1. **Demo script, click by click** (write it in this file): Setup → Check (hardship summary, decision
   letter: Blocked) → document: eligibility note (Ready) → reviewer, Issue passport → Passport tab →
   Recall: mark northstar-7 faulty, 14 / 3, queue → Disposal: 6 due, 3 held, approve 3 → chain verified.
   Note what to say at each click and the fallback if a step fails.
2. **Offline mode for the stage:** set `RECORDCHECK_ONLINE=false` and pre-warm the citation cache; or
   keep online and let a network error read as "not checked" (never "not found"). Decide and test both.
3. ~~Reset script~~ done: see **Stage database** below.
4. **Hosting for judges' phones:** a *named* Cloudflare tunnel on a domain Hasim controls, stable URL,
   QR code on the last slide. Fallback: the quick tunnel started on the morning.
5. **Backup video** of the full path, on two devices, plus screenshots of each tab in `docs/demo/`.
6. **Venue laptop checklist:** HDMI adaptor, hotspot, `uv sync` done, `.env` present, fonts/zoom set for
   a projector (browser zoom 125%, Streamlit wide mode).

**Stage database (S2, done 19 Oct).** The demo runs on its own target, never the DB other chats share.
- Local (the stage laptop): `uv run python scripts/stage.py reset`, then
  `RECORDCHECK_DB=data/stage.sqlite RECORDCHECK_POLICY=data/stage-policy.json uv run streamlit run app/streamlit_app.py`.
  Reset before each rehearsal: back to the seed (40 passports, default policy, empty disposal register and review
  queue), chain verified, and it prints a one-line summary.
- Postgres (a Neon branch made for the stage, not the shared Preview/Production DB):
  `uv run python scripts/stage.py reset --database-url <stage URL> --yes`. The script never reads `DATABASE_URL`
  from the environment, so it cannot wipe the shared DB by accident.

## Read first
`prototype/record-check/README.md`, `team/03 Game plan.md` (Monday timeline, rules for the day).

## Rules that bite
Share the tunnel URL with the team only: anyone with the link spends the API credit. Never commit `.env`.

## Done when
Two clean run-throughs on the venue laptop with Wi-Fi off; video on two devices; QR code resolves.
