# 01 · Build and enhancements

**Goal:** a demo that runs one path perfectly, offline-safe, by Monday 14:30, plus the few enhancements
that strengthen the pitch. Code lives in `prototype/record-check/`.

## State

**Done (17 Oct):** engine (citations, evidence, passport + hash chain, recall, disposal with recall hold,
policy studio + filing gate), Streamlit console with six tabs, FastAPI wrapper enforcing the gate,
seed data (2 cases, 4 documents, 40 passports, 4 sector presets), 62 offline tests. Haiku
(`claude-haiku-5-5`) for claim splitting and profile suggestions; live Crossref/OpenAlex with cache.

**Next, in priority order:**
1. **Printed passport.** Export a one-page passport PDF (the six groups, tier, hash, policy version) so
   judges can hold a record of an AI-assisted decision. Button on the Passport tab. (reportlab or
   weasyprint; keep it dependency-light.)
2. **Recall honours "faulty from".** `recall.recall()` ignores `effective_from`; it should list only
   passports created on or after that date, and say how many were excluded.
3. **Sidebar truth.** Show the real model id (`llm.MODEL`) and "cache + live" state in the sidebar.
4. **Policy guardrails.** Warn on bars looser than the preset; show the policy hash on the Register tab;
   write policy diffs (not just a summary) to the audit log.
5. **UI polish for the stage:** bigger type on the gate banner and the recall tiles; shorten metric
   labels that truncate ("Citations f…"); click a sentence to open its trace (currently a selectbox).
6. **Contradiction rules beyond household** (e.g. employment status from the file note), each as an
   explicit rule with a reason sentence.
7. Hosting: a named Cloudflare tunnel on a stable domain + QR code (see 05).

## Read first
`prototype/record-check/ARCHITECTURE.md` (contracts), `README.md` there, then the module you touch.
Concept and tiers: `ideas/concept-records-gateway.md`. Policy studio: `ideas/concept-policy-studio.md`.

## Rules that bite
- Change `models.py` first when a shape changes, then the module, then tests. Hashes use
  `exclude_none`, so adding optional fields is safe; renaming fields is not.
- Tests stay offline and keyless (`tests/conftest.py` strips the key). Anything touching the API or
  network is monkeypatched or `skipif`.
- No LLM decides a weight, tier, gate or record. It splits text and suggests profiles only.
- Wording rules in `CLAUDE.md` §7. No emoji in the UI.
- Subagents on Sonnet; review their diffs. Feature freeze Monday 14:30.

## Done when
The demo path (Setup → Check: Blocked → fix/eligibility note: Ready → Passport → Recall: 14/3 →
Disposal: holds) clicks through twice without error on the venue laptop, offline, and a backup video exists.
