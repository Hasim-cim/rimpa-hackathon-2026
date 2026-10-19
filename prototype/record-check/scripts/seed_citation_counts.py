"""Give a few seed passports citation counts, then re-hash and re-link the seed chain (the hash covers them).

Run: uv run python scripts/seed_citation_counts.py   (idempotent; edits data/seed/passports.json in place)
The counts are invented. They let the dashboard's recall signal show: one model crosses it, one stays well below.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from recordcheck import passport  # noqa: E402
from recordcheck.models import Passport  # noqa: E402

# (found, mismatch, not_found, not_checked). northstar-7: 15 checked, 5 not found (33%); atlas-mini: 12 checked, 1 not found (8%)
COUNTS = {
    "REC-2026/002585": (2, 0, 1, 0), "REC-2026/002756": (1, 0, 2, 0), "REC-2026/002805": (2, 0, 1, 0),
    "REC-2026/002891": (3, 0, 0, 0), "REC-2026/002972": (2, 0, 1, 0),
    "REC-2026/002639": (3, 0, 0, 0), "REC-2026/003102": (3, 0, 0, 0), "REC-2026/003392": (2, 1, 0, 0),
    "REC-2026/003692": (2, 0, 1, 0),
}


def main() -> None:
    path = ROOT / "data" / "seed" / "passports.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    prev = None
    for d in raw:
        p = Passport(**d)
        if p.record.id in COUNTS:
            p.process.citation_summary = dict(zip(passport.CITATION_KEYS, COUNTS[p.record.id]))
        p.integrity.prev_hash = prev
        p.integrity.hash = passport.compute_hash(p)
        prev = p.integrity.hash
        d["process"]["citation_summary"] = p.process.citation_summary
        d["integrity"]["prev_hash"], d["integrity"]["hash"] = p.integrity.prev_hash, p.integrity.hash
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(raw)} passports; chain head {prev[:12]}")


if __name__ == "__main__":
    main()
