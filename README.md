# Record Check

*Prototype for the RIMPA Global Hackathon 2026. Records management decides what to trust by evidence,
not by whether AI touched it.*

Four steps of one workflow for an AI-assisted document:

1. **Check citations** — each reference is looked up; reported as found / mismatch / not found / not checked.
2. **Weigh the evidence** — each sentence is traced to authoritative records: supported / weak / unsupported / contradicted.
   AI-written and human-written sentences get the same test.
3. **Issue the passport** — a record package (what, who, which model, why, how, who reviewed), tiered by
   NAA's risk rule, with a hash chain.
4. **Recall** — mark a model faulty, find every record it helped make, queue the risky ones for re-review.

## Run

```bash
uv sync
cp .env.example .env            # optional: ANTHROPIC_API_KEY, OPENALEX_API_KEY, RECORDCHECK_ONLINE=true
uv run streamlit run app/streamlit_app.py        # the console
uv run uvicorn api.main:app --reload             # the engine as an API, http://127.0.0.1:8000/docs
uv run pytest -q                                 # offline tests, no key needed
```

Everything runs offline from `data/seed/` (invented case, invented records, cached citation lookups).
With a key and a network it upgrades to live Crossref/OpenAlex and LLM claim splitting.

Design and module contracts: [`ARCHITECTURE.md`](ARCHITECTURE.md).
Planning, research and the pitch: `~/repos/rimpa-hackathon-2026`.
