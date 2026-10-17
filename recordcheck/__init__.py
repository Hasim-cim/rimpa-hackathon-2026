"""Record Check engine. See ARCHITECTURE.md."""

from pathlib import Path

from dotenv import load_dotenv

# Load repo-root .env (keys and switches) before any module reads os.environ. Never commit .env.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
