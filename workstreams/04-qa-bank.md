# 04 · Judge Q&A bank

**Goal:** an answer, in one or two sentences, for every question the judges are likely to ask, each
grounded in the product as built or a sourced fact. Lives in `team/04 Pitch and Q&A prep.md` (fill the
answer column) and the pressure-test log in `ideas/scorecard.md`.

## State

**Done:** 10 likely questions listed; Price's "staff won't click save" answered by the gateway pivot.

**Next:** draft answers for all ten, then add these from the build, which judges will spot:
- "Who checks the reviewer is real?" → a *named* reviewer recorded in the passport; authentication is
  an integration with the agency's identity system, not built. Say "named", never "verified".
- "Can the IM just set the bar to zero?" → yes, it is their decision; the passport records the policy
  version and hash, and policy saves are audited, so it is visible later.
- "If you destroy records, doesn't the hash chain break?" → no: the content is destroyed, the hash and
  chain position stay; the chain reports "N disposed entries retained as hash stubs".
- "Isn't this Purview / Langfuse?" → wait for 03's table. Current line: logging is plumbing; the records
  layer (tiers, disposal, metadata, policy, recall) is the product.
- "What stops staff using personal ChatGPT?" → policy and network control, as for any records system; the
  register makes bypass visible.
- "What about personal information in prompts?" → T0 kept 90 days then destroyed with approval; T1+
  follows the business record; APP 11 tension handled by the tier.
- "How accurate is the evidence check?" → it reports evidence found or not found, never a verdict; the
  rules are deterministic and explainable; the LLM only splits sentences.
- "Which model version made this record, and what if it's gone?" → the passport stores the model the
  API returned; recall finds every record a model produced, sorted by risk.
- Long (information warfare): "What about a deliberate attacker planting a source?" → the authoritative
  systems list is a whitelist the IM owns; a planted web page can never become evidence.
- Christensen: "Which metadata standard?" → the six groups; mapping to ISO 23081 per 03.
- Secis: "How does this fit NAA guidance?" → it implements the risk-tiered rule and the agentic list;
  tiers and retention are configuration an agency sets.

**Added 19 Oct from session 1 deep research** (wording and sources in `research/session-1-outcomes-2026-10-19.md`):
- "Vendors already clean up ROT; isn't this that?" → they clean the repository; we trace which AI outputs relied on a
  source and recall them when it's superseded. Purview logs accessed files, but we found no workflow that acts on them.
- "Why not sentiment analysis for intent?" → tone isn't evidence; we use the IAR's own Purpose field plus conditions of use.
- "Isn't ROT just delete-it?" → no: flag and review; a superseded record is still a record and keeps its disposal authority.
- "How do you know people over-trust AI?" → Microsoft Research, N=404: 80.9% agreement with an unhedged AI.
- "Why now?" → Queensland's guidance names outdated documents and ROT as AI risks; Privacy Act APP 1.7 from 10 Dec 2026.

Pressure-test each answer against the live app: if the app can't show it, soften the claim.

## Read first
`team/04 Pitch and Q&A prep.md`, `ideas/scorecard.md` (pressure-test log), `ideas/concept-records-gateway.md`
(Risks and answers), `ideas/concept-policy-studio.md` (Honest limits), `docs/background-analysis.md` (judges).

## Done when
Every question has an answer and an owner who will say it; the three hardest have been rehearsed.
