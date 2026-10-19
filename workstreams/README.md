# Workstreams

One brief per parallel task, so a new chat can pick it up cold. To start a chat on one:

> Open Claude Code in `~/repos/rimpa-hackathon-2026` and say: **"Work on `workstreams/02-pitch.md`."**

Each brief has the same shape: goal, state (done / next), files to read first, rules that bite, and the
done criterion. **When you finish a step, update the brief's State section** and log any decision in
`docs/decisions.md`. That is how the other chats learn what changed.

| # | Brief | Owner (suggested) | Due |
|---|---|---|---|
| 01 | [Build and enhancements](01-build.md) | Hasim | Mon 14:30 freeze |
| 02 | [Pitch script and slides](02-pitch.md) | Storyteller | Mon 15:00 mentor pitch, Tue 10:00 final |
| 03 | [Research: novelty and standards](03-research.md) | Expert | Sun call, then Mon midday |
| 04 | [Judge Q&A bank](04-qa-bank.md) | Expert | Mon evening |
| 05 | [Demo, hosting and backup](05-demo-ops.md) | Hasim | Mon 14:30 |
| 06 | [Sunday team call](06-sunday-call.md) | Team | Sun 18 Oct |
| 07 | [Production web app on Vercel, V1 → V4](07-webapp.md) | Hasim | V1 by Mon 14:30, V2 at parity |

Shared vocabulary: **Record Check** is the product. Its steps are **check citations → weigh evidence →
issue the passport → recall**, configured in the **Policy studio** (Setup tab), with **Disposal** for
transitory entries. Tiers T0–T3. Weights supported / weak / unsupported / contradicted. Citation statuses
found / mismatch / not found / not checked. Gate: Ready to file / Needs attention / Blocked.

## Plan to Tuesday 10:00 (written Mon 19 Oct, 11:45) 💭

The product now covers every point from session 1 except **intent**. The biggest risk is no longer missing
features: the **pitch and the demo script still describe Sunday's product**. So the next 3 hours go to the
story, the stage setup and one small build. Session 1 is in `research/session-1-outcomes-2026-10-19.md`.

**A. Before the 14:30 freeze (must)**

| # | Task | Brief | Why |
|---|---|---|---|
| A1 | Rewrite the pitch spine in the room's words: open on Andrea's "is my AI search giving back reliable results?" and "AI sounds confident"; name ROT; "prevent, not treat" = source health + recall by source | 02 | The mentor heard these words this morning; the pitch should answer them back |
| A2 | Add a **Sources** beat to the demo script: the debt notice is reissued → mark superseded → 13 outputs, 4 T2 → queue. Our stand-in for their knee-surgery example (invented data, no clinical claims) | 05 | It's the newest and most "prevent" feature, and it isn't in the script yet |
| A3 | **Stage database:** run the demo on its own file (`RECORDCHECK_DB=data/stage.sqlite`) with a one-line reset, so rehearsals never touch the DB the other chats share | 05 | The shared local DB is stale (no draft, copy or reissue) and must not be reseeded |
| A4 | Backup: screenshots of each tab and a screen recording of the full path | 05 | Venue Wi-Fi and laptop risk |
| A5 | **Intended use** on records: a `purpose` field ("draft for discussion", "not for decisions about individuals"); a claim in a decision document that rests on a record outside its purpose reads weak with that reason. Small: models → evidence → seed → tests → Sources tab column | 01 | The one session-1 point we don't answer. A records control, not sentiment analysis |

**B. After the mentor pitch, Monday evening (should)**

| # | Task | Brief | Why |
|---|---|---|---|
| B1 | Apply mentor feedback first; it outranks everything below | all | |
| B2 | **AI search reliability number** for Andrea: share of retained outputs whose claims all rest on current authoritative records, and the sources dragging it down. From passports' evidence summaries plus source health | 01 | Answers "tell me the accuracy" with one figure |
| B3 | **Printed passport** PDF, one page, for the judges to hold | 01, 02 | Already the top build item; still not done |
| B4 | Close **EC-EVI-14 / EC-SRC-10**: check the numbers in a sentence linked by wording. A judge typing a wrong amount live is the likeliest way to break the demo | 01 | Credibility in Q&A |
| B5 | **Novelty table** (open questions 2–5), now also for ROT tools: records vendors (including OpenText, our host) already sell ROT clean-up. Our line has to be "we trace which AI outputs relied on a source and recall them", and it must be checked before it's said | 03, 04 | "Isn't this just X?" is the likeliest question |
| B6 | Q&A answers for: ROT vs vendor clean-up tools; why not sentiment for bias; what "prevent" means without real-time correction; Privacy Act APP 1.7 (10 Dec 2026) as the scale and why-now line | 04 | New since Sunday |
| B7 | Web app: a Sources page at parity with the console (endpoints exist) | 07 | Only if V2 is the stage UI |

**C. Only if time (could)**: metadata mapping view (IAR columns → our record fields, the "we read your
metadata" point); seed document that cites the draft policy so a draft shows in Check; sidebar truth; policy
guardrails; UI polish for the projector; more contradiction rules.

**Drop:** 01 item 2 "recall honours *faulty from*". It contradicts EC-REC-05 (over-inclusive by design, the
information manager triages), and that is the better answer for a records audience.

