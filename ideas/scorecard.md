# Idea scorecard

## Rubric

Each column is scored 1–5. The first four are the hack pack's judging criteria. The last two are our
own filters.

| Column | Asks |
|---|---|
| **Idea** | Is it creative? Would the judges have seen it before? |
| **Fit** | Does it solve a real problem for an **organisation and its information manager**? |
| **Function** | Could it work and scale in the real world? |
| **Pitch** | Can it land in 5 minutes with one demo moment? |
| **IM core** | Is a real records act (capture, metadata, appraisal, keep or destroy) at its centre? |
| **8h build** | Can we show it working by Monday 3 pm? |

Anything scoring **≤ 2 on IM core** is a generic AI tool.

## Round 1 scoring (15 Oct)

| # | Idea | Idea | Fit | Function | Pitch | IM core | 8h build | **Total** |
|---|---|---|---|---|---|---|---|---|
| 1 | Fact-check overlay (Hasim's original) | 2 | 2 | 2 | 4 | 1 | 2 | **13** |
| 2 | Blockchain provenance | — | — | — | — | — | — | parked |
| 3 | "Save as record" capture | 3 | 5 | 4 | 3 | 5 | 4 | **24** |
| 4 | Citation check before filing | 3 | 5 | 4 | 5 | 3 | 5 | **25** |
| 5 | AI provenance metadata standard (protocol) | 3 | 4 | 3 | 2 | 5 | 5 | **22** |
| 6 | Model-retirement watch / recall | 5 | 4 | 3 | 4 | 5 | 3 | **24** |
| 7 | Archive reference triage | 4 | 3 | 4 | 4 | 4 | 4 | **23** |
| 8 | AI-assisted reparative description | 4 | 3 | 3 | 3 | 4 | 3 | **20** |
| 9 | "Verify against the archive" for fake historical images | 4 | 3 | 2 | 4 | 3 | 2 | **18** |

**Why idea 1 scores low:**
- The space is crowded (GPTZero, NewsGuard, Originality.ai).
- Google Scholar has no API.
- The best open-ended fact-checking agrees with humans only about 72% of the time.
- There's no information manager in it.

The instinct is right, though: a live layer sitting where AI is used. We kept the layer and changed
what it does.

**Why blockchain is parked:**
- It has been tried before, in ARCHANGEL.
- Integrity isn't truth.
- Records must sometimes be corrected or destroyed.
- Long-term preservation is a risk.

The gateway gets tamper evidence from a hash chain instead (see the concept).

## Round 2, after the deep research (16 Oct)

Ideas 3, 4 and 6 combine into the **AI Record Passport**, and the research moved it from a browser
button to a **records-aware gateway**:

| Weakness of the button version | Fixed by the gateway? |
|---|---|
| Staff have to click "save" (Price: "shelfware") | ✅ Capture is automatic, because every call passes through |
| The ChatGPT web page doesn't show the model version | ✅ The API response carries the model id |
| Keeping every prompt is over-retention | ✅ NAA's risk tiers decide what is kept |
| Doesn't touch agentic AI | ✅ Agent actions are logged as the highest tier, NAA's [admitted gap](../research/deep-research-2026-10-16.md) |

| Idea | Idea | Fit | Function | Pitch | IM core | 8h build | **Total** |
|---|---|---|---|---|---|---|---|
| **Records-aware AI gateway / Passport** (3 + 4 + 6) | 4 | 5 | 4 | 4 | 5 | 3 | **25** |

**Current lead.** The full design is in [concept-records-gateway.md](concept-records-gateway.md).
**Fallback:** idea 4 on its own, the simplest build with the strongest demo.

The team makes the final pick on the Sunday call. Log it in [`../docs/decisions.md`](../docs/decisions.md).

## Pressure-test log

| Judge | Question | Answer we'd give | Status |
|---|---|---|---|
| Price | "Staff won't click 'save as record'. What happens when 80% don't?" | Nobody clicks. Capture happens at the gateway every AI call already passes through, and NAA's own risk tiers decide what becomes a record. The information manager sets the rules once. That is the strategic role. | ✅ answered by the gateway pivot |
| Secis | *next* | | |
| Christensen | *next* | | |
| Long | *next* | | |

## Round 3, after the prototype (17 Oct)

New candidates from Hasim's notes and the build. Unscored until the Sunday call.

| Idea | Idea | Fit | Function | Pitch | IM core | 8h build | Notes |
|---|---|---|---|---|---|---|---|
| **Policy studio** (IM setup: sector, document types, quality bar, authoritative systems) | | | | | | | Layer on Record Check. Puts the IM in the control loop before the first prompt. [Concept](concept-policy-studio.md) |
| **Evidence weight** (ontology layer: claims traced to authoritative records, AI or not) | | | | | | | Built in the prototype as step 2. Hasim's reframe of the blockchain thread |
| **Disposal with recall hold** | | | | | | | Built. T0 destroyed after 90 days with approval; held while the model is under recall; chain still verifies |
| **Record-of-issue check** (forged documents) | | | | | | | Standalone backup. Not built |
| **Statistic passport** (voting / census trust) | | | | | | | Hook only. No clear IM |
