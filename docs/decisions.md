# Decisions

| Date | Decision | Why | By |
|---|---|---|---|
| 15 Oct | Park the blockchain provenance idea | Tried before (ARCHANGEL). Integrity isn't truth. Records must be correctable and disposable | Hasim, research |
| 15 Oct | Drop open-domain fact-checking as the core | Crowded, ~72% agreement at best, no IM role | Hasim, research |
| 16 Oct | Move the Passport from a browser button to a **gateway** | Fixes adoption, model-version visibility and over-retention, and targets NAA's agentic gap | Hasim, research |
| 17 Oct | Shortlist for Sunday: **Record Check** (citation check → evidence weight → passport → recall) as lead, its own floor (citations + passport) as fallback, record-of-issue check as standalone backup | Four of the top five ideas are steps of one workflow; cutting from the bottom never means starting over. See the idea book | Hasim, Claude |
| 17 Oct | Product form: **web app** (Streamlit console) over an engine (Python package + FastAPI), plus a **printed passport PDF** for the judges. The gateway proxy is a scale slide, not the demo | Judges are records people; they need something to click and hold. A proxy is invisible on stage | Hasim, Claude |
| 17 Oct | Build the prototype now in a **sibling repo** `~/repos/record-check`, not in `prototype/` | Open question 1 is unanswered. If pre-built code is banned, it's a rehearsal and we rebuild Monday; if allowed, we move it in | Hasim |
| 17 Oct | Stack: Python 3.12, Streamlit, FastAPI, SQLite; Claude API for claim splitting only, with a deterministic offline fallback | One-day build, offline-safe demo, the API response carries the model id | Hasim |
| 17 Oct | Add **Policy studio** (IM sets sector, document types, quality bar, authoritative systems) and **Disposal with recall hold** to Record Check | Puts the IM in the control loop before the first prompt (brief Q5); shows not every prompt is kept; records stay disposable with the chain intact | Hasim |
| 18 Oct | **One source of truth:** the prototype moved into `prototype/record-check/` (history kept via git subtree); the sibling repo is archived. Rule 5 amended | Parallel chats need one repo to read and write | Hasim |
| 18 Oct | Parallel work runs as briefs in `workstreams/`; each chat updates its brief | So the team can split up without losing state | Hasim |
| 18 Oct | *Lead idea and fallback: TBD on the team call* | | Team |
