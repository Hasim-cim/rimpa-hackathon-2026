# CLAUDE.md

Team workspace for the RIMPA Global Hackathon 2026 (19–21 Oct). **This repo is the single source of
truth**: research, ideas, decisions, the pitch, and the prototype all live here.

Start with `README.md`. If you were asked to work on one task, open its brief in `workstreams/` first:
it says what is done, what is next, which files to read, and what "done" means.

## Rules

1. **Verify before you assert.** The judges are records professionals and an NAA executive. One wrong
   fact on stage costs the pitch. Check anything unsure against a primary source, and prefer the
   `research/` files over memory.
2. **Keep the three markers honest.** A link means the page was opened. ⚠️ means a search snippet only.
   💭 means our design or inference. Never upgrade ⚠️ to a link without opening the page.
3. **Don't repeat refuted framings.** They're listed in `research/deep-research-2026-10-16.md`, along with
   the corrections in `docs/background-analysis.md` §9 (45 years not 99, Robodebt was not AI, and so on).
4. **One source of truth.** New findings go into `research/`, decisions into `docs/decisions.md`, idea
   changes into `ideas/`, task progress into the brief in `workstreams/`. Update `README.md` status when
   the lead idea or a rule changes. Nothing project-related lives outside this repo.
5. **The prototype lives in `prototype/record-check/`.** Whether code written before the event is allowed
   is still open (question 1); if Monday's rules forbid it, it was a rehearsal and we rebuild from the
   contracts in its `ARCHITECTURE.md`. Follow that file's module contracts; change `models.py` first when
   a shape changes; keep `uv run pytest -q` green and offline.
6. **The pitch hero is the information manager**, not the end user. Every feature should answer
   "which records act does this perform?"
7. **Wording.** Never "true", "false" or "fake". Say "supported by authoritative records", "not found",
   "possibly fabricated". Never "captures everything": the NAA rule is risk-tiered.
8. **Working style.** Autonomous subagents run on Sonnet; the main session reviews their output and looks
   for product improvements. Ask Hasim before decisions that change direction (scope, stack, waiving a
   rule); don't ask for routine ones. Commit only when asked.

## Facts that are easy to get wrong

- Judging criteria come from the hack pack p. 27 (Idea & Solution, Fit, Functionality, Presentation &
  Team), not from the event web page.
- The mentor is **Michelle** Tolliday (ISO/TC 46/SC 11). The PDF's text layer has stale names in it.
- The NAA risk-tiered rule means **not every prompt is kept**. Don't pitch "capture everything".
- Everything in the prototype's seed data is invented (cases, people, records, the fabricated
  references). References [2] Spicker 2023 and [3] Edmiston 2024 are real papers. The model vendors
  "Northstar" and "Atlas" are fictional. Sector presets are our starting points, not regulators' rules.

## Running the prototype

```bash
cd prototype/record-check
uv sync                                          # once
uv run streamlit run app/streamlit_app.py        # console, http://localhost:8501
uv run uvicorn api.main:app --reload             # engine as an API
uv run pytest -q                                 # offline, keyless, ~3 s
```

Keys and switches live in `prototype/record-check/.env` (git-ignored; copy from `.env.example`). The demo
runs fully offline from seed data; the Claude API (Haiku) and live Crossref/OpenAlex are upgrades.
