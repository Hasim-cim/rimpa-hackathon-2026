# ROT, vendor tools, and novelty check for Record Check (research as at 2026-10-19)

Marker key: a markdown link = I OPENED that page and read the claim there. ⚠️ = search snippet only, page not opened (or opened but failed to load). 💭 = my inference. Fetch tool returns a model-summarised page, so quoted phrases are as returned by the fetch; re-check on screen before putting a quote on a slide.

## 1. What we can safely say on stage (summary)

1. Queensland's own AI-and-records guidance names the exact problem: "a generative AI system may use an outdated document that has been identified as recently opened", retention of ROT "may lead to confusing or incorrect responses", and agencies should "ensure ... that the source of data can be identified" ([Queensland Government, last updated 5 Dec 2024](https://www.forgov.qld.gov.au/information-technology/recordkeeping-and-information-management/recordkeeping/resources-and-tools-for-records-management/artificial-intelligence-and-public-records)). It also says source identification "may not be readily available or accessible in some systems such as Microsoft 365 Copilot".
2. ROT is an established records term (AIIM: usage "dates at least as far back as the early 2000s"). Standard advice: one authoritative copy, dispose of what is no longer needed, but keep anything that is a record. Vendors (Microsoft, Varonis, RecordPoint) all sell "find and clean up ROT before AI". That is the established half of our idea; do not claim it as new.
3. Microsoft Purview already logs which files Copilot accessed for each interaction (`AccessedResources` in the audit log) and can retain Copilot prompts and responses. So "source to AI output link" is not unique. Say the audit log is an activity log you search and export, not a records-management workflow ([audit page](https://learn.microsoft.com/en-us/training/modules/purview-ai-secure-copilot/audit-copilot)).
4. What I could not find in any vendor doc I opened: a feature that, when a source record is superseded, lists every retained AI output that relied on it and queues those outputs for review. Defensible wording: "In the vendor documentation we reviewed we did not find ...". Not "no one does this". Closest thing found is research-stage: an arXiv preprint on dependency-consistent answer caching (see section 3).
5. NAA's AI position (retain final or decision-informing outputs, not every prompt) is snippet-only for me, because the NAA page timed out three times. Reconfirm from the page before quoting. See section 4.

## 2. Q1. ROT: origin, definitions, standard advice

**Origin.** Not found. The AIIM post says only that usage "dates at least as far back as the early 2000s" ([AIIM, Kevin Parker 2016](https://community.aiim.org/blogs/kevin-parker/2016/05/05/defining-information-rot)). The Smashing piece does not say who coined it ([Smashing Magazine 2015](https://www.smashingmagazine.com/2015/06/dealing-with-redundant-out-of-date-trivial-rot-content/)). Do not say who coined it.

**Variants of the acronym.** "Redundant, Outdated, Trivial" is often used for web content; "Redundant, Obsolete, Trivial" is preferred by the AIIM author because "Obsolete" "includes 'outdated' and more" ([AIIM Parker](https://community.aiim.org/blogs/kevin-parker/2016/05/05/defining-information-rot)). Use "Redundant, Obsolete, Trivial" with records people.

**Definitions (opened):**
- AIIM community (Richard Surber, 2017): ROT is "Redundant, Obsolete, and/or Trivial information", covering information kept without a valid business, legal or common practice purpose, physical and electronic, including email ([AIIM Surber](https://community.aiim.org/blogs/richard-surber/2017/09/05/rot-introduction-prevention-tips)). Note: this is a community blog by a member, not an AIIM standard.
- AIIM community (Parker): Redundant = duplicated in multiple places; Trivial = "of very little importance or value", deletable unless it qualifies as a record, corporate knowledge or business insight; Obsolete = "no longer in general use", "discarded", "replaced", or outdated, and it covers information that is superseded, incorrect or incomplete ([AIIM Parker](https://community.aiim.org/blogs/kevin-parker/2016/05/05/defining-information-rot)). The word "superseded" sits inside Obsolete, which helps our feature wording.
- Queensland Government: uses "redundant, obsolete and trivial (ROT) information" without a formal definition ([Queensland](https://www.forgov.qld.gov.au/information-technology/recordkeeping-and-information-management/recordkeeping/resources-and-tools-for-records-management/artificial-intelligence-and-public-records)).
- Smashing Magazine (web content, "redundant, out-of-date and trivial") ([Smashing](https://www.smashingmagazine.com/2015/06/dealing-with-redundant-out-of-date-trivial-rot-content/)).

**Bodies I looked for and did NOT find a formal ROT definition from:** RIMPA (no result at all), ARMA (no glossary entry surfaced; the IGBOK mention is ⚠️ from an oilit.com review snippet), NAA, ISO. Not found, so do not attribute a definition to them. State archives: only Queensland uses the term (opened). NSW AI page did not mention ROT (opened).

**Standard advice (opened):**
- Parker: define a "Single Point Of Truth" for each information type; consolidate duplicates; delete trivial material when no longer needed unless it is a record; check for superseded or incorrect information, not just old; do not keep everything on the assumption storage is cheap ([AIIM Parker](https://community.aiim.org/blogs/kevin-parker/2016/05/05/defining-information-rot)).
- Surber: file plan; one authoritative copy rather than duplicates; follow a retention schedule (e.g. "big bucket") and hold regular destruction days; policy that only the final version is a record and drafts are destroyed once final exists ([AIIM Surber](https://community.aiim.org/blogs/richard-surber/2017/09/05/rot-introduction-prevention-tips)).
- Smashing: require owners to review content on a schedule; stale pages that cannot be removed should be flagged and pulled from navigation and search ([Smashing](https://www.smashingmagazine.com/2015/06/dealing-with-redundant-out-of-date-trivial-rot-content/)).
- Contested: an eDiscovery Today piece reports Brendan Sullivan arguing "redundant" no longer justifies action given modern storage ⚠️ ([snippet](https://ediscoverytoday.com/2025/04/09/rot-should-be-redefined-says-brendan-sullivan-information-governance-trends/)).

💭 Implication for the pitch: for records people the correct reflex is not "delete ROT" but "dispose under an authority, keep what is a record". Our "source health" label (ROT or draft) should say "flag and review", never "delete". A superseded record under a retention schedule is still a record; it just should not be the live source for new AI answers.

## 3. Q2. Vendor tools (what the docs say)

### Microsoft (Copilot readiness, SharePoint Advanced Management, Purview)
- **Finds ROT-like content?** Partly. SAM Content Management Assessment can "Find issues or risks (such as inactive or ownerless sites)" and "Identify potentially overshared content" ([Microsoft Learn: Get ready for Copilot with SAM, updated Aug 2026](https://learn.microsoft.com/sharepoint/get-ready-copilot-sharepoint-advanced-management)). Inactive-site, ownership and attestation policies work at site level, not document level ([Site lifecycle management](https://learn.microsoft.com/sharepoint/site-lifecycle-management)). The page does not use the term ROT. Site-level only: not found at document or record level.
- **Stated purpose:** "Copilot and agents work best for your organization when your content is up to date and well governed", and lifecycle policies "help ensure Copilot and agentic experiences reference current content" ([same page](https://learn.microsoft.com/sharepoint/get-ready-copilot-sharepoint-advanced-management)). Microsoft 365 Archive: "Copilot isn't trained on archived content" (same page).
- **Enforcement:** policies "don't delete SharePoint sites directly"; they notify owners and can set read-only or archive ([Site lifecycle management](https://learn.microsoft.com/sharepoint/site-lifecycle-management)).
- **Purview DSPM for AI (classic):** says AI "can proactively surface content that might be obsolete, over-permissioned, or lacking governance controls". Remediation example: "When content hasn't been accessed for at least 3 years, use Microsoft Purview Data Lifecycle Management to automatically delete it." Activity explorer shows "files referenced, and sensitive files referenced" per AI interaction ([DSPM for AI](https://learn.microsoft.com/en-us/purview/dspm-for-ai)). Note it is labelled "classic"; Microsoft says a newer DSPM replaced it.
- **Links source to AI output?** Yes, at log level. Audit record fields include `AccessedResources` ("Lists the files, messages, or sites Copilot referenced, including details like file name, sensitivity label ID, and access status") and `Messages` (prompts and responses). Microsoft's own example use: "confirm whether a sensitive file was used in a Copilot prompt". To filter by `AccessedResources` you "export the results to a CSV file and filter offline"; default retention 180 days ([Audit Copilot interactions](https://learn.microsoft.com/en-us/training/modules/purview-ai-secure-copilot/audit-copilot)). This is an investigation log, framed around sensitive data, not around supersession.
- **Retains outputs?** Yes. Retention policy location "Microsoft Copilot experiences"; prompts and responses stored in hidden mailbox folders; expired content passes through SubstrateHolds then is deleted after at least a day unless held ([Apply retention policies to Copilot prompts and responses](https://learn.microsoft.com/en-us/training/modules/purview-ai-secure-copilot/retention-copilot)). Retention is by time/policy, not by source status.
- **Recalls outputs when a source changes?** Not found in any of the pages opened above.
- Queensland says source identification "may not be readily available" in Copilot ([Queensland](https://www.forgov.qld.gov.au/information-technology/recordkeeping-and-information-management/recordkeeping/resources-and-tools-for-records-management/artificial-intelligence-and-public-records)). That is a government statement from Dec 2024; Purview's AccessedResources field (above) is a later or separate admin-side log. Be careful: do not say "Copilot cannot show its sources" (it shows citations to users). Say "the audit log lists accessed files, but we found no workflow that acts on them when a source is superseded".

### OpenText (hackathon host)
- Page access: OpenText blog pages, the Content Aviator solution overview PDF and the white paper PDF returned 403 or unreadable binary to me. **I opened no OpenText product documentation.** Everything below is ⚠️.
- ⚠️ Content Aviator: answers include links to cited documents; "Aviator delivers text response along with links to cited documents"; claims "every action the AI content assistant takes ... is traceable, policyaware, and audit ready"; respects access controls ([search results incl. white paper and blog snippets](https://www.opentext.com/en/media/white-paper/secure-ai-content-management-with-opentext-content-aviator-wp-en.pdf), snippet only).
- ⚠️ Documentum CM 26.2 blog has a section heading "Modernized governance and retention management", details not seen.
- ⚠️ OpenText China "smart migration" page says AI classification can identify and remove ROT to speed migration; not Content Aviator, not English, snippet only.
- Intelligent Classification, InfoArchive file analysis: nothing found. Retention behaviour of Aviator: nothing found.
- 💭 Action before the event: ask the OpenText mentors directly whether Aviator keeps a per-answer source list and whether anything flags answers when a cited document is superseded. Do not claim anything about OpenText on stage from this file.

### RecordPoint
- AI Governance page: register AI systems, "maintain a centralized inventory of datasets", track risks and approvals; says natural-language query returns "full citations and direct links to source records". ROT and lineage not mentioned on that page ([RecordPoint AI governance](https://www.recordpoint.com/ai-governance)). Help-centre AI Governance article returned 403 ⚠️ (snippet: early access, Copilot connection via Copilot Studio with a 1:1 setup session).
- ROT: RecordPoint blog describes ROT as "information that is duplicated (redundant), outdated (obsolete), or lacks business value (trivial)", with discovery, metadata, policy-driven actions, audit trails and defensible disposal; recommends "tamper-proof audit trails for all actions"; Copilot not mentioned there ([RecordPoint ROT blog](https://www.recordpoint.com/blog/how-metadata-driven-classification-helps-eliminate-rot)).
- ⚠️ Snippet only: "Intelligence Signaling add-on analyzes file metadata against predefined rules, and document content is not currently analyzed for ROT"; pricing page lists ROT detection as an inventory feature; Australian bank customer case.
- Links source to AI outputs / recalls: not found (AI governance page opened has no lineage).

### Objective
- Only the Public Sector Network marketplace listing was opened: "Objective Information Intelligence" connects to existing systems to "optimise information for modern technologies, including AI solutions such as Microsoft Copilot" and "private RAG implementations". ROT: "The page does not mention" it ([listing, marketing summary](https://publicsectornetwork.com/marketplace/vendors/objective)).
- Objective's own docs/release notes not found. Source to output link, recall: not found.

### M-Files
- Vendor page: Aino automates "metadata tagging, summarizing content"; can "Automatically retire outdated content" under retention policies; duplicates and "version confusion" addressed by single-copy version control; "Every change is logged with full version history". The page does not say AI answers are linked to source documents ([M-Files AI document control page](https://www.m-files.com/sv/lp/ai-powered-document-control/)).
- ⚠️ Snippets: duplicate-content detection is a platform feature; Aino needs the Business Platform Edition and a semantic index ([community](https://community.m-files.com/learning-resources/video-guides/w/user-videos/95/detect-avoid-creating-duplicate-content), [edition page](https://product.m-files.com/?p=752)).
- Source to output link, recall: not found.

### Varonis
- DLM "automatically finds and quarantines redundant, obsolete, and trivial (ROT) data across your entire data estate"; "at least 30% of enterprise data is ROT" (vendor claim, do not repeat as fact); "AI processes and analyzes all the data it can access, including ROT". No mention of tracing a specific AI output to the source records; Copilot appears only in site navigation ([Varonis blog](https://www.varonis.com/blog/introducing-data-lifecycle-management)).
- ⚠️ Separate snippet: Copilot readiness via data risk assessment (permissions, links, labels).
- Source to output link, recall: not found.

### Other (snippets only, not opened)
- ⚠️ DryvIQ, Securiti, Zantaz, Shinydocs, Netwrix, Proventeq, NetApp all market ROT discovery plus AI readiness. None checked for output tracing.

## 4. Q3. Novelty check: "when a source is superseded, find every AI output that relied on it"

**Verdict: partly exists (as components and in research); not found as a product feature in records or content-management tools.**

Evidence:
- **Observability tools capture the raw material.** Langfuse traces record retrieved documents: retrieval is wrapped "to capture what documents were retrieved" and groundedness evaluators verify "claims can be traced back to sources". The article does not say Langfuse can find traces by retrieved document ID or flag answers when a source changes ([Langfuse RAG blog](https://langfuse.com/blog/2025-10-28-rag-observability-and-evals)). Langfuse docs: "You can filter by metadata keys in the Langfuse UI and API" ([Langfuse metadata](https://langfuse.com/docs/observability/features/metadata)). 💭 So an engineer could build a "which traces cited document X" query by storing document IDs as metadata; I did not test this and found no documented built-in feature. This is observability for developers, not a records workflow.
- **Cache-invalidation research does exactly the mechanism.** arXiv 2607.26076 (FinCacheServe, submitted 14 July 2026): answers are "guarded by document versions, evidence fingerprints, tool fingerprints"; it reports "zero observed dependency-stale outputs" on a 2,230-request trace. It is a research prototype evaluated on SEC-derived financial documents; the abstract does not describe a reverse index; the aim is cost-efficient serving (skipping LLM calls), not records review ([arXiv abstract](https://arxiv.org/abs/2607.26076)). Closest prior art found. Cite as "research is moving the same way", not as a competitor product.
- ⚠️ Snippet only: Coalent (PyPI) says `source_changed(id)` marks only cache units whose provenance includes that source id; the PyPI page would not load, so unverified. ⚠️ Practitioner blogs on RAG version drift, `superseded_by` metadata and deterministic chunk keys (Medium, hemju.me, izzy.agency, fuzzypoint.uk): opinions, not products. fuzzypoint.uk fetch failed.
- **Data lineage tools:** ⚠️ snippet-level only. Search found no source showing OpenLineage or Purview lineage tracing document-level retrieval to generated answers; one vendor blog (FutureAGI) argues lineage "stops at the model boundary". That is an argument, not verified fact. I did not open OpenLineage's own docs or Purview lineage docs, so "not found" is weak for these.
- **Microsoft Purview:** the audit log records accessed files per interaction (opened, section 3) and Purview can retain outputs, but I found no documented step that, on supersession of a source file, lists dependent outputs and queues review. Partial building blocks, no workflow.
- **RecordPoint, OpenText, Objective, M-Files:** no such feature found in what I could open (OpenText docs unreachable).

Wording we can defend: "Existing tools can tell you which files an AI used, and some research prototypes invalidate cached answers when documents change. In the documentation we reviewed we did not find a records workflow that recalls retained AI outputs when a source record is superseded." Do not say "first", "only", or "nobody does".

## 5. Q4. Australian guidance

- **Queensland Government (opened, last updated 5 Dec 2024):** generative AI systems "are not recordkeeping systems"; manage "prompts, responses, conversations, and all the processing steps"; "ensure when using a generative AI system response to create content, that the source of data can be identified"; "Information made through generative AI systems is only as accurate as the information the response is sourced from"; AI "may use an outdated document that has been identified as recently opened"; retention of ROT "may lead to confusing or incorrect responses"; "Ongoing removal of obsolete, irrelevant content focuses generative AI systems"; "Use existing systems and processes to relate the AI generated content to the final official document" ([forgov.qld.gov.au](https://www.forgov.qld.gov.au/information-technology/recordkeeping-and-information-management/recordkeeping/resources-and-tools-for-records-management/artificial-intelligence-and-public-records)). Strongest Australian primary source for our pitch. The fetch result mentions an Act reference that varied between page versions in search snippets (2002 vs 2023); verify the live page before quoting any Act name. This is Queensland Government (ForGov) guidance, not necessarily Queensland State Archives authored; check the page footer.
- **NSW (opened):** AI-generated records must be accurate and complete; "AI outputs may contain errors and need verification"; metadata must stay "perpetually linked to the record it relates to"; records should document "the prompts, inputs or algorithms used to create the record"; "It is not enough to leave them in the AI tool where they were created" ([NSW Government recordkeeping](https://www.nsw.gov.au/nsw-government/recordkeeping/create-and-capture/ai-and-recordkeeping)). No ROT or "AI-ready" language found on that page. Useful: "document the inputs" supports our source-link feature.
- **NAA (⚠️ snippets; page timed out 3 times, not opened):** "Information management for records created using artificial intelligence (AI) technologies" ([page](https://www.naa.gov.au/information-management/manage-information-assets/types-information/information-management-records-created-using-artificial-intelligence-ai-technologies)). Snippet claims: AI-generated content is Commonwealth records; agencies "do not need to retain every AI output, prompt, input or chat log"; final or decision-informing outputs are usually kept; prompt/response logs "generally low value"; first published January 2025, updated recently with Finance's AI Delivery and Enablement Division. Do not quote until opened. Whether the NAA page says anything on source records or ROT: unknown.
- **NAA Check-up 2025 (opened IDM article):** "Eighty-seven per cent of Australian Government agencies now use artificial intelligence"; "only 15 per cent apply it to information management activities"; "just 8 per cent use it to create metadata"; 62% consult IM teams when integrating AI ([IDM Magazine](https://idm.net.au/node/15699)). Secondary source reporting the NAA report; the NAA PDF itself was not opened ⚠️.
- **PROV (Victoria):** AI research paper (Oct 2023) and AI Technologies and Recordkeeping Policy exist per search ⚠️; PDF returned 403, not opened. WA SRO advice drawing on PROV ⚠️ (human sign-off for disposal).
- **OVIC:** ⚠️ snippet only: consulted in 2024 on "Artificial Intelligence – Understanding Privacy Obligations"; privacy scope. Nothing found on ROT or AI-ready information.
- **"AI-ready" as an NAA, NSW, PROV or QSA term:** not found.
- **ROT in NAA policy:** not found.

## 6. Table

| Product | Finds ROT? | Links source → AI outputs? | Recalls outputs when source changes? | Evidence |
|---|---|---|---|---|
| Microsoft SharePoint Advanced Management / Copilot readiness | Partly: inactive, ownerless, overshared sites (site level); not document-level ROT | n/a here (see Purview) | Not found | [Get ready for Copilot](https://learn.microsoft.com/sharepoint/get-ready-copilot-sharepoint-advanced-management), [Site lifecycle](https://learn.microsoft.com/sharepoint/site-lifecycle-management) |
| Microsoft Purview (Audit, DSPM for AI, DLM retention) | Partly: obsolete/stale content mentioned; "not accessed for 3 years" delete example | Partly: audit log `AccessedResources` and "files referenced" per interaction; filter by export to CSV | Not found | [Audit](https://learn.microsoft.com/en-us/training/modules/purview-ai-secure-copilot/audit-copilot), [DSPM for AI](https://learn.microsoft.com/en-us/purview/dspm-for-ai), [Retention](https://learn.microsoft.com/en-us/training/modules/purview-ai-secure-copilot/retention-copilot) |
| OpenText Content Aviator / Documentum / InfoArchive | Not found (docs unreachable) | ⚠️ Citations to source documents claimed in snippets | Not found | No OpenText page opened (403/binary) |
| RecordPoint | Yes, per vendor blog (metadata-based; ⚠️ content not analysed per snippet) | Partly: AI governance page claims "citations and direct links to source records" for its query tool | Not found | [AI governance](https://www.recordpoint.com/ai-governance), [ROT blog](https://www.recordpoint.com/blog/how-metadata-driven-classification-helps-eliminate-rot) |
| Objective | Not found (listing does not mention ROT) | Not found | Not found | [Listing](https://publicsectornetwork.com/marketplace/vendors/objective) |
| M-Files (Aino) | Partly: duplicates and retiring outdated content (platform, not Aino) | Not found | Not found | [M-Files page](https://www.m-files.com/sv/lp/ai-powered-document-control/) |
| Varonis | Yes (DLM): ROT and stale data, quarantine | Not found | Not found | [Varonis DLM](https://www.varonis.com/blog/introducing-data-lifecycle-management) |
| Langfuse (RAG observability) | No (not its purpose) | Partly: retrieved documents captured in traces; metadata filterable | Not found (no built-in source-change flag) | [RAG blog](https://langfuse.com/blog/2025-10-28-rag-observability-and-evals), [metadata](https://langfuse.com/docs/observability/features/metadata) |
| FinCacheServe (research prototype, arXiv) | No | Yes in design (version/evidence fingerprints per cached answer) | Yes in design: invalidates stale cached answers; research prototype for serving cost, not records | [arXiv 2607.26076](https://arxiv.org/abs/2607.26076) |
| OpenLineage / Purview lineage / Arize / LangChain tracing | Not checked | ⚠️ Not found in snippets | ⚠️ Not found in snippets | Not opened; weak negative |

## 7. Lines we must NOT say

- "Nobody does this", "we are the first", "no vendor links outputs to sources": false or unverifiable. Purview's audit log lists files Copilot accessed per interaction; OpenText and RecordPoint claim citations; research (arXiv 2607.26076) invalidates answers on document change. Say "in the documentation we reviewed we did not find ...".
- "Copilot can't show where its answers came from": not supported. Queensland says identification "may not be readily available" in some systems including Copilot (Dec 2024); Purview's audit log has `AccessedResources`. Use the Queensland quote, attributed and dated.
- "RIMPA / ARMA / NAA / ISO define ROT as ...": no such definition found. Attribute only to AIIM community posts (blogs by members) or to the Queensland Government's usage.
- "Who coined ROT" or any origin date: not found; only "early 2000s" usage per AIIM.
- "Delete ROT": records advice is dispose under authority and keep records; AIIM says trivial can be deleted "unless it qualifies as a record". Use "flag and review".
- "30-50% of data is ROT" (also "at least 30%" Varonis, "50-60%" TechTarget, "85%" Zantaz/Gartner): vendor or unsourced figures. Do not state as fact.
- "NAA requires X about AI outputs" until the NAA page is opened. Snippet-only: final or decision-informing outputs retained; not every prompt kept. (Consistent with house rule: never "capture everything".)
- "OpenText Content Aviator does/doesn't X": no OpenText docs were readable. Ask the host's mentors.
- "OpenLineage / Purview lineage / Langfuse cannot do this": not checked in primary docs. Say "we did not find it documented".
- "Coalent does provenance-based invalidation" as a fact: PyPI page did not load; snippet only.
- "NAA Check-up shows 87% of agencies use AI" without noting source: figures come from an IDM Magazine article, not the NAA PDF (not opened).
- "Microsoft Purview deletes unused content automatically": the doc gives it as a remediation option an admin configures, with a 3-year example.

## 8. Open items to verify before Monday/Tuesday
1. Open the NAA AI position statement in a browser (our fetch timed out) and copy exact wording and date.
2. Open the PROV AI policy and research paper in a browser (403 to us).
3. Ask OpenText mentors about Aviator source lists and supersession handling; open OpenText Content Aviator docs in a browser.
4. Read Purview's current "Learn about retention for Copilot and AI apps" and the newer (non-classic) DSPM page.
5. Check Queensland page footer for authoring body (QSA vs ForGov) and current Act reference.
