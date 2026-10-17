# Deep research, idea directions (16 Oct 2026)

**Method:** 5 search angles, then 20 sources fetched, 95 claims extracted, and the top 25 checked by
3-vote adversarial verification. **23 were confirmed and 2 refuted.** Raw output:
[`deep-research-2026-10-16.json`](deep-research-2026-10-16.json).

> [!IMPORTANT]
> **This upgrades the background analysis.** Several NAA claims in
> [`docs/background-analysis.md`](../docs/background-analysis.md) were marked ⚠️ *unverified* because
> naa.gov.au timed out. This run fetched the [NAA page](https://www.naa.gov.au/node/3660) itself and
> confirmed them 3–0. Where the two documents disagree, this one wins.

## Confirmed findings

### 1. Every Australian regulator treats AI output as a record. High confidence
- **Commonwealth (NAA):** "AI generated content created or received by Australian Government agencies
  constitutes Commonwealth records… and must be managed as such."
  ([NAA](https://www.naa.gov.au/node/3660))
- **NSW:** "AI-generated content is a State record."
  ([NSW](https://www.nsw.gov.au/nsw-government/recordkeeping/create-and-capture/ai-and-recordkeeping))
- **Victoria:** AI content is public records, including contractors' work.
  ([PROV policy](https://prov.vic.gov.au/sites/default/files/files/documents/ai_tech_and_recordkeeping_policy_v1_2024.pdf))
- **Queensland:** **prompts, responses and conversations** are public records.
  ([QLD](https://www.forgov.qld.gov.au/information-technology/recordkeeping-and-information-management/recordkeeping/resources-and-tools-for-records-management/artificial-intelligence-and-public-records))

### 2. NAA's capture rule is tiered by risk, explicit enough to code. High confidence
- Agencies don't have to keep every prompt. Prompts, inputs and source data are kept **only when they
  give context to a retained output or show how a decision was reached.**
- *"The greater the significance of the record or the reliance placed on AI decision-making, the
  stronger the need for supporting evidence."*
- Logs are low value but need a **set** retention period. *"Some common AI assistants retain logs
  permanently unless configured otherwise."*
- AI content accepted as a final record without human review must say in its metadata that **AI
  generated it**.
- Queensland's QChat keeps records 3 months and disposes after 6. Copilot and ChatGPT may have no
  automatic retention.

### 3. AI tools are not recordkeeping systems. High confidence
Records must be captured *"with sufficient metadata in a system where they can be appropriately
managed… not left solely in an AI tool"* (NAA). *"Generative AI systems are not recordkeeping
systems"* (QLD). **That leaves a structural gap** between where AI work happens and where records are
managed.

### 4. The minimum metadata is already defined. High confidence
- **NSW:** a confirmation that AI generated it, the software used, and the prompts, inputs or
  algorithms. The metadata must be **"perpetually linked"** to the record.
- **QLD (must):** the **source of the data can be identified**, and the AI content is **related to the
  final official document**.
- **QLD also admits** that source identification *"may not be readily available… in some systems such as
  Microsoft 365 Copilot"*. That is a mandated control the common tools can't meet.

### 5. Victoria's policy is a ready-made spec for an AI use register. High confidence
For each AI technology, record its purpose, how and why it is used, the records it produces, the data
it can and can't access, and its risks. Where possible, also document how **bias in algorithms and
datasets, IP, and hallucinations** are *"addressed"*: the research done, the action decided and why,
the risk accepted, and the mitigations (PROV clause 1, footnote 8). The policy never uses the words
"AI use register"; that mapping is ours.

### 6. Human oversight of checking and disposal. Medium confidence (one jurisdiction)
PROV requires that accuracy checks on AI records be overseen by a **skilled human with authority and a
documented line of responsibility**. Disposal of AI records needs human oversight.

### 7. Agentic AI is the openly acknowledged gap. High confidence ⭐
NAA's section *"Managing records relating to agentic AI technologies – New"*, updated September 2026,
says the advice *"does not currently provide specific guidance on managing agentic AI records"*. It
names **system prompts, agent instructions, activity logs and audit trails** as records to capture,
says autonomous actions need more evidence, and promises further advice.

### 8. Paradata, from InterPARES Trust AI. Medium confidence (one scholarly source)
Capture *paradata*, data about the methods, processes and people behind a record, **throughout** AI use.
Accountability comes from documenting **who chose the tool and the data**, not from explaining the
algorithm. A Bank of Canada case study splits paradata into:
- **technical:** training data and parameters, usage logs, vendor documentation, version;
- **organisational:** AI policy, regulation and ethics, project planning, staff training, impact
  assessment, implementation procedure.

([Feliciati & Duranti, JLIS.it 2025](https://jlis.it/index.php/jlis/article/view/636))

### 9. DTA transparency statements. High confidence
Commonwealth agencies must publish an AI transparency statement in a fixed format, reviewed at least
annually. It classifies usage by pattern and domain (Attachment A) and covers uses where the public is
affected without human review.
([DTA](https://www.digital.gov.au/ai/ai-in-government-policy/standard-ai-transparency-statements))

### 10. The global story is EU AI Act Article 12. Medium confidence (scope and timing)
High-risk AI systems must allow **automatic event logging** over their lifetime, for traceability and
post-market monitoring ([Art 12](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-12)).
It covers **high-risk only**, so most office copilots are out of scope. A verifier reported the
obligations deferred to 2027–28 ⚠️ *unverified*.

### 11. DTA Technical standard for government's use of AI (31 Jul 2025). Medium confidence
Its lifecycle statements cover enabling AI auditing, managing bias, version control and watermarking.
These line up with records controls, but the standard doesn't cite ISO 15489 or the Archives Act.

## Refuted, so don't say these
- ❌ "NSW guidance says AI tools don't capture records automatically" (0–3).
- ❌ "DTA transparency statements leave a use-case register gap that we fill" (0–3).

## Ranked directions from the synthesis
1. **A records-aware AI gateway** for LLM and agent calls. It applies NAA's risk tiers, stamps the
   required metadata, writes paradata, and exports a record package. It targets the agentic gap.
2. **An AI use register plus a transparency-statement generator** built from the PROV, DTA and paradata
   fields.
3. **Source traceability and citation checking**, linking each output to its sources and to the final
   document. This is the QLD rule Copilot can't meet.
4. **A human oversight workflow** for accuracy sign-off and disposal (PROV).

## Gaps this run did not close
- **Existing commercial products** (LLM observability tools, Purview for Copilot, records vendors' AI
  features) weren't verified, **so no novelty claim is safe yet**. See [`open-questions.md`](open-questions.md).
- There is no verified evidence that automatic capture beats manual declaration.
- C2PA, ISO 23081 element mapping, ISO/IEC 42001, NIST AI RMF, reparative description, and the NZ, UK
  and US archives positions produced no surviving claims.
- **The gap may be closing:** NAA says agentic guidance is coming.
