# Session 1 outcomes, 19 Oct (build day)

Team notes from session 1 with practitioners, pasted into chat as written. Andrea and Juan are attendees.
These are what the room said they care about, not verified facts.

## What they said

- People trust AI output by default because it **sounds confident**: they want model reliability,
  hallucination checks, and model recall.
- **They already have metadata.** Extend it rather than invent a new scheme. Find out theirs, or use
  fictitious metadata to make the point.
- **ROT (redundant, obsolete, trivial)** is a concept they already use. Test the framework against it.
- **Volume:** data keeps growing and nobody has time to check everything manually, one by one.
- **Andrea:** "Is my AI search giving back high-quality, reliable results?" They want something that
  already tells them the accuracy.
- **Juan:** intervene early and remove retroactive work: prevent rather than treat. Raise risks
  proactively.
- **Outdated information, multiple versions, and drafts** that aren't the final agreed document. Their
  example: a knee surgery that was once standard but is no longer recommended.
- **Intent:** it isn't only whether information is accurate. Is a document being used against its
  original intent? Does the AI output faithfully reflect the original message? The bias question
  (sentiment analysis was floated).

## Mapping to Record Check 💭

| They said | Record Check today | Gap |
|---|---|---|
| Confident AI, hallucination | Evidence weight per claim; citation check; model registry and recall | None. Lead with it |
| Existing metadata | `SourceRecord`: system, authoritative, status, superseded_by, fields | Show their schema mapped onto ours |
| ROT: obsolete | `superseded` → weight `weak` (`evidence.py`) | Name it "obsolete" in the UI |
| ROT: redundant | `hashing.py` exists; no duplicate check | Duplicates and drafts not detected |
| ROT: trivial | Non-authoritative sources → `weak`; T0 tier | Name it in the UI |
| Drafts | `RecordStatus` = current / superseded / disposed | No `draft` status |
| Volume | Risk tiers; only weak or unsupported claims need a human | Pitch as management by exception |
| Accuracy up front / prevent | Gate before review (`/check` with `document_type`) | A source-health check before the AI uses a source |
| Intent / faithfulness | Weight `contradicted` | No "intended use" on records; no faithfulness check on qualifiers |

## Deep research, 19 Oct (verified)

Four research passes, one per theme. Full evidence, with every claim marked (link = opened, ⚠️ = snippet,
💭 = ours), is in [`session-1-evidence/`](session-1-evidence/). The main session re-opened the Queensland page
and the Microsoft Research abstract to confirm them. Everything below is safe to say as worded; check the
evidence file before changing the wording.

### Stage-safe lines

| Session 1 theme | What we can say | Source |
|---|---|---|
| **Outdated docs, ROT** | Queensland Government guidance already names the problem: a generative AI system "may use an outdated document", and keeping ROT "may lead to confusing or incorrect responses from AI". It asks agencies to "ensure ... that the source of data can be identified" | [Queensland Government, updated 5 Dec 2024](https://www.forgov.qld.gov.au/information-technology/recordkeeping-and-information-management/recordkeeping/resources-and-tools-for-records-management/artificial-intelligence-and-public-records) |
| **AI sounds confident** | In a pre-registered Microsoft Research experiment (N=404, FAccT 2024), people agreed with an unhedged AI 80.9% of the time; when the AI was wrong, they got 33.0% of answers right, against 64.7% with no AI | [arXiv 2405.00623](https://arxiv.org/abs/2405.00623) (N and direction in the abstract; figures from the full text) |
| **Is my AI search reliable?** | Purpose-built legal AI research tools, grounded in documents, gave hallucinated answers 17–33% of the time in a pre-registered Stanford study. One cited a real case for a point resting on an overruled decision. The vendors disputed the method | [Stanford, arXiv 2405.20362](https://arxiv.org/pdf/2405.20362) |
| **Wrong answers carry liability** | A BC tribunal held Air Canada responsible for its chatbot's bereavement-fare answer, which conflicted with its own policy page: C$812.02 in total (2024 BCCRT 149) | Secondary pages opened; the decision itself was blocked. Don't say the cause was outdated content |
| **Knee surgery (superseded guidance)** | In 2017 a BMJ guideline panel made "a strong recommendation against the use of arthroscopy in nearly all patients with degenerative knee disease". The Australian Knee Society said similar in 2019. Say "the guidance changed" | [BMJ 2017;357:j1982](https://pmc.ncbi.nlm.nih.gov/articles/PMC5426368/), [AKS 2019](https://www.kneesociety.org.au/resources/Position-Statement-from-the-Australian-Knee-Society-on-Arthroscopic-Surgery-of-the-Knee-Final-2019.pdf) |
| **Medicine has a word for it** | "Medical reversal": one analysis of more than 3,000 trials in three major journals found 396 established practices later shown no better than a lesser therapy | Herrera-Perez et al., eLife 2019 (see evidence file) |
| **Intent / original purpose** | OVIC's Sample IAR Template V2.0 already has "Purpose (primary purpose of collection)": "whether the information asset may be used for other purposes without modification", to "determine the original intent". Our `purpose` field extends it; `not_for` is our extension of ICA RiC's "Conditions of Use" | `reference/Sample-IAR-Template-V2.0.xlsx`, Supplementary tab (main session re-read it); ICA RiC-CM v1.0 |
| **Superseded links** | The same template's "Type of relationship" has "Replaces / Replaced By": our `superseded_by` | Same workbook |
| **Why not sentiment** | Sentiment analysis measures opinion and tone, not whether a source supports a claim, and some systems show race and gender bias (Kiritchenko & Mohammad 2018, 219 systems). Faithfulness research checks claim by claim against the source, as we do | Evidence file |
| **Volume (say "reported")** | KPMG/University of Melbourne (48,000+ people, 47 countries): 66% rely on AI output without evaluating its accuracy. Workday (3,200): about 37% of AI time savings is lost to rework | Surveys; see evidence file |

### Novelty: recall by source record
**Partly exists.** Microsoft Purview's Copilot audit log lists the files Copilot accessed (`AccessedResources`), and
LLM tracing tools (e.g. Langfuse) record retrieved documents. A July 2026 research preprint invalidates cached
answers when documents change. In the documentation we reviewed we did **not** find a records workflow that
recalls retained AI outputs, by risk tier, when a source record is superseded. Say exactly that. Never "first",
"only" or "nobody does".

### Don't say
- That anyone coined ROT, or that RIMPA, ARMA, NAA or ISO define it (not found). Use "redundant, obsolete,
  trivial" and "flag and review", never "delete ROT": a superseded record is still a record.
- Anything about OpenText's products (every OpenText page was blocked). Ask the mentors instead.
- That Air Canada's or NYC MyCity's errors came from outdated content (no source states a cause).
- That Medicare banned knee arthroscopy (the 2021 change restricted and reworded items), or "doctors stopped doing
  it" or "it doesn't work". Keep to degenerative knee disease.
- Any AGRkMS or ISO 23081 element name or number (pages blocked; ⚠️ only).
- Any statistic on growth in AI-generated content (none found), or the NAA Check-up 2025 figures (secondary only).
- "Copilot cannot show its sources" (it shows citations to users; the Queensland line is about records source data).

### Still to check in a browser before Tuesday
NAA AI position statement; AGRkMS v2.2 PDF (Rights, Use Permission); ACSQHC knee osteoarthritis Clinical Care
Standard (2024) wording; the Moffatt decision text; OpenText product pages; Queensland page's Act reference.

## Garbage in, garbage out: how Record Check tackles bad information 💭

Session 1's concerns are one problem: **an AI answer is only as good as the records it draws on**. Queensland's
guidance says the same: "Information made through generative AI systems is only as accurate as the information
the response is sourced from" (see Deep research). AI makes bad information faster and more confident; it
doesn't create a new kind. So the answer is a records answer, applied at four points. Each control answers
"which records act does this perform?" (rule 6).

| Point | The garbage | Control | Records act | Session 1 voice | State |
|---|---|---|---|---|---|
| **1. In: the sources** | Redundant copies, obsolete versions, drafts, trivial or unofficial sources, records used outside their purpose | Only current, approved, authoritative records that are fit for this document type count as evidence. Source health shows the rest as ROT or draft, for the IM to fix at the source | Appraisal, classification, authority control | ROT; drafts; "intent"; "we already have metadata" | ✅ built (source health, `draft`, intended use) |
| **2. Through: the answer** | Confident claims with no support; real citations used for things they don't say; fabricated references | Every claim weighed against the records; every reference looked up; "sounds confident" is never evidence | Evidence of business, reliability | "AI sounds so confident" | ✅ built; ❌ numbers and dates inside a sentence matched by wording (G1) |
| **3. Out: filing** | Unsupported output becoming the official record | The filing gate blocks it; the passport records the evidence, model and reviewer | Capture, registration, metadata | "prevent rather than treat" | ✅ built |
| **4. Later: when a source changes** | Yesterday's answer still being relied on after the record changed | Recall by source and by model; the reliability figure drops the moment a source is superseded | Review, disposal, recall | knee surgery; "intervene early" | ✅ built |

**The question a judge will ask: "What if the authoritative record itself is wrong?"** Then Record Check passes
it, and says so: it checks support, not truth. Fixing a wrong record is records management's job (correction
with a version chain), and the moment the corrected version supersedes it, recall finds every output that used
the old one. The debt-notice demo is exactly that. Two improvements make the answer stronger:
**records that disagree** are flagged to the IM (G2), and **records past their review date** are flagged (G3).

**Never say** "Record Check stops misinformation" or "catches everything". Say "it shows which statements are
supported by authoritative records, which aren't, and why, and it tells the IM where the source needs fixing".

**Build items for garbage in (queued for the builder after B4; specs in `workstreams/01-build.md`):**
G1 facts must match, not just words · G2 records that disagree · G3 review-date flag · G4 dropped qualifiers.

## Open for Hasim 💭

- **Prevent rather than treat** pulls against the 19 Oct decision "no real-time correction". Proposed answer that
  keeps the decision: `/check` is an API any AI search tool can call before an answer is used, plus a proactive
  risk feed for the IM (superseded records still being cited, models under recall, references nobody confirmed).
- **Intent:** answer with a records control, not sentiment analysis. Give each record or asset a purpose /
  permitted-use field ("draft for discussion", "not for decisions about individuals") and flag a decision document
  that relies on a record outside its purpose. A sentiment score would be a model judgement, which breaks the rule
  that the model never decides a weight.
- **Knee-surgery example:** researched (see above). Use it as an analogy in the pitch, worded as "the guidance changed"; the demo keeps the invented debt-notice story.
- **Built 19 Oct:** `draft` status, duplicate detection, source health (ROT), recall by source record, intended use (`purpose`, `not_for`). Still open: metadata mapping view (plan C).
