# Record Check: confident AI output, RAG reliability, stale sources, incidents, volume

Researched 2026-10-19. Markers: a markdown link = I opened that page and read the claim there. ⚠️ = search snippet only, not opened. 💭 = our inference. Where a page was opened through WebFetch it returns a model-written summary of the page, so quoted phrases below are those the tool returned from the page; re-check any phrase before it goes on a slide.

Blocked or unopened primary sources: the Moffatt decision on the BC Civil Resolution Tribunal site and on CanLII both returned HTTP 403. **Moffatt facts below therefore come from secondary pages I opened, not from the decision itself.** The HBR workslop article was opened but its excerpt did not carry the statistics (the BetterUp page did).

## Summary: what we can safely say on stage

1. A tribunal held Air Canada responsible for what its own chatbot told a customer, and ordered C$812.02 in total (Moffatt v. Air Canada, 2024 BCCRT 149, 14 Feb 2024). The cause was the bot contradicting another page of the airline's own site, not a documented outdated-content problem.
2. Even purpose-built, retrieval-based legal AI tools hallucinated between 17% and 33% of the time in a preregistered Stanford study ("over 1 in 6" queries), and vendors disputed the methodology.
3. In a 404-person Microsoft Research experiment, people agreed with the AI's answer 80.9% of the time when it spoke without hedging; people given the AI's wrong answers got 33.0% right, versus 64.7% with no AI at all.
4. Research on retrieval with out-of-date or contradictory documents consistently shows accuracy falling (HoH, VersionRAG, a TGA/PubMed study). Naive RAG scored 58% on version-sensitive questions in one benchmark.
5. Volume and cost: Workday (Jan 2026) found about 37% of time saved by AI is lost to rework; KPMG/Melbourne (48,000+ people, 47 countries) found 66% rely on AI output without evaluating accuracy. Both are surveys, so say "reported".

---

## Q1. Over-trust of confident AI output

**1a. Microsoft Research, "I'm Not Sure, But..." (Kim, Liao, Vorvoreanu, Ballard, Vaughan; FAccT 2024).** Pre-registered experiment, N=404, medical questions answered with or without a fictional LLM-powered search engine. Numbers are model-estimated means from the paper ([ar5iv full text](https://ar5iv.labs.arxiv.org/html/2405.00623v1), [arXiv abstract page](https://arxiv.org/abs/2405.00623)):
- Agreement with the AI: 80.9% (no uncertainty expressed), 74.8% (first-person "I'm not sure, but...", p<0.05), 77.6% (general phrasing, not significant), 58.4% (no AI).
- Accuracy when the AI was wrong: 33.0% (no hedging), 47.8% (first-person hedge), 40.1% (general hedge), 64.7% (no AI).
- Accuracy overall: 63.9% (no hedging) vs 72.8% (first-person hedge) vs 74.2% (no AI).
- Reading: people with the AI and no hedging did worse on the AI's wrong answers than people with no AI. The hedge cut overreliance "but not eliminated" it. 💭 This supports "confidence is not evidence", and a flag next to a claim plays the same role as a hedge.
- Caveat: medical questions, fictional search engine, lab experiment, not records work.

**1b. Steyvers et al., "What Large Language Models Know and What People Think They Know" (Nature Machine Intelligence 2025; arXiv v2).** Opened the [arXiv abstract](https://arxiv.org/abs/2401.13835): "users tend to overestimate the accuracy of LLM responses when provided with default explanations"; "longer explanations increased user confidence, even when the extra length did not improve answer accuracy"; rewriting explanations to reflect the model's internal confidence narrowed the gaps. No numbers are in the abstract and I did not open the full paper, so cite the direction, not figures. ⚠️ A search snippet said the journal version is in Nature Machine Intelligence; I did not open the journal page.

**1c. Microsoft Research literature review (Passi and Vorvoreanu, MSR-TR-2022-12, June 2022).** ~60 papers. Defines overreliance: "Overreliance on AI occurs when users start accepting incorrect AI outputs." Notes human oversight can make users "the last line of defense against AI failures" ([Microsoft Research page](https://www.microsoft.com/en-us/research/?p=854967)). I did not open the report PDF, so no findings from inside it. ⚠️ A search snippet also lists a 2025 Microsoft report (MSR-TR-2025-4) saying overreliance mitigations can backfire; not opened.

**1d. Stanford legal study as over-trust evidence.** The authors note that Lexis+ AI cited a real case, but the answer relied on that case's description of Planned Parenthood v. Casey, which has been overruled. Their words: "its citation serves only to mislead the user about the reliability of its answer" ([arXiv PDF](https://arxiv.org/pdf/2405.20362)). 💭 A real link to a real document does not mean the claim is supported, which is the Record Check premise.

**1e. ClashEval (Wu, Wu, Zou; Stanford, 2024), a model-side version of over-trust.** Six LLMs including GPT-4o adopted incorrect retrieved content, "overriding their own correct prior knowledge over 60% of the time" ([arXiv](https://arxiv.org/abs/2404.10198)). Models were less likely to accept content that was more blatantly wrong, and more likely to adopt it when less confident in their own answer. 💭 Subtly wrong content is the dangerous case, and it is what a superseded version looks like.

Not found: a study showing LLM fluency alone (as opposed to uncertainty wording or explanation length) raises reliance with a clean effect size that I opened. Do not claim "fluent language causes over-trust" as a single study result.

## Q2. How reliable is RAG / AI search in practice

**Stanford RegLab/HAI, "Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools" (Magesh, Surani, Dahl, Suzgun, Manning, Ho).**
- Preprint 30 May 2024; HAI news page dated 23 May 2024, updated 30 May 2024 to add Westlaw ([HAI page](https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries), [arXiv abs](https://arxiv.org/abs/2405.20362)). The PDF I opened is a later version that mentions 2025 and the Westlaw tool ([arXiv PDF](https://arxiv.org/pdf/2405.20362)). It appears in the Journal of Empirical Legal Studies 2025 per a search result header ⚠️.
- Headline from the paper: Lexis+ AI, Westlaw AI-Assisted Research and Ask Practical Law AI "each hallucinate between 17% and 33% of the time." 202 queries. Hallucination counts "incorrect or misgrounded" answers, including real sources that are irrelevant or contradict the claim.
- "Over 1 in 6 of our queries caused Lexis+ AI and Ask Practical Law AI to respond with misleading or false information. And Westlaw hallucinated substantially more—one-third of its responses contained a hallucination." Accurate (correct and grounded) answers: Lexis+ AI 65%, Westlaw 41%, Practical Law AI 19% (20% in a re-validated version, per the paper's footnote).
- GPT-4 (no retrieval) did worse than the tools. The HAI page cites the group's earlier study for general chatbots "between 58% and 82%" on legal queries.
- Relevant to us: the paper lists "inapplicable authority" (wrong jurisdiction, or "has been overruled") as a distinct error type, and says Westlaw sometimes stated a rule from an overruled case without citing it, which "impedes verification of the claims most likely to be false."
- Number discrepancy: the HAI page text returned "more than 34%" for Westlaw; the paper says 33% (and the abstract range tops out at 33%). Use the paper: "17% to 33%".
- **Disputed.** [LawNext](https://www.lawnext.com/2024/05/stanford-will-augment-its-study-finding-that-ai-legal-research-tools-hallucinate-in-17-of-queries-as-some-raise-questions-about-the-results.html): Thomson Reuters said the first version tested the wrong product (Ask Practical Law AI, not AI-Assisted Research); the authors said TR had denied access, which TR later provided. LexisNexis's Jeffrey Pfeifer said the authors never contacted them, the company's own analysis found "a much lower hallucination rate", the study used a broader definition, and tests predated Lexis+ AI RAG 2.0 (the paper's footnote also says its results do not speak to the second-generation product). So say "in a Stanford study, which the vendors disputed", and "legal research, not records".

**Other RAG evidence.**
- Australian: ASIC's AWS proof of concept (Llama2-70B summarising submissions to a parliamentary inquiry). Reviewers who did not know AI was involved scored human summaries "61 (81 per cent)" and AI "35 (47 per cent)" out of 75; AI summaries had wrong information, lack of nuance, misplaced context. The report cautions it tested "one particular AI model (Llama2-70B) at one point in time" and one use case; AWS said it was not used for regulatory work ([Region Canberra, 5 Sept 2024](https://region.com.au/government-test-shows-humans-far-outperforming-ai-because-they-understand-the-task-better/805612/)). This is summarisation, not RAG, and an older model.
- ⚠️ Digital Transformation Agency Copilot evaluation: a search snippet says "lack of contextual knowledge required time spent on output verification and editing which negated some of the efficiency savings." The digital.gov.au pages timed out, so not opened.
- Not found: a primary, independently verified benchmark of enterprise-search answer accuracy on an organisation's own documents. Search results offered blog-level figures (78% vs 95% factual consistency on an internal corpus, a "Stanford AI Lab 40%") with no primary source I could open. Do not use them.

## Q3. Stale, superseded and conflicting sources in RAG

All four items below were opened at the arXiv abstract page.

- **HoH benchmark (Ouyang et al., arXiv 2503.04800, Mar 2025).** "the first benchmark specifically designed to evaluate the impact of outdated information on RAG." Findings: outdated information lowers answer accuracy "because it pulls models away from correct content"; models can be steered toward potentially harmful outputs "even when up-to-date information is also available"; current RAG struggles in both retrieval and generation with outdated information ([arXiv](https://arxiv.org/abs/2503.04800)). No percentages were on the abstract page.
- **VersionRAG (Huwiler, Stockinger, Fürst; arXiv 2510.08109, 9 Oct 2025).** VersionQA: 100 questions over 34 versioned technical documents. Accuracy: naive RAG 58%, GraphRAG 64%, VersionRAG 90%. Implicit change detection: baselines 0-10%, VersionRAG 60% ([arXiv](https://arxiv.org/abs/2510.08109)). Caveat: small benchmark; the authors' own method is the winner.
- **"Contradictions in Context: Challenges for RAG in Healthcare" (Javadi et al., arXiv 2511.06668; v1 Nov 2025, v2 Apr 2026).** Five LLMs; questions built from Australian TGA consumer medicine documents; PubMed abstracts from different years retrieved. "contradictions between highly similar abstracts do, in fact, degrade performance"; "retrieval similarity alone is insufficient for reliable medical RAG"; they recommend contradiction-aware filtering ([arXiv](https://arxiv.org/abs/2511.06668)). Australian source material, useful for the room.
- **Knowledge Conflicts for LLMs: A Survey (Xu et al., EMNLP 2024).** Three types: "context-memory, inter-context, and intra-memory conflict", which can seriously affect reliability, especially where "incorrect or unreliable information is common" ([arXiv abs](https://arxiv.org/abs/2403.08319)). Inter-context conflict (two retrieved documents disagree) is the record-versions case. ⚠️ EMNLP 2024 pages 8541-8565 comes from a search snippet.
- **Adaptive Chameleon or Stubborn Sloth (Xie et al., ICLR 2024 Spotlight).** LLMs readily accept external evidence that contradicts their memory if it is "coherent and convincing", and show "a strong tendency to favor" evidence consistent with their own memory when it is mixed with conflicting evidence ([arXiv](https://arxiv.org/abs/2305.13300)). 💭 A confident, well-written draft can win over a terse approved version.
- ⚠️ Search-snippet only, unopened: FiscalQA Pro (French tax code, versioned articles; reported via a news summary, arXiv ID unconfirmed). Do not cite.

💭 None of these studies is about records-management systems. The honest framing is: documented in retrieval research, plausible in a records repository, and what Record Check tests for.

## Q4. Incidents

**Moffatt v. Air Canada, 2024 BCCRT 149.**
- Tribunal: BC Civil Resolution Tribunal. Decision date 14 February 2024 ([Daily Hive](https://dailyhive.com/canada/air-canada-chatbot-decision), [Business Law Today](https://businesslawtoday.org/?p=24320)). Tribunal Member Christopher Rivers ⚠️ (snippet; no opened page named him).
- Amount: damages $650.88 + CRT fees $125 + pre-judgment interest $36.14 = **$812.02** ([Daily Hive](https://dailyhive.com/canada/air-canada-chatbot-decision)). Currency is Canadian dollars (the page gave no symbol or currency; the tribunal is Canadian, so CAD is 💭). The claimant originally sought about $880 ⚠️ (snippet).
- What the bot said: the chatbot suggested he could request the reduced bereavement fare after travel, "kindly do so within 90 days of the date your ticket was issued" ([Hull & Hull](https://hullandhull.com/2024/02/booking-travel-usingbereavement-air-fare/)); another page on the site said retroactive requests were not allowed ([McCarthy Tétrault](https://www.mccarthy.ca/en/insights/blogs/techlex/moffatt-v-air-canada-misrepresentation-ai-chatbot)).
- Air Canada's defence, per the same page: the chatbot was a "separate entity" and correct information was elsewhere on its website. Tribunal findings as quoted: "I find Air Canada did not take reasonable care to ensure its chatbot was accurate"; "It should be obvious to Air Canada that it is responsible for all the information on its website" ([McCarthy Tétrault](https://www.mccarthy.ca/en/insights/blogs/techlex/moffatt-v-air-canada-misrepresentation-ai-chatbot), [Daily Hive](https://dailyhive.com/canada/air-canada-chatbot-decision)). Business Law Today quotes "A consumer cannot be expected to double-check information it finds on one part of the website with another" ([link](https://businesslawtoday.org/?p=24320)). Negligent misrepresentation found ([ehlaw.ca](https://ehlaw.ca/?p=22062)).
- Cause: the opened sources describe a chatbot answer that conflicted with the airline's own policy page. They do not say the bot used outdated content, and I found no source stating the technical cause (hallucination vs retrieval). So it is a "conflicting with the authoritative page" incident, not a proven "superseded document" one. 💭 It still shows that organisations answer for what the bot says even when the correct record exists.
- It is a tribunal decision, not a court judgment. I could not check later appeal history.

**NYC MyCity chatbot.**
- Announced October 2023 by Mayor Eric Adams; The Markup published 29 March 2024. Built on Microsoft's platform; Microsoft declined to comment then ([The Markup, 29 Mar 2024](https://themarkup.org/news/2024/03/29/nycs-ai-chatbot-tells-businesses-to-break-the-law)).
- Wrong answers reported there: landlords need not accept Section 8 / rental assistance tenants (the bot said yes to one reporter and no to all ten Markup staff who asked); locking out a tenant is legal; "there are no restrictions on the amount of rent that you can charge a residential tenant"; "Yes, you can make your restaurant cash-free" (a 2020 city law requires accepting cash); "Yes, you can take a cut of your worker's tips". Found by The Markup, with more housing errors found by Rosalind Black (Legal Services NYC). The city said it was a pilot that "has already provided thousands of people with timely, accurate answers".
- Later: in January 2026 Mayor Mamdani called it "functionally unusable" and said it cost "around half a million dollars"; the city took it down on 4 Feb 2026, saying its "beta test has ended" ([The Markup, 30 Jan 2026 (updated 4 Feb)](https://themarkup.org/artificial-intelligence/2026/01/30/mamdani-to-kill-the-nyc-ai-chatbot-we-caught-telling-businesses-to-break-the-law)). The cost is Mamdani's figure; the article says the real cost is unclear and building it reportedly cost nearly $600,000.
- Cause: the 2026 article says it does not say whether the errors came from outdated information or hallucination, and the 2024 article gave no cause. So: **do not say it was outdated content.** It is an example of wrong policy advice from a government's own chatbot. Cause unstated.

**Australian incident, documented but not the same pattern.** Deloitte's report to the Department of Employment and Workplace Relations (fee $440,000, on an IT system DEWR uses to automate welfare penalties) contained non-existent academic references and a fabricated quote from a Federal Court judgment. DEWR found the errors only through media reporting; secretary Natalie James: "We should not be receiving work that has glaring errors in footnotes and sources." Deloitte repaid "almost $98,000, or $97,587 according to Senate Estimates, about 20 per cent of its fee" ([Region Canberra](https://region.com.au/government-urged-to-get-deloittes-total-fee-returned-for-delivering-a-botched-ai-report/911846/)). That page does not mention the tool used. ⚠️ Search snippets say the revised report disclosed Azure OpenAI GPT-4o; not opened, so do not state it. This is AI-assisted consulting, fabricated citations, not an assistant misquoting an organisation's own content. The subject system was the welfare compliance system; do not link it to Robodebt (not an AI system).

Not found: a well-documented Australian case of an AI assistant giving outdated or wrong policy from an organisation's own records.

## Q5. Volume and verification effort

- **Workday, "Beyond Productivity: Measuring the Real Value of AI" (with Hanover Research; released 14 Jan 2026; 3,200 employees and leaders).** "37%" of time saved through AI is lost to rework such as correcting errors and verifying outputs; only "14% of workers consistently achieve net-positive productivity outcomes once rework is accounted for"; 85% say AI saves them one to seven hours a week ([ERP Today](https://erp.today/workday-research-finds-ai-productivity-gains-are-lost-to-rework/)). Vendor-sponsored survey of self-reports; fieldwork dates and margin of error not on that page (⚠️ a snippet says fieldwork was November 2025).
- **BetterUp Labs and Stanford Social Media Lab "workslop" study.** 1,150 full-time US desk workers surveyed September 2025. 40% received workslop (polished-looking AI work that shifts the work to colleagues) in the prior month; about 2 hours on average to resolve each; $186 per employee per month ([BetterUp](https://www.betterup.com/workslop)). US-only, self-reported. I read the numbers on BetterUp's page, not on HBR.
- **KPMG and University of Melbourne, global trust study 2025.** Over 48,000 respondents, 47 countries; 66% "rely on AI output without evaluating accuracy"; 56% "making mistakes in their work due to AI" ([KPMG](https://kpmg.com/ee/en/insights/2025/05/Trust-attitudes-and-use-of-artificial-intelligence-A-global-study-2025.html)). The page gave no Australia figure (it links an Australia snapshot PDF I did not open). The University of Melbourne led the research ⚠️.
- Not found: a primary statistic on growth of AI-generated content volume inside organisations (documents per year or share of records created with AI). I did not find one I could open. Do not state one.

---

## Best three facts for the pitch

1. A BC tribunal ordered Air Canada to pay C$812.02 after its chatbot gave wrong bereavement-fare advice that conflicted with its own policy page, holding the airline responsible for "all the information on its website" ([Daily Hive](https://dailyhive.com/canada/air-canada-chatbot-decision)).
2. In Stanford's preregistered study of legal research AI built on retrieval, the tools hallucinated between 17% and 33% of the time, including answers that cited real but overruled cases ([Stanford paper](https://arxiv.org/pdf/2405.20362); vendors disputed the method, say so).
3. In a 404-person Microsoft Research experiment, participants shown an AI answer without hedging agreed with it 80.9% of the time and got only 33.0% right when the AI was wrong, versus 64.7% with no AI ([Kim et al. 2024](https://ar5iv.labs.arxiv.org/html/2405.00623v1)).

Backup: Workday (37% of AI time savings lost to rework) and the HoH finding that outdated documents pull models away from correct content even when current ones are retrieved.

## Lines we must NOT say

- "The NYC chatbot gave outdated information" or "Air Canada's bot used outdated content." Neither cause is established in sources I opened.
- "Air Canada paid $812" without "Canadian" or "total including interest and fees". Do not say the tribunal member's name unless re-verified from the decision.
- "AI search is wrong 1 in 6 times" as a general claim. It is legal research tools, 202 queries, and disputed. Say "in a Stanford study of legal AI tools".
- "34%" for Westlaw. The paper says 33%.
- "People trust fluent AI" as a proven single-study result. The opened evidence is about uncertainty wording and explanation length.
- Any statistic on growth in AI-generated content in organisations. Not found.
- "Robodebt" as an AI example, and do not connect the Deloitte/DEWR report to it.
- "The Deloitte report used GPT-4o" (snippet only), or that Deloitte refunded the full fee (about $98,000 is reported).
- "Hallucination-free", "true/false/fake". Say "supported by authoritative records", "not found", "possibly fabricated".
- That RAG research proves records repositories have this problem. The studies are on legal, medical and technical-document sets; present them as evidence of the mechanism.
