"""Generate data/seed/ai_events.json and data/seed/passports.json deterministically.

Run: uv run python scripts/make_seed.py
All people, prompts and outputs are invented.
"""

from __future__ import annotations

import json
import random
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from recordcheck import db, passport  # noqa: E402
from recordcheck.models import AIEvent, Review, ToolCall  # noqa: E402

N7, N8, ATLAS = "northstar-7-2026-03-01", "northstar-8-2026-09-15", "atlas-mini-2025-11-20"
PROVIDER = {N7: "Northstar AI (fictional vendor)", N8: "Northstar AI (fictional vendor)", ATLAS: "Atlas Labs (fictional vendor)"}
WINDOW = {N7: ("2026-03-05", "2026-09-14"), N8: ("2026-09-15", "2026-10-10"), ATLAS: ("2026-03-05", "2026-10-10")}
SOURCES = ["REC-2026/003540", "REC-2026/004740", "REC-2026/004790", "REC-2026/004802", "REC-2026/004805", "REC-2026/004809"]
RESERVED = {"REC-2026/003540", "REC-2026/004740", "REC-2026/004790", "REC-2026/004802", "REC-2026/004805", "REC-2026/004809", "REC-2026/004811"}

FUNCTIONS = ["Debt waiver assessment", "Eligibility review", "Policy briefing", "Correspondence", "Case note summary"]
USERS = ["A. Caseworker", "C. Officer", "D. Analyst"]
REVIEWER = "B. Team Leader"
SNIPPETS = {
    "Debt waiver assessment": ("Summarise the hardship evidence for case {c} for the delegate.", "Hardship summary for case {c}: income and rent are on file; the delegate should confirm household size."),
    "Eligibility review": ("Check the eligibility criteria against case {c}.", "Case {c} appears to meet two of three criteria; residency evidence is outstanding."),
    "Policy briefing": ("Brief me on the current hardship policy in two paragraphs.", "The hardship policy allows case-by-case waiver; version 4 replaced version 3 in July."),
    "Correspondence": ("Draft a letter to the applicant on case {c} asking for bank statements.", "Dear applicant, please supply your bank statements for July and August for case {c}."),
    "Case note summary": ("Summarise the case notes for case {c} in five lines.", "Case {c}: two contacts this month, one document received, review due in 14 days."),
}

# (model, app, kind) kinds: T0 plain, T1 default, T1x exported, T2 decision, T3 agent action
SPECS = (
    [(N7, "agency-assistant", "T1")] * 8 + [(N7, "drafting-helper", "T1x")] * 3
    + [(N7, "agency-assistant", "T2")] * 3
    + [(N7, "policy-chat", "T0")] * 2 + [(N7, "drafting-helper", "T0")] * 2
    + [(N8, "agency-assistant", "T1")] * 3 + [(N8, "agency-assistant", "T2")] * 2 + [(N8, "case-agent", "T3")]
    + [(N8, "policy-chat", "T0")] * 2 + [(N8, "drafting-helper", "T0")]
    + [(ATLAS, "agency-assistant", "T1")] * 4 + [(ATLAS, "policy-chat", "T1x")] + [(ATLAS, "agency-assistant", "T2")] * 3
    + [(ATLAS, "case-agent", "T3")] + [(ATLAS, "policy-chat", "T0")] * 2 + [(ATLAS, "drafting-helper", "T0")] * 2
)


def main() -> None:
    rnd = random.Random(20261019)
    rules = passport.load_tier_rules()
    items = []
    for model, app, kind in SPECS:
        lo, hi = (datetime.fromisoformat(x) for x in WINDOW[model])
        t = lo + timedelta(seconds=rnd.randrange(int((hi - lo).total_seconds()) + 86400 - 1))
        items.append((t.replace(microsecond=0), model, app, kind))
    items.sort(key=lambda x: x[0])

    events: list[AIEvent] = []
    for i, (t, model, app, kind) in enumerate(items, 1):
        fn = rnd.choice(FUNCTIONS if kind != "T3" else ["Case note summary"])
        if kind == "T2":
            fn = rnd.choice(["Debt waiver assessment", "Eligibility review"])
        case = f"2026/{rnd.randrange(100, 999):04d}"
        p, o = SNIPPETS[fn]
        tool_calls = []
        if kind == "T3":
            tool_calls = [ToolCall(name="case_system.update_status", side_effect=True, summary=f"Set case {case} status to 'awaiting documents'"),
                          ToolCall(name="case_system.read_notes", side_effect=False, summary=f"Read notes for case {case}")]
        events.append(AIEvent(
            id=f"EVT-2026-{i:04d}", app_id=app, user=rnd.choice(USERS), created=t,
            prompt=p.format(c=case), system_prompt=None if app == "policy-chat" else f"You are the {rules.app_names[app].split(' (')[0]}. Be concise; cite source records.",
            output=o.format(c=case), model_requested=model, model_returned=model, provider=PROVIDER[model],
            source_record_ids=[] if kind in ("T0",) else rnd.sample(SOURCES, rnd.randint(1, 3)),
            tool_calls=tool_calls,
            exported_to_document=f"DOC-2026/{case.split('/')[1]}-note" if kind == "T1x" else None,
            decision_flag=kind == "T2", function=fn if kind != "T3" else "Case note summary",
        ))

    with tempfile.TemporaryDirectory() as td:
        conn = db.connect(Path(td) / "seed.sqlite")
        db.init(conn)
        rid = 2400
        for e in events:
            rid += rnd.randrange(7, 95)
            while f"REC-2026/{rid:06d}" in RESERVED:
                rid += 1
            tier = passport.classify(e, rules)
            review = None
            if tier in ("T2", "T3"):
                review = Review(reviewer=REVIEWER, decision=rnd.choice(["approved", "approved", "approved_with_edits"]),
                                reviewed_at=e.created + timedelta(hours=rnd.randint(2, 30)), note="Checked against source records.")
            passport.build(e, tier=tier, review=review, conn=conn, rules=rules, record_id=f"REC-2026/{rid:06d}")
        assert rid < 4700, rid
        report = passport.verify_chain(conn)
        assert report.ok, report
        passports = db.get_passports(conn)
        conn.close()

    seed = ROOT / "data" / "seed"
    (seed / "ai_events.json").write_text(json.dumps([e.model_dump(mode="json") for e in events], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (seed / "passports.json").write_text(json.dumps([p.model_dump(mode="json") for p in passports], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    from collections import Counter
    c = Counter((p.agent.model_returned, p.business.tier) for p in passports)
    for m in (N7, N8, ATLAS):
        print(m, {t: c[(m, t)] for t in ("T0", "T1", "T2", "T3")})
    print("total", len(passports), "last id", passports[-1].record.id)


if __name__ == "__main__":
    main()
