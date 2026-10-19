# Deep research: what information managers use now, and what Record Check adds (19 Oct)

Run with the deep-research workflow (searches, fetches and verifiers on Sonnet). It fetched 19 sources,
extracted 58 claims and verified 25: 21 survived and 4 were refuted (3 verifier votes per claim, 2 refutes
kill). Raw output is in the session scratchpad and isn't kept. **Read this alongside**
[`deep-research-2026-10-16.md`](deep-research-2026-10-16.md) and
[`session-1-evidence/rot-and-vendor-tools.md`](session-1-evidence/rot-and-vendor-tools.md). Those files
already cover Purview's Copilot audit log (`AccessedResources`), DSPM for AI, SharePoint Advanced Management and
RecordPoint. This file adds what's new.

Markers as usual: a link means a verifier opened the page, ⚠️ means a search snippet only, 💭 means our
inference.

## What information managers use today

### 1. Purview is the baseline records toolkit. High confidence
Retention labels declare records, applied manually or auto-applied by sensitive info, keywords or
content type. Purview also offers a file plan for importing retention schedules, event-based retention,
disposition review, proof of deletion and export of disposed items. Regulatory-record labels can't be
auto-applied. ([Microsoft Learn, updated 25 Jun 2026](https://learn.microsoft.com/en-gb/Purview/records-management))

### 2. AI interactions get one blanket retention policy, not per-record control. High confidence
State Records NSW's Microsoft 365 guidance (May 2025) gives Copilot experiences and Enterprise AI apps
(e.g. ChatGPT Enterprise) an example policy: keep 10 years, then destroy automatically. The guidance
says "No action is possible, the items will be deleted automatically". Retention labels "cannot be
applied to ... Copilot engagements or Enterprise AI apps messages" ([SRNSW guidance, Attachment A
pp. 90–91](https://www.nsw.gov.au/sites/default/files/2025-07/state-records-nsw-managing-records-in-microsoft365-guidance.pdf)).
- Caveats: this is state guidance, not Commonwealth, and an **example** policy, not a mandate. It's a
  snapshot from May 2025.
- 💭 Our reading: the information manager can't tier, annotate or recall one AI output through labels.
  **Don't say "no provenance"**: the Purview audit log does list the files Copilot accessed (see
  rot-and-vendor-tools.md). The gap is acting on a single output, not logging it.

### 3. NAA: AI material is a Commonwealth record, kept on risk. Medium confidence
AI-related material is a Commonwealth record under the Archives Act (technology-neutral). Low-value
drafts and summaries can go under normal administrative practice. Final outputs, outputs relied on for
decisions and those that evidence high-risk activity need keeping. Prompts and inputs are kept only where
they support a retained output.
([RIMPA summary of NAA guidance](https://www.rimpa.com.au/resource/managing-records-created-with-ai-technologies-in-government.html))
"Building trust in the public record" is extended to 31 Dec 2028
([RIMPA](https://www.rimpa.com.au/resource/building-trust-in-the-public-record-extended-to-2028.html)).
- The NAA primary page timed out, so this rests on RIMPA's secondary page. Sources disagree on the
  guidance's publication date: check naa.gov.au before quoting a date.
- "Risk-tiered" is our paraphrase. RIMPA names no formal tiers.

### 4. ISO 23081 is about actions on records, not only description. Medium confidence
ISO 23081-1:2017 ties metadata to the ISO 15489-1 statements and covers defining and managing the
actions taken on records ([RIMPA, 21 Jan 2025](https://www.rimpa.com.au/resource/metadata-standards-for-records-management-iso-23081-series.html)).
The ISO text itself wasn't opened. 💭 This event focus suits the passport, which logs events on the record.

### 5. Transparency rules exist, and compliance is patchy. Medium confidence
- ADM+S, *AI Transparency in Practice*, found "outright non-compliance" in several cases and about 30
  entities with no statement we could find ([PS News](https://psnews.com.au/?p=173970); the report PDF
  wasn't opened). Statements have been due since about Feb 2025 ⚠️ (inferred: the DTA page timed out).
- **NAA Check-up 2025** (175 agencies, Sept–Dec 2025): 87% use AI, but only 15% use it for information
  management and 8% for metadata creation
  ([RIMPA IM blog](https://www.rimpa.com.au/resource/im-blog-naa-check-up-ai-is-everywhere-so-why-is-it-missing-from-records-management.html);
  also idm.net.au/node/15699 ⚠️; the NAA PDF timed out). **A strong pitch line**, but cite it as the NAA
  Check-up via RIMPA until the PDF is opened.

### 6. Citation checkers exist, and all of them check scholarly indexes. High confidence
- **CheckIfExist** (preprint): Crossref, Semantic Scholar and OpenAlex in cascade, with a string-similarity
  confidence score ([arXiv 2602.15871](https://arxiv.org/abs/2602.15871)).
- **AAAI-26 student abstract**: three stages (exact lookup, fuzzy search, LLM check) give Valid, Partially
  Valid or Hallucinated ([AAAI](https://ojs.aaai.org/index.php/AAAI/article/download/42257/46218)).
- **RefChecker**: deterministic filters, then an LLM with web search, then a re-compare to clear
  false positives from out-of-date databases. It uses Semantic Scholar, OpenAlex, Crossref, DBLP and ACL
  Anthology ([docs](https://docsearch.algolia.com/mcp/docs/repo/markrussinovich/refchecker)).
- 💭 **Our difference:** none of them check against an organisation's **authoritative records**. Ours
  is the records layer, and the scholarly lookup is our fallback. We can borrow their staged pattern
  (exact, then fuzzy, then LLM) and graded confidence.

### 7. Their accuracy evidence is thin, so hedge it. Medium confidence
AAAI-26 pilot: about 200 citations (about 30 hallucinated), about 80% precision, about 65% recall with exact lookup
alone and about 75% with fuzzy search added. It's a 2-page abstract, and CheckIfExist is a preprint
([AAAI](https://ojs.aaai.org/index.php/AAAI/article/download/42257/46218)). The verifier noted that a flag
is a likelihood judgement, not proof, which backs our "possibly fabricated" wording. **Don't quote an accuracy figure
for our own tool.**

### 8. RIMPA's AI conversation is about governance and people, not tools. Low confidence
The RIMPA AI roundtable page frames AI around governance gaps, data quality, skills and trust, and names
no tool for detecting fabricated citations
([RIMPA AI roundtable](https://www.rimpa.com.au/events/ems-events-calendar/ai-roundtable.html)). That's one
page, so it's weak support for "unfilled niche".

## Refuted, so don't say these
- ❌ "Per RIMPA, keeping metadata, prompts and inputs for high-risk outputs is a provenance gap we fill" (1–2).
- ❌ "The NAA Check-up shows agencies don't identify which AI material is a record" (1–2).
- ❌ "The check-citations skill sorts references as fabricated / chimeric / modified-real" (0–3).
- ❌ "Citation tools admit they miss grey literature" (0–3).

## 💭 What Record Check adds, by records act

| Records act | Addition | Sits on top of | Why the current toolset can't |
|---|---|---|---|
| Classify and assess | A risk-tier decision per AI output (NAA keep-or-destroy logic) | Purview retention labels or policy | Copilot and AI app items take only a blanket policy, not labels (§2) |
| Capture and describe | The passport: ISO 23081-style event metadata attached to the kept output | EDRMS or SharePoint record | The audit log is an investigation log you export, not a record's metadata |
| Verify evidence | Check claims against authoritative records: exact, then fuzzy, then LLM, with graded confidence | The organisation's records, with Crossref/OpenAlex as fallback | Existing checkers see only scholarly indexes (§6) |
| Recall | When a source record is found unreliable, list the downstream records that relied on it | Passport links | No workflow acts on a superseded source (rot-and-vendor-tools.md) |
| Dispose | The policy studio exports retention settings to the file plan, records authority mapping and disposition review queue | Purview file plan, disposition review | Policy is set at tenant level, and AI items auto-delete with no information-manager review (§2) |
| Report | Evidence for transparency statements and the NAA Check-up | DTA statement, NAA Check-up | Disclosure is patchy and IM use of AI is low (§5) |

## Gaps this run didn't close
Nothing about these was verified: Objective, OpenText Content Manager or RecordPoint APIs, AFDA or BCS
specifics, AGRkMS field mapping, information-asset registers, DATA Scheme rules, and misinformation tools
beyond citation checkers. **So any connector we name (Graph or Purview API, Objective, OpenText,
RecordPoint) is 💭 until we check the vendor docs.** We're at OpenText today, so ask them about the
Content Manager API.
