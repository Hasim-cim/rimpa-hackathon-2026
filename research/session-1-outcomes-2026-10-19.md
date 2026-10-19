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

## Open for Hasim 💭

- **Prevent rather than treat** pulls against the 19 Oct decision "no real-time correction". Proposed answer that
  keeps the decision: `/check` is an API any AI search tool can call before an answer is used, plus a proactive
  risk feed for the IM (superseded records still being cited, models under recall, references nobody confirmed).
- **Intent:** answer with a records control, not sentiment analysis. Give each record or asset a purpose /
  permitted-use field ("draft for discussion", "not for decisions about individuals") and flag a decision document
  that relies on a record outside its purpose. A sentiment score would be a model judgement, which breaks the rule
  that the model never decides a weight.
- **Knee-surgery example:** use it as a fictitious superseded clinical guideline in the health-service preset.
- **Build pick for today:** `draft` status, purpose / permitted use, metadata mapping, or duplicate detection.
