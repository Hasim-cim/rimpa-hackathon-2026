# Live data and real metadata: what to build on (19 Oct, pre-plan test)

**Question:** which live public API can the demo run on, and which metadata standard should our record and passport
fields follow?

**Answer:** the **Federal Register of Legislation API** for live data, and the **NAA Minimum Metadata Set** (built on
AGRkMS 2.2) for field names. I called the API myself on 19 Oct. The responses are saved in
[`live-api-evidence/frl/`](live-api-evidence/frl/) and can serve as offline fixtures.

Markers as usual. A link means the page was opened. "Archived copy" means it was opened through the Wayback Machine,
because naa.gov.au, trove.nla.gov.au and glam-workbench.net block automated fetches. Those copies date from 2025, so
check there's no newer version before quoting them on stage.

## 1. Federal Register of Legislation API: use it

- **Access.** The API is OData at `https://api.prod.legislation.gov.au/v1/`, documented in Swagger at
  [api.prod.legislation.gov.au/swagger](https://api.prod.legislation.gov.au/swagger/index.html). The register's
  [data share and reuse page](https://www.legislation.gov.au/help-and-resources/using-the-legislation-register/data-share-and-reuse)
  says no API key is needed. It also says the API may change, and heavy use may be throttled or blocked.
- **Licence.** The same page says most content is Creative Commons and reuse, including commercial reuse, is allowed.
  It doesn't give the CC version, so check the terms page before quoting one.
- **Live calls on 19 Oct**, plain curl, 1.3 to 3.6 s each:

| Call | Result |
|---|---|
| `/titles?$filter=name eq 'Public Service Act 1922'` | `C1922A00021`, **Repealed** 1999-12-05. The register names the repealing Act as the Public Employment (Consequential and Transitional) Amendment Act 1999. It does **not** say "replaced by" the 1999 Act |
| `/titles?$filter=name eq 'Public Service Act 1999'` | `C2004A00538`, **InForce** |
| `/titles?$filter=name eq 'Social Security Act 1991'` | `C2004A04121`, **InForce** |
| `/versions?$filter=titleId eq 'C2004A02796' and isCurrent eq true` | Archives Act 1983, **compilation 51**, `C2026C00223`, from 2026-06-01 |

- **Gotchas** (from the research agent's calls):
  - `/versions` also returns future-dated versions, so always filter on `isCurrent eq true`.
  - Filtering on `status` errors, so look titles up by name or id and read `status` from the result.
  - Name matching is exact, so strip "(Cth)" and section numbers first.
- **The API works at the level of an Act and its compilations, not sections.** It can say an Act is in force or
  repealed, or that a compilation is current or superseded. It can't confirm that s 1237AAD exists or says what a
  draft claims. 💭 Wording: "Act found in force on the Federal Register of Legislation; section for a person to confirm".

### 💭 Why it fits
- It needs no key, it's authoritative and it's Commonwealth. It's also exactly the kind of source an NAA executive trusts.
- It fills our known gap: legislation citations currently return `not_checked`. The seed's own citation [1],
  "Social Security Act 1991 (Cth) s 1237AAD", would become "Act in force (C2004A04121); section for a person to
  confirm".
- **Repealed and superseded compilations map directly onto superseded-source recall.** Demo idea: an AI draft cites
  the Public Service Act 1922. The live lookup says "repealed on 5 December 1999". Only say "replaced by" where the register itself states it. Recall
  then lists every retained output that cites the old Act.
- Effort is about 2 to 3 hours: a small client, title normalisation, mapping to a `CitationResult` with a new
  `source` value, the JSON fixtures above for offline, and a live switch like Crossref's.

## 2. The others: don't build on them for tomorrow
- **data.gov.au CKAN.** The live API works with no key: `package_search`/`package_show`, 48,920 results for
  "records". But it holds **dataset** metadata, not records, so it's a poor fit for checking a draft. ⚠️ We didn't find
  an NAA organisation slug.
- **NAA RecordSearch.** There's no API. The GLAM Workbench (archived copy) says "RecordSearch doesn't provide access to
  machine-readable data through an API" and that changes in May 2025 "blocked the screen scrapers". Don't scrape it.
- **Trove API v3.** It needs a key from a request form. The page (archived copy) says "most requests will be answered
  within a week", which is too slow for tomorrow.

## 3. The metadata standard to follow

**AGRkMS v2.2** (June 2015; PDF, archived copy, and the NAA page lists 2.2 as current).
- It has five entities: **Record, Agent, Business, Mandate, Relationship**.
- It has 26 properties: 8 mandatory, 12 conditional and 6 optional.
- Mandatory for a Record: Category, Identifier, Name, Date Range (start), Disposal (Records Authority) and Extent.
- **Rights, Language, Format, Integrity Check and Security Classification are conditional, not mandatory. Don't call
  them mandatory.**

**NAA Minimum Metadata Set**, from the [current NAA page](https://www.naa.gov.au/information-management/standards/australian-government-recordkeeping-metadata-standard/minimum-metadata-set).
I opened it in a real browser on 19 Oct; the levels below match the archived copy. It's "a simplified application of" AGRkMS 2.2,
"focused only on the Record entity", in three cumulative levels. "You must use at least the properties of the Core level". Also:
**"The value and expected longevity of information determines the amount of metadata that must be kept about it."** That's the
NAA's own risk-tiered principle, in its words, and it's safe to quote on stage. The
[AGRkMS page](https://www.naa.gov.au/information-management/standards/australian-government-recordkeeping-metadata-standard)
(also opened on 19 Oct) confirms Version 2.2 is current.
- **Core:** Identifier, Creator, Date Created.
- **Additional:** Title, Protective Marking, Disposal Class, Format.
- **Transfer:** Rights, Integrity Check.

### 💭 Our fields mapped to it

| Our field | NAA property | Have it? |
|---|---|---|
| record `id` | Identifier (+ Identifier Scheme) | Yes, but the scheme is missing |
| `created_by` / passport agent person | Creator | Yes |
| `created` | Date Created | Yes |
| `title` | Title (Name Words) | Yes |
| none | **Protective Marking** | **Missing** (e.g. OFFICIAL, OFFICIAL: Sensitive) |
| passport business `disposal` | Disposal Class (+ Records Authority) | Free text only; needs structuring |
| none | **Format** | **Missing** (e.g. text/plain, application/pdf) |
| none | **Rights** | **Missing** |
| `hash` / passport integrity | Integrity Check (Hash Function Name `sha256`, Message Digest) | Yes |
| passport agent | AGRkMS Agent entity | Yes |
| passport business `function` | AGRkMS Business entity | Yes |
| `status`, `superseded_by`, `corrects` | AGRkMS Relationship (Related Entity, Change History) | Yes |
| `tier`, evidence weights, `not_for`, `review_due` | No equivalent | Our extensions |

**What this gives the pitch:** "Every passport carries the NAA Minimum Metadata Set's Core and Additional
properties, plus the AI fields the NAA and NSW guidance ask for." The current NAA page has now been opened (19 Oct) That line only holds once the four missing fields
(Protective Marking, Format, Rights, structured Disposal Class) are added. Until then, say "maps onto the NAA Minimum
Metadata Set, with four fields to add".

**NAA guidance specific to AI records:** ⚠️ search snippet only. naa.gov.au/node/3660 couldn't be fetched and has no
archived copy, so don't quote its wording.

## Next step
Handed to planning (`-ac`). There are two candidate build items:
1. Live legislation citation checks, with fixtures.
2. The four missing Minimum Metadata Set fields on passports, plus a "Metadata" group on the passport card labelled
   with the NAA property names.

## Addendum: pre-plan test of the legislation lookup (19 Oct, afternoon)
I ran 10 realistic citations through a throwaway probe, now saved at [`live-api-evidence/frl/probe.py`](live-api-evidence/frl/probe.py).
It uses only the standard library, with no key.

**Name clean-up works.** Strip "(Cth)" and anything from a section or schedule marker onward ("s 1237AAD", "sch 1", "s 24"),
then match exactly with `name eq '<Act name year>'`.

| Cited as | Register answer |
|---|---|
| Social Security Act 1991 (Cth) s 1237AAD | C2004A04121, InForce |
| Public Service Act 1922 (Cth) | C1922A00021, Repealed |
| Archives Act 1983 (Cth), s 24 | C2004A02796, InForce |
| Privacy Act 1988 (Cth) sch 1 | C2004A03712, InForce |
| Freedom of Information Act 1982 | C2004A02562, InForce |
| Public Governance, Performance and Accountability Act 2013 (Cth) s 15 | C2013A00123, InForce |
| Data Availability and Transparency Act 2022 | C2022A00011, InForce |
| **Social Security Act 1947** | C1947A00026, titled **"Social Services Consolidation Act 1947"**, Repealed. **Exact match also searches `nameHistory`**: the Act was renamed Social Security Act 1947 in 1982. Show both names. |
| Privacy Act 1989 (wrong year) | No exact match. A `contains(name,'Privacy Act')` fallback returns instruments such as "Privacy Act 1988 - Tax File Number Guidelines" |
| Records Integrity Act 2021 (invented) | Nothing |

**What the API can't do:**
- **No server-side fuzzy search.** Combining filters (`collection eq 'Act' and startswith(...)`) returns HTTP 400.
- `startswith` timed out after 20–26 s.
- A wrong year has to be handled client-side. Use `contains` on the stem, keep only results whose `collection` is `Act`, compare
  the years, and call it "found, details differ: the register has Privacy Act 1988".

**Speed varies a lot.**
- Calls took 1.4–2 s at first, then 7–12 s, then timed out, after about 25 calls in a few minutes.
- Assume rate limiting, which the docs warn of.
- So the build needs a per-title cache in the existing `citation_cache` table, a timeout of about 8 s that falls back to
  "not checked", and **prefetched fixtures for every demo citation**.
- Never call it live on stage without a warm cache.

💭 **Suggested statuses**, using the existing `CitationResult` statuses (wording rule 7):

| Situation | Status | Note |
|---|---|---|
| Exact match, in force | `found` | "Act found in force on the Federal Register of Legislation (C2004A04121); section for a person to confirm" |
| Exact match, repealed | `mismatch` | "Repealed on <date> (register)". Only name a replacement if the register says so. |
| Matched through name history | `found` / `mismatch` | Add "listed on the register as <current title>" |
| Same stem, different year | `mismatch` | "The register has <name> <year>, not <cited year>" |
| No match | `not_checked` | "No Commonwealth Act of this name on the Federal Register of Legislation; a person should confirm (it may be state legislation or misnamed)". **Never "possibly fabricated"**: the register only holds Commonwealth law, so a state Act or a regulation would be wrongly flagged. Planner override, 19 Oct. |
| Timeout or error | `not_checked` | "Register did not respond; a person confirms" |
