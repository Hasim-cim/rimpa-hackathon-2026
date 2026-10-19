import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import recordcheck  # noqa: E402,F401  (loads .env; we then strip the key so tests are offline and keyless)

os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("DATABASE_URL", None)  # tests run on SQLite; tests/test_postgres.py opts in separately
os.environ["RECORDCHECK_ONLINE"] = "false"
