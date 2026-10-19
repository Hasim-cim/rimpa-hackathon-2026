# Open questions

These are the things we have to check before we rely on them. Tick each one off with a source once it's
answered.

| # | Question | Why it matters | Owner | Status |
|---|---|---|---|---|
| 1 | **Is code written before the event allowed?** The hack pack doesn't say | Decides whether we can prototype this weekend or only spike and specify | Anyone: email admin@rimpa.com.au, or ask at 08:00 Monday | ⏳ |
| 2 | **Prior art: LLM gateways and observability** (e.g. Langfuse, Helicone, Portkey, LiteLLM). What do they log, and do they record the model version per call? | If we pitch "we log AI calls", a judge can say that exists. Our difference has to be the **records layer**: risk tiers, disposal, record export, paradata | Hasim | ⏳ |
| 3 | **Prior art: Microsoft Purview for Copilot and AI apps.** Does the audit or interaction schema capture the model or version? | The judges' likeliest "isn't this just X?" | Expert | ⏳ |
| 4 | **Prior art: records vendors** (RecordPoint, Objective, OpenText). Any capture of AI interactions as records? | Same | Expert | ⏳ |
| 5 | Does any product do **model recall**: find every record that relied on a given model or version? | If none does, this is our most novel piece | Hasim | 🟡 Partly (19 Oct): no product found that recalls retained outputs by model or by source record; Purview logs accessed files, tracing tools log retrieved documents. Say "in the documentation we reviewed we did not find". See `research/session-1-outcomes-2026-10-19.md` |
| 6 | Map ISO 23081 entities onto the NSW AI metadata rule and the InterPARES paradata categories | Conni Christensen and Michelle Tolliday will test metadata rigour | Expert | ⏳ |
| 7 | When is NAA's agentic AI guidance due? | If it lands before Tuesday, cite it. If not, "you said it's coming, here's a working answer" | Expert | ⏳ |
| 8 | Re-open the NAA Check-up 2025 figures (87% use AI, 15% use it in IM, 8% for metadata) | A strong statistic for the Fit argument, but still ⚠️ | Storyteller | ⏳ |
| 9 | Which LLM API do we use for the demo, and what does its response give us (model id, citations or sources)? | Model version capture depends on it | Hasim | ✅ Claude API, Haiku (`claude-haiku-5-5`). `response.model` returns the exact model id; the passport stores it as "model returned". Tested 17 Oct in the prototype |
