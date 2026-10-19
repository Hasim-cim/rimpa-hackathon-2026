"""Vercel entrypoint: the same API, served under /api."""

import os

# Records live in Neon Postgres (DATABASE_URL, set by the Vercel integration); db.py ignores these then.
# ponytail: without DATABASE_URL, fall back to SQLite in /tmp, which is per instance and reseeds on every cold
# start, so writes vanish between requests. Only for a deployment with no database attached.
os.environ.setdefault("RECORDCHECK_DB", "/tmp/recordcheck.sqlite")
os.environ.setdefault("RECORDCHECK_POLICY", "/tmp/policy.json")

from fastapi import FastAPI  # noqa: E402

from api.main import app as engine  # noqa: E402  (reads the env vars above at import)

app = FastAPI()
app.mount("/api", engine)  # one /api prefix on Vercel leaves the rest of the URL space to the web app
