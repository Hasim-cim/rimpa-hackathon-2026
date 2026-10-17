# 📚 Background brief

A 15-minute read so we're all working from the same facts. Every claim was checked on 15 Oct 2026. Anything marked ⚠️ was only seen in search summaries, so open the source before saying it on stage.

---

## The brief, as it actually reads

**Challenge (Hack Pack, section 01).** AI is amplifying bias, misinformation and disinformation, which reduces information quality and authenticity, undermines trust and weakens organisational integrity. We're asked:

1. How is the use of AI **in organisations** leading to these problems?
2. What are the **long-term risks for records and archives** that need mitigating?
3. What **information management (IM) skills and practices** could guard against them?
4. How can those skills, practices, **standards and protocols** be implemented as a solution?
5. How can the solution help **information managers play a strategic role** in AI initiatives?

Valid outputs: a best-practice guide; a methodology, strategy or protocol; a specification, algorithm or formula. Software isn't required, but it helps on *Functionality*.

**Three things that are easy to miss:**
- The hero is **the information manager inside an organisation**, not the general public.
- Question 2 is about **time**: what happens in 20–50 years to a record an AI touched. Few teams will answer it.
- Judges will be records professionals, not ML engineers.

## Judging criteria (Hack Pack p. 27)

| Criterion | Question |
|---|---|
| Idea & Solution | How creative is the idea? |
| Fit | How relevant is it to a real commercial or social problem? |
| Functionality | Could it work? Could it scale? |
| Presentation & Team | How persuasive was the pitch? Is the team balanced and credible? |

Pitch: **5 minutes**, then 5 minutes of judge questions.

## Judges

| Judge | Role | What to expect (our inference) |
|---|---|---|
| Josephine Secis | Assistant Director-General, Government Information & Collection Management, **NAA** (the sponsor) | Fit with NAA policy; authenticity over decades; could an agency adopt it? |
| James Price | MD, Experience Matters; co-author of *Information Asset Management*. His firm says "software is not a silver bullet" ([bio](https://dataleaders.org/james-price/)) | Business value; governance and people, not just software |
| Greg Long | Assistant Director, Maritime Warfare Centre, RAN | Nothing public found. Probably provenance and deliberate disinformation |
| Conni Christensen | Founding Partner, Synercon Group. Argues records automation fails on inconsistent metadata ([2014 talk](https://www.slideshare.net/InfoGovCon/conni-christensen)) | Metadata and classification rigour |

**Mentors (Monday):** Andrea McIntosh (M365 and Purview governance), **Michelle Tolliday** (chairs ISO/TC 46/SC 11, which owns the records standard ISO 15489), **John Cox** (on the **2024 winning team**, so ask him what made it land), Michael Haley, Errol Leboydre, Mark Cornish.

## What won before

- **2024: valuing information as a strategic asset.** The winner built a dashboard forecasting information value at 1, 6 and 12 months, with a Cost side and a Value matrix. Their line was "cost is factual, value is subjective." ([write-up](https://www.rimpa.com.au/resource/what-was-it-like-participating-in-a-hackathon.html))
- **2025: carbon footprint of IM.** The winner built a cost-optimisation tool that also **helps records managers decide what to archive and what to destroy**. Judges liked its "balance of sustainability and practicality". ([article](https://www.rimpa.com.au/resource/nt-team-win-hackathon.html))
- **The pattern (our read):** both turned an IM idea into money or decisions, both put a core IM act inside the tool, and both were judged *practical*.

## Five records ideas the judges take for granted

1. **A record is defined by function, not format.** It is information kept as evidence of business. The Archives Act 1983 s3 uses "any form (including any electronic form)" ([Act](https://www.legislation.gov.au/C2004A02796/2024-05-22/2024-05-22/text/original/pdf)). So an AI output used in business **is a record**.
2. **The four characteristics of authoritative records (ISO 15489)** and how AI breaks each:

| Characteristic | Meaning | How AI breaks it |
|---|---|---|
| Authenticity | It is what it claims, by whom, when | Deepfakes, synthetic documents |
| Reliability | The content is an accurate account | Hallucinated facts and citations |
| Integrity | Complete and unaltered | Summaries that drop meaning, silent "enhancement" |
| Usability | It can be found and interpreted | In 30 years, which model made this? |

3. **Context lives in metadata and provenance.** ISO 23081 is the records-metadata standard.
4. **Keeping or destroying is a legal decision.** Archives Act s24 makes destroying *or altering* a Commonwealth record an offence unless authorised. s24(5) says any electronic modification that loses information is *deemed destruction*.
5. **Keep by value and risk, not everything.** High-value / high-risk records get the most care ([NSW](https://www.nsw.gov.au/nsw-government/recordkeeping/plan/high-risk-records)).

## What regulators already say about AI records

- **NAA** ⚠️: AI-generated content is a Commonwealth record. Agencies **don't** have to keep every prompt. Keep outputs that are final records, feed significant records, evidence high-risk activity or inform decisions, and capture them in a records system, "not only in the AI tool". (Consistent with the [RIMPA summary](https://www.rimpa.com.au/resource/managing-records-created-with-ai-technologies-in-government.html).)
- **NSW:** metadata must record **that AI produced it, the software used, and the prompts or inputs** ([NSW](https://www.nsw.gov.au/nsw-government/recordkeeping/create-and-capture/ai-and-recordkeeping)).
- **UK archivists (ARA, Feb 2026):** document known biases, protect originals, treat AI output as a **non-authoritative suggestion**, ground generative tools in sources ([ARA](https://www.archives.org.uk/ai-preparedness-guidelines-for-archivists)).
- **ISO:** a working group on AI and records exists, but **nothing is published yet** ([SC 11](https://committee.iso.org/home/tc46sc11)).

> **The gap we can fill:** the guidance agrees on *what* to capture (an AI flag, the tool and version, the prompts, and which outputs evidence decisions). It says nothing about **how it gets captured at the moment someone pastes into a chatbot**. Nothing found records the **model version**, so a record made by a retired model can't be re-evaluated later.

## Vocabulary

- **Misinformation:** false, no intent to harm.
- **Disinformation:** false, deliberate harm.
- **Malinformation:** *true* but used to harm, e.g. leaks. This one is missing from our diagram.
  ([Wardle & Derakhshan 2017](https://shorensteincenter.org/information-disorder-framework-for-research-and-policymaking/))
- **Why LLMs make things up:** they produce plausible text, and training rewards guessing over "I don't know" ([Kalai et al. 2025](https://arxiv.org/abs/2509.04664)). Specifics like citations and catalogue numbers are what get invented.

## Case studies (pick at most two for the pitch)

| Case | What happened | Records lesson |
|---|---|---|
| **Deloitte / DEWR (2025)** | A ~A$440k government report with fake references and a made-up judicial quote. AI use was disclosed only afterwards, and Deloitte repaid the final instalment ([The Register](https://www.theregister.com/software/2025/10/06/deloitte-refunds-australian-government-over-ai-in-report/722000)) | No disclosure, no citation check, no audit trail |
| **AI medical scribe (ABC, Aug 2026)** | A scribe recorded psychedelic mushroom use the patient says never happened, and it went into a letter to her GP ([ABC](https://www.abc.net.au/news/2026-08-14/ai-medical-scribe-error-leaves-patient-devastated/107031672)) | AI text became the authoritative record, unmarked |
| **Fake court cases** | Mata v Avianca (US 2023). A Victorian solicitor's practising certificate was restricted in 2025 ([VLSB+C](https://lsbc.vic.gov.au/news-updates/news/statement-mr-dayal-matter)). The **NSW Supreme Court** now requires human citation checks and annexed prompts ([SC Gen 23](https://supremecourt.nsw.gov.au/documents/Practice-and-Procedure/Practice-Notes/general/current/PN_SC_Gen_23.pdf)) | Courts already run "records management of AI" |
| **Robodebt (2015–2019)** | Income averaging raised unlawful debts. The Royal Commission: "There simply were not records kept of who decided what, when" ([report](https://www.croakey.org/wp-content/uploads/2023/07/report_of-the-royal-commission-into-the-robodebt-scheme.pdf)) | Automated decisions need recorded rules and versions. *This was rules-based, not AI.* |
| **Arup deepfake (2024)** | ~US$25m lost after a video call where everyone else was a deepfake ([CNN via ABC17](https://abc17news.com/money/cnn-business-consumer/2024/05/16/british-engineering-giant-arup-revealed-as-25-million-deepfake-scam-victim/)) | A video call is not an authorisation record |
| **ICRC archives (Dec 2025)** | Public notice: chatbots invent archival catalogue numbers ([ICRC](https://www.icrc.org/en/article/important-notice-ai-generated-archival-references)). The Library of Virginia estimates ~15% of reference requests are ChatGPT-generated ([SciAm](https://www.scientificamerican.com/article/ai-slop-is-spurring-record-requests-for-imaginary-journals/)) | Archives bear the cost of proving a record *doesn't* exist |

## What already exists, and where it stops

- **Content Credentials (C2PA):** proves who made a piece of media, **not that it's true**. Voluntary, and can be stripped ([FAQ](https://c2pa.org/faq/)).
- **Citation checkers (e.g. GPTZero):** check references exist. Built for academic documents, not records.
- **Microsoft Purview:** retains Copilot and AI-app prompts and responses ([docs](https://learn.microsoft.com/purview/retention-policies-copilot)). It doesn't verify anything, and its docs don't mention the model version.
- **Blockchain for archives:** tried in the UK's ARCHANGEL project, 2017–19 ([Surrey](https://blockchain.surrey.ac.uk/projects/archangel.html)). Integrity isn't truth, and records sometimes must be corrected or destroyed. **Parked.**

## Corrections to our brainstorm

- **Retention:** the Royal Commission recommended **45 years** (Rec 8.1), not 99.
- **The 7-year figure** is Corporations Act financial records ([ASIC](https://asic.gov.au/for-business-and-companies/companies/company-building-blocks/company-record-keeping/)). We couldn't confirm an APRA rule.
- **Dutch benefits scandal:** say "algorithmic risk scoring using nationality", not "AI".
- **Google Scholar has no API.** Use Crossref or OpenAlex.
