# Research: "intent of the record" metadata, faithfulness checks, sentiment analysis (2026-10-19)

Markers: a markdown link = I opened that page/file and read the claim there. ⚠️ = search snippet only, not opened. 💭 = our inference.
Access notes: ISO 23081 and ISO 15489 are paywalled and the ISO OBP page returned 403, so I have no ISO text, only the ISO committee page and snippets. NAA (naa.gov.au) pages and the AGRkMS PDF timed out three times on fetch, then a later attempt was refused by the tool permission layer. I stopped there and did not work around it. **Every AGRkMS claim below is therefore ⚠️ (search snippet) and must be checked against the AGRkMS v2.2 PDF before stage.**

## 5-line summary: what we can safely say on stage

1. OVIC's own sample IAR template (V2.0, a file I opened) already has a "Purpose (primary purpose of collection)" element, defined as "whether the information asset may be used for other purposes without modification". So "extend the IAR" is literally true for purpose; it sits in the template's Supplementary tab, as optional.
2. OVIC's IAR template also has Related Information Asset + "Type of relationship" (values "Replaces / Replaced By ... Derived From") and "Asset status" (current / semi-current / non-current). That covers our superseded_by and status.
3. ICA Records in Contexts v1.0 defines "Conditions of Use" ("Terms and circumstances affecting the use of a record resource ... after access has been provided") and models Mandate as a kind of Rule. Dublin Core has `audience`, `replaces`/`isReplacedBy` and `accessRights`. None of them define a "must not be relied on for document type X" element. That one is our extension (💭).
4. Research on summary faithfulness supports checking at claim/sentence level against the source with entailment-style (NLI) models: Maynez et al. 2020, SummaC 2022, FActScore 2023, MiniCheck 2024. These check "is this claim supported by the source text". They do not check whether the document is being used for a purpose it was not made for. That is what our purpose / not_for fields are for.
5. Sentiment analysis is defined as analysing "people's opinions, sentiments, evaluations, attitudes, and emotions" (Liu), and documented systems show race/gender bias (Kiritchenko & Mohammad 2018). It measures tone, not support by evidence or use against intent. Say it respectfully: tone is a useful extra signal, but a records control is auditable and rule-based.

---

## Q1. Do records metadata standards already have purpose / function / mandate / use-conditions / rights elements?

### ISO 23081 (records metadata)
- ISO 23081-1:2017 (Edition 2) scope: ["covers the principles that underpin and govern records management metadata"; applies to records and their metadata, processes, systems and organizations. Last reviewed and confirmed 2023](https://committee.iso.org/standard/73172.html).
- ⚠️ A reseller table of contents (iteh.es, not opened) lists 9.3 "Metadata about business rules, policies and mandates" (9.3.1 capture, 9.3.2 post-capture), 9.4 agent metadata, 9.5 business process metadata. Confirm numbering against the standard.
- ⚠️ ISO 23081-2:2021 (second edition, replaces 2010) is the "conceptual and implementational issues" part: a framework for defining metadata elements and decisions for implementing them (snippets from SCC/AFNOR/PECB listings).
- Not found: I could not read the ISO text, so I cannot quote an ISO 23081 element named "purpose". Do not say "ISO 23081 element X" on stage with a name or number. You may say "ISO 23081-1 has a section on metadata about business rules, policies and mandates" only with the ⚠️ caveat.
- 💭 The ICA RiC-CM text says it "has also been influenced by, and reflects, ISO 23081" ([RiC-CM v1.0](https://www.ica.org/app/uploads/2024/01/ric-cm-1.0_0.pdf), section 1.6.4). So RiC's Mandate / Rule / Activity entities are a readable proxy for the ISO 23081 entity idea, but not a substitute for quoting ISO.

### ISO 15489-1:2016
- ⚠️ Snippets (not opened): the standard names four characteristics of authoritative records, "reliability, integrity, usability and authenticity", its scope includes "analysis of business context" and "metadata for records and records systems" (clause 5.2.3 in the contents). Nothing found about purpose / intended-use elements. Not found.

### AGRkMS (NAA), all ⚠️ (NAA pages blocked/timed out)
- ⚠️ AGRkMS v2.2 (June 2015) has numbered properties and a table of which entities (Record, Agent, Business, Mandate, Relationship) each applies to. Source: NAA PDF `AGRkMS-Version-2.2-June-2015_tcm16-93990_1.pdf` (snippet only).
- ⚠️ Property 12 "Rights": described in a snippet as "policies and requirements that govern or restrict non-security related use and access"; sub-properties Rights Statement, Rights Type, Rights Status; applies to the Record entity only. NAA's minimum metadata set page says Rights must be used "if there are non-security related restrictions or policies affecting the access to or use of a record" (snippet paraphrase).
- ⚠️ Rights Type term "Use Permission": "A permission assigned to business information that allows or restricts access by particular agents or groups of agents" (snippet from NAA "AGRkMS and security classification" page).
- ⚠️ Property 11 "Permissions" (types Security, Recordkeeping, Business) and Security Classification (Record, Business, Mandate entities).
- Not found: an AGRkMS property literally called "Use" or "Purpose". The search tool said it could not confirm one. Check the PDF's property list.
- [NSW State Archives mapping page](https://www.nsw.gov.au/mapping-between-as-nzs-5478-2015) (opened): maps NSW's six minimum metadata requirements to RMPRS (AS/NZS 5478:2015, AGRkMS-based) properties. "Metadata recording the business context in which records and information were created or received and used" maps to: Name, Date Range, Jurisdiction, Contact, Position, Language, Coverage, Keyword, Document Form. "Relationships" maps to Identifier, Name, Related Entity, Change History, Keyword. Caveat: the page's table was flattened, so the pairing was inferred by position by the fetch tool.
- [NSW minimum metadata page](https://www.nsw.gov.au/nsw-government/recordkeeping/create-and-capture/using-metadata/requirements-for-metadata) (opened): six requirements: Content, Structure, Business Context ("The circumstances under which the records were created, received, and used"), Relationships, Actions and events, Retrieval information. This is the best quotable "business context" hook. Note the wording came via a summarising fetch tool, so re-read the page for exact text.
- Not found in NSW pages: any "purpose" or "mandate" element.

### ICA Records in Contexts (RiC-CM v1.0, November 2023), opened and read (local text of the PDF)
Source: [RiC-CM v1.0](https://www.ica.org/app/uploads/2024/01/ric-cm-1.0_0.pdf).
- RiC-A09 Conditions of Use: "Terms and circumstances affecting the use of a record resource or an instantiation after access has been provided." Example: "Permission of the copyright owner must be obtained before use".
- RiC-A08 Conditions of Access: "Terms and circumstances affecting the availability of a record resource or an instantiation for consultation."
- RiC-E17 Mandate: "Delegation of responsibility or authority by an agent to another agent to perform an activity." Scope note: "A mandate should not be confused with the one or more documentary sources that serve as evidence of its identity. A documentary source is a record."
- RiC-E16 Rule: "Conditions that govern the existence, responsibility, or authority of an agent; or the performance of an activity by an agent; or that contribute to the distinct characteristics of things created or managed by an agent."
- RiC-E15 Activity: "The doing of something for an agent designed purpose." Scope note: "The end is the purpose of the activity, or why the activity is performed."
- RiC-A17 Documentary Form Type: "Categorization of a record set, record, or record part with respect to its extrinsic and intrinsic elements that together communicate its content, administrative and documentary context, and authority."
- Not found: a "Function" entity in RiC-CM v1.0 (I found Activity and Activity Type). Do not say RiC has a Function entity.
- Not found: an attribute meaning "intended use" or "must not be used for". Conditions of Use is the nearest and is about legal/conservation terms.

### Dublin Core (DCMI Terms), opened: [DCMI Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)
- `audience`: "A class of agents for whom the resource is intended or useful."
- `accessRights`: "Information about who access the resource or an indication of its security status."
- `rights`: "Information about rights held in and over the resource."
- `license`: "A legal document giving official permission to do something with the resource."
- `provenance`: "A statement of any changes in ownership and custody of the resource since its creation" "that are significant for its authenticity, integrity, and interpretation."
- `replaces`: "A related resource that is supplanted, displaced, or superseded by the described resource." `isReplacedBy`: "A related resource that supplants, displaces, or supersedes the described resource."
- `source`: "A related resource from which the described resource is derived."
- Not found: a DCMI term for purpose of creation or prohibited uses. `audience` is the nearest to "intended use".

**Q1 conclusion.** "Purpose" and "superseded" have a natural home. A "not to be relied on for these document types" element was not found in any standard I could read. Say it is "an extension of use-conditions, not a new scheme".

---

## Q2. OVIC Information Asset Register (IAR) Sample Template V2.0

Sources: [OVIC resource page](https://ovic.vic.gov.au/resource/sample-information-asset-register-iar-template/) (opened: "designed to help organisations develop an Information Asset Register or enhance their existing one"; V2.0; the page itself lists no tabs or fields; upload path suggests 2019/11, not stated on the page). The workbook itself is opened locally: `/Users/hasimrahman/repos/rimpa-hackathon-2026/reference/Sample-IAR-Template-V2.0.xlsx`. [Practitioner Guide V2.0](https://ovic.vic.gov.au/wp-content/uploads/2021/05/Practitioner-Guide-Identifying-and-Managing-Information-Assets-V2.0.pdf) (opened as PDF text, "Version 2.0 November 2019", first published June 2016).

Workbook tabs: How to use / VPDSF Requirements / Core (inc. VPDSF reqs) / Supplementary / Overview - Legal & Regulatory. The instructions say the template "provides 3 options" (tabs) and that organisations should "cross reference the fields ... and consider updating or enhancing your existing register" (instruction text, partly truncated in my read).

**VPDSF Requirements tab fields:** Asset name; Asset description; Personal information?; National interest / national security information (NSI)?; Location; Format; Creation date or acquired date; Last updated; Originator; Owner; Custodian; BIL - Confidentiality; Protective marking; BIL - Integrity; BIL - Availability; Suitable for unlimited public release?; Approver/authorisor; Public release date.

**Core tab adds:** Asset status ("Current, semi-current or non-current"); Tags/keywords; Temporal range/coverage; Data source URL; Program URL; Unique ID; Update frequency; Attribution statement; Copyright statement; Licensing; Disclaimer; Business classification ("Business classifications may be functional, process based, subject based or organisation based"; "Assists in identifying the scope, types, use and functions of an information asset"); Type/Category; Record disposal category (disposal category, disposal class); Geographic coverage (granularity, ASGS, bounding box, vertical coverage).

**Supplementary tab (optional elements the organisation can add), with exact definitions:**
- IAR entry review date: "The date that this entry on the IAR was last reviewed or updated"
- **Purpose (primary purpose of collection)**: "A description of the purpose for which the information asset was collected, and whether the information asset may be used for other purposes without modification." Note text: "This helps organisations determine the original intent or purpose for generation or collection of that information asset." It ties this to the Privacy and Data Protection Act 2014 (Vic) on reuse of personal information for a secondary purpose, and says it documents "any mandates for collecting the information".
- Related Information Asset: "Link to related information assets"; "Organisations to define whether this information asset is an input or an output."
- Type of relationship: "Typical values would be: Replaces / Replaced By, New Version / Old Version, Derived From / Derivation, Related information assets. Other values are allowed."
- Disposal requirements; Access ("Access restrictions to the information asset"); Collected to meet mandatory legal or regulatory obligations?; Collection method; Collection validation; Off-line access; Supports Business Process ("Business process the information relates to"); Source ICT System ("Name of the business ICT system / application associated with the information asset").
- **Data Quality / Trust Statement**: "A statement about the quality of the data and purposes for which it can be used." (close to our not_for / fit-for-purpose idea).

**Practitioner Guide:** defines an information asset as "a body of information, defined and practically managed so it can be understood, shared, protected and used to its full potential" and says assets "have a recognisable and manageable value, risk, content and lifecycle" (section 4.1). Section 11.2 says an IAR supports "governance arrangements (identifying at a high-level what information assets exist, the purpose of these assets, and the roles and responsibilities surrounding the access, use and management of the information)". There is no "business value" field as such; the template uses Business Impact Levels (confidentiality, integrity, availability) for "security value".

Gaps and cautions for the pitch:
- The IAR describes information assets (bodies of information), not individual records. 💭 Record Check applies the same fields per record or per asset; say so honestly.
- Purpose is in the Supplementary tab (optional), not the VPDSF-required fields.
- The OVIC resource page notes the PSPF "OFFICIAL: Sensitive" change (search snippet, ⚠️), so the protective-marking wording in V2.0 is dated.
- Owner, custodian and originator are there; "authoritative" status is not a field (💭 ours; closest is Asset status + Unique ID + Last updated).

---

## Q3. Faithfulness of LLM outputs to a source: what works

All opened via ACL Anthology / arXiv abstract pages unless marked.
- Maynez et al., ACL 2020, [On Faithfulness and Factuality in Abstractive Summarization](https://aclanthology.org/2020.acl-main.173/): models "are highly prone to hallucinate content that is unfaithful to the input document"; "Our human annotators found substantial amounts of hallucinated content in all model generated summaries." They also report that textual entailment measures correlate better with faithfulness than standard metrics such as ROUGE (paraphrase of the abstract via fetch tool).
- Laban et al., TACL 2022, [SummaC](https://aclanthology.org/2022.tacl-1.10/): opens "In the summarization domain, a key requirement for summaries is to be factually consistent with the input document." Finding: NLI models were trained at sentence level, so splitting the document into sentences and aggregating pair scores (SummaC-Conv) works better; balanced accuracy 74.4%, about 5 points above prior work (as reported on the page; I did not verify the benchmark).
- Min et al., EMNLP 2023, [FActScore](https://arxiv.org/abs/2305.14251): "breaks a generation into a series of atomic facts" and scores the share supported by a reliable knowledge source. Closest published pattern to our "claim by claim against authoritative records". Human evaluation found ChatGPT biographies scored only 58%. Caveat: the knowledge source there is Wikipedia, not an organisation's records.
- Tang, Laban, Durrett, EMNLP 2024, [MiniCheck](https://arxiv.org/abs/2404.10774): small models that check each fact in a claim against grounding documents, claimed "GPT-4-level performance but for 400x lower cost" (authors' claim, unverified by me).
- Laban et al., [LLMs as Factual Reasoners / SummEdits](https://arxiv.org/abs/2305.14540): "Most LLMs struggle on SummEdits, with performance close to random chance"; GPT-4 is about 8 points under estimated human performance (as reported via fetch tool). Use this as a caution: LLM-only judging of consistency is not reliable, which supports claim-level checks plus human review.
- Decontextualization: Choi et al., TACL 2021, [Decontextualization: Making Sentences Stand-Alone](https://aclanthology.org/2021.tacl-1.27/): "Taking excerpts of text can be problematic, as key pieces may not be explicit in a local window." The task is rewriting a sentence so it can be understood on its own without changing its meaning. This is research on the quoting-out-of-context problem, but it is about sentence meaning, not about the purpose of a record.
- 💭 What this adds up to: entailment/NLI and atomic-fact checking test "does the source text support this claim". They cannot tell you a discussion paper was never meant to support a decision. A purpose / not_for field makes that a deterministic rule, so the check is explainable and auditable.
- Not found: a benchmark that tests "use of a document against its original purpose". I did not find one; say "we did not find one", not "none exists".

---

## Q4. Is sentiment analysis suitable for detecting bias or misrepresentation?

- Definition, opened: [Bing Liu, Sentiment Analysis and Opinion Mining (2012)](https://www.cs.uic.edu/~liub/FBS/SentimentAnalysis-and-OpinionMining.html): "the field of study that analyzes people's opinions, sentiments, evaluations, attitudes, and emotions from written language."
- Bias in the tools, opened: [Kiritchenko & Mohammad 2018, Examining Gender and Race Bias in Two Hundred Sentiment Analysis Systems](https://arxiv.org/abs/1805.04508): built the Equity Evaluation Corpus ("8,640 English sentences"); tested 219 systems from SemEval-2018 Task 1; several "consistently provide slightly higher sentiment intensity predictions for one race or one gender."
- Opened: [Poria et al., Beneath the Tip of the Iceberg (IEEE TAC)](https://arxiv.org/abs/2005.00357): the field is saturated in polarity classification and there are "under-explored, yet key aspects ... necessary to attain true sentiment understanding." The abstract says nothing about records or misrepresentation.
- ⚠️ Pang & Lee 2008 (Foundations and Trends in IR) is the standard survey; snippets (not opened) and a lecture deck list domain dependence, negation, sarcasm as known challenges. Do not quote these without opening.
- 💭 Reasoning for the pitch (our inference, not a source claim): sentiment measures the tone of a text. A faithful summary of a bad-news report is negative; an unfaithful summary of it can be neutral or positive. Tone does not tell you whether a claim is supported, whether the source was current, or whether the source was meant for this use. Not found: a source saying sentiment analysis detects misrepresentation of a source, so do not claim one.
- Respectful framing: "Sentiment is a useful signal for tone. For an information manager we wanted a control they can inspect and sign off, tied to records they already govern."

---

## Q5. Archival concepts for "original intent"

- Archival bond, opened: [InterPARES terminology](https://www.interpares.org/ip2/ip2_terminology_db/archival-bond/109): "The network of relationships that each record has with the records belonging in the same records aggregation." Source cited: Duranti, Eastwood & MacNeil, *Preservation of the Integrity of Electronic Records* (Kluwer, 2002), p. 109.
- Provenance and context, opened: [RiC-CM v1.0](https://www.ica.org/app/uploads/2024/01/ric-cm-1.0_0.pdf) section 1.5.1 describes the traditional principle: "Respect des fonds stipulates that the records created, accumulated, and used by a person or group in the course of life and work are to be kept together and not intermixed with records from other sources. Respect for original order stipulates that the interrelations among the records in a fonds established in the context of accumulation and use is to be preserved." Section 1.5.3 "Expanding the Understanding of Provenance" says RiC-CM "recognizes that provenance is much more complex".
- RiC record definition (RiC-E04): "Discrete information content formed and inscribed, at least once, by any method on any carrier in any persistent, recoverable form by an agent in the course of life or work activity."
- Dublin Core `provenance` (opened above) says custody changes matter "for its authenticity, integrity, and interpretation".
- Not found: the phrase "original intent" as a defined archival term in these sources. 💭 The closest we can honestly say is "a record is created in the course of an activity for a purpose (RiC Activity: 'the end is the purpose of the activity'), and its context is part of its meaning".
- ⚠️ A snippet credited the archival bond concept to Giorgio Cencetti (1937) via Wikipedia; unverified, do not say on stage.

---

## Mapping table

| Our field | Standard element it maps to | Source |
|---|---|---|
| purpose | OVIC IAR Supplementary element "Purpose (primary purpose of collection)", exact match in meaning ("original intent or purpose"). Related: RiC Activity ("the end is the purpose of the activity"); DC `audience` (nearest, weaker) | [OVIC template xlsx](file:///Users/hasimrahman/repos/rimpa-hackathon-2026/reference/Sample-IAR-Template-V2.0.xlsx), [RiC-CM v1.0](https://www.ica.org/app/uploads/2024/01/ric-cm-1.0_0.pdf), [DCMI](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) |
| not_for (document types it must not be relied on for) | No exact element found. Nearest: OVIC "Data Quality / Trust Statement" ("purposes for which it can be used"); the "whether ... may be used for other purposes without modification" clause of OVIC Purpose; RiC-A09 Conditions of Use; AGRkMS Rights (non-security use restrictions) ⚠️. Say: "extends use-conditions" (💭) | OVIC xlsx; [RiC-CM v1.0](https://www.ica.org/app/uploads/2024/01/ric-cm-1.0_0.pdf); AGRkMS ⚠️ |
| status | OVIC Core "Asset status" ("Current, semi-current or non-current") | OVIC xlsx |
| superseded_by | OVIC "Related Information Asset" + "Type of relationship" (value "Replaces / Replaced By"); DC `isReplacedBy` | OVIC xlsx; [DCMI](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) |
| authoritative | No IAR field. Concept: ISO 15489-1 "authoritative records" (reliability, integrity, usability, authenticity) ⚠️. In our design it is derived from status + owner + system 💭 | ⚠️ snippets for ISO 15489-1 |
| system | OVIC Supplementary "Source ICT System" ("Name of the business ICT system / application associated with the information asset"); Core "Location" | OVIC xlsx |
| (supporting) owner / custodian / originator | OVIC VPDSF fields of the same names; ISO 23081 agent metadata (9.4) ⚠️; RiC Agent | OVIC xlsx; ⚠️ |
| (supporting) business function / mandate | OVIC Core "Business classification" and Supplementary "Supports Business Process", "Collected to meet mandatory legal or regulatory obligations?"; RiC Mandate (RiC-E17); ISO 23081-1 9.3 ⚠️; NSW "Business Context" requirement | OVIC xlsx; RiC-CM; [NSW](https://www.nsw.gov.au/nsw-government/recordkeeping/create-and-capture/using-metadata/requirements-for-metadata) |

---

## Lines we must NOT say

- "ISO 23081 has a purpose element" or any ISO 23081/15489 element number or quote. We have no ISO text. Say only that ISO 23081-1 covers metadata about "business rules, policies and mandates" with the ⚠️ caveat, or leave ISO out.
- "AGRkMS has a Use / Purpose element." Not found. Any AGRkMS quote needs the PDF opened first.
- "The OVIC template requires purpose." It is optional (Supplementary tab). Also do not say it is a regulator rule for our not_for field.
- "OVIC's IAR has a not-for or prohibited-use field." It does not; the Purpose definition only asks "whether the information asset may be used for other purposes without modification".
- "A standard defines not_for / forbidden document types." Not found; it is our extension.
- "Sentiment analysis is biased / doesn't work." Say it measures tone and that bias has been documented in specific systems (219 SemEval systems in one study).
- "No research exists on checking use against intent." Say we did not find a benchmark for it.
- "NLI / faithfulness checkers solve this." SummEdits shows LLM judges near chance on hard cases; MiniCheck's 400x claim is the authors' own.
- "RiC has a Function entity" or "'original intent' is an archival term." Neither found.
- "Archival bond = intent." The InterPARES definition is about relationships between records in an aggregation.
- Never "true / false / fake"; say "supported by authoritative records", "not found", "possibly fabricated" (CLAUDE.md rule 7).
