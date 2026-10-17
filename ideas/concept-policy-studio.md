# Concept: Policy studio — the information manager defines what good looks like

*Added 17 Oct as a layer on Record Check. Hasim's idea: give IMs creative control over the rules.*

Status: **building in the prototype** (`~/repos/record-check`, Setup tab). Design choices are ours 💭.

## The gap it fills

Record Check judges documents by evidence rather than by whether AI touched them. But *someone* has to say
what counts as evidence, which documents matter, and what "good enough to file" means. If that is hard-coded,
the information manager is a spectator. If the IM configures it, records management is in the AI control
loop before the first prompt. That is the brief's question 5.

## What the IM sets up 💭

| Setting | Example | What it drives |
|---|---|---|
| **Sector profile** | Commonwealth agency · state agency · health service · local council | Default document types, retention, and which guidance the passport cites |
| **Document types monitored** | Decision letter, case note, briefing, clinical note | Default tier per type and which checks run |
| **Quality bar per type** ("what good looks like") | Decision letter: no unsupported or contradicted claims, all citations found or not checked, a named reviewer | The **filing gate**: Ready to file / Needs attention / Blocked, with reasons |
| **Authoritative systems** | Case management, payroll, policy library; *not* saved web pages | What counts as evidence when claims are weighed |
| **Apps and default tiers**, **retention periods** | Existing `tier_rules.json`, now editable | Capture tiers and disposal |

The rules are configuration. No LLM decides what a record is. The LLM may **suggest** a starting profile from a
one-sentence description of the organisation; the IM confirms every field. Offline, the IM picks a preset.

## Why the judges should care

- **Price (shelfware):** staff never configure anything; the IM sets the rules once and the gate does the rest.
- **Christensen (metadata rigour):** this is metadata modelling driven by business-activity analysis, as a form.
- **Secis / NAA:** the tiers, retention and holds are the NAA risk rule made editable per agency.
- **Long (adversaries):** the authoritative-systems list is a whitelist; a planted web page cannot become evidence.

## Honest limits

- Presets are our generic starting points, not transcriptions of any regulator's rules. Say "starting point".
- The quality bar is a set of thresholds over our four weights and four citation statuses, so it is only as
  good as the linking rules underneath.
- Health and finance presets are illustrative; the research verified government guidance only.

## Build (same day)

`policy.json` (active policy) + `policy_presets.json` (sector presets) → `policy.py` (load, save, apply preset) →
`gate.py` (assessment + citations + review → GateResult) → Setup tab (forms) → Check tab shows the gate
→ passport records policy version, document type and gate result.
