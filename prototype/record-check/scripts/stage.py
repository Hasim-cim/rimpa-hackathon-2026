"""Stage database: the demo runs on its own target, and this resets only that target.

    uv run python scripts/stage.py reset                       # local: data/stage.sqlite + data/stage-policy.json
    uv run python scripts/stage.py reset --database-url URL --yes   # a Postgres stage branch (Neon), wiped and reseeded
    uv run python scripts/stage.py env                         # prints the env lines to run the console on stage

The script never reads DATABASE_URL from the environment, so it cannot reach the shared database by accident.
Run the console on stage locally with:
    RECORDCHECK_DB=data/stage.sqlite RECORDCHECK_POLICY=data/stage-policy.json uv run streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STAGE_DB = ROOT / "data" / "stage.sqlite"
STAGE_POLICY = ROOT / "data" / "stage-policy.json"


def reset(database_url: str | None = None, db_file: Path = STAGE_DB, policy_file: Path = STAGE_POLICY) -> str:
    os.environ.pop("DATABASE_URL", None)          # only the target named here is ever touched
    if database_url:
        os.environ["DATABASE_URL"] = database_url
    else:
        os.environ["RECORDCHECK_DB"] = str(db_file)
        os.environ["RECORDCHECK_POLICY"] = str(policy_file)
    from recordcheck import db, passport, policy
    db._shared = None
    if not database_url:
        for f in (db_file, Path(f"{db_file}-wal"), Path(f"{db_file}-shm"), policy_file):
            f.unlink(missing_ok=True)
    conn = db.open_db()
    try:
        counts = db.reset(conn)
        policy.reset()
        pol = policy.load()                       # back to the default preset
        chain = passport.verify_chain(conn)
    finally:
        conn.close()
        if db._shared is not None:
            db._shared.close()
            db._shared = None
    where = urlsplit(database_url).hostname if database_url else str(db_file)
    return (f"Stage reset: {where}. Seeded {counts.get('passports', 0)} passports, {counts.get('records', 0)} records; "
            f"policy v{pol.version} ({pol.sector}); chain {'ok' if chain.ok else 'BROKEN'} ({chain.checked}).")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("reset", help="wipe and reseed the stage target")
    r.add_argument("--database-url", help="Postgres stage target; must not be the shared database")
    r.add_argument("--yes", action="store_true", help="confirm wiping a Postgres target")
    sub.add_parser("env", help="print the env lines for running on the local stage DB")
    a = ap.parse_args(argv)
    if a.cmd == "env":
        print(f"RECORDCHECK_DB={STAGE_DB}\nRECORDCHECK_POLICY={STAGE_POLICY}")
        return 0
    if a.database_url and not a.yes:
        print(f"Refusing to wipe {urlsplit(a.database_url).hostname} without --yes.", file=sys.stderr)
        return 2
    print(reset(a.database_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
