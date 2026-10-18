# 03 · Research: novelty and standards

**Goal:** make every claim on stage safe, and find out what we can say is new.
Findings go into `research/` with the three markers (link / ⚠️ / 💭). Tick off `research/open-questions.md`.

## State

**Done:** background analysis; 16 Oct deep research (23 confirmed, 2 refuted); NAA risk-tiered rule and
agentic gap confirmed. Question 9 answered: Claude API; the response carries the model id
(`claude-haiku-5-5`), which the passport stores as "model returned".

**Next, in priority order:**
1. **Novelty (open questions 2–5).** Open the docs and record what each actually does:
   - LLM gateways and observability: Langfuse, Helicone, Portkey, LiteLLM. Do they log the model id per
     call? Any retention tiers, disposal, record export, or "find everything model X produced"?
   - Microsoft Purview for Copilot / AI apps: what the interaction audit schema holds (model version?),
     retention, anything like recall.
   - Records vendors: RecordPoint, Objective, OpenText. Any AI-interaction capture as records?
   - Verdict per product in a table; then write the one-paragraph novelty claim we *can* make.
2. **Standards mapping (question 6).** Map the passport's six groups onto ISO 23081 entities, the NSW AI
   metadata rule and InterPARES paradata. Check W3C PROV-O and ICA Records in Contexts (RiC-O) before we
   name them for the evidence layer; currently ⚠️.
3. **NAA agentic guidance (question 7):** has it landed? If yes, cite it; if not, "you said it's coming,
   here is a working answer".
4. **NAA Check-up 2025 figures (question 8)**: open the source before anyone quotes them.
5. **Record-of-issue check**: do certificate verification registers already exist in AU government?
   (Decides whether idea 5 is a backup or dead.)
6. Pre-built code rule (question 1): email admin@rimpa.com.au if not already done; else ask at 08:00 Mon.

## Read first
`research/open-questions.md`, `research/deep-research-2026-10-16.md` (incl. "Gaps this run did not close"),
`docs/background-analysis.md` §9, `ideas/concept-policy-studio.md` (honest limits).

## Rules that bite
Rules 1–3. A ⚠️ never goes on a slide. Record the URL you opened and the date.

## Done when
Open questions 2–8 have a status and a source; `research/novelty-2026-10.md` exists with the product
table and the claim we can make; 02 and 04 have been told what changed.
