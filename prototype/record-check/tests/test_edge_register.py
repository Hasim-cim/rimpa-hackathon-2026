"""Keeps EDGE_CASES.md honest. Pure parsing and ast; imports no engine code, offline, well under a second.

Checks: IDs unique; every tested row names a test that exists; every gap row has a strict xfail in
test_edge_gaps.py whose reason contains the ID (and no xfail is orphaned); the summary counts match the rows.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "EDGE_CASES.md"
GAPS_FILE = "tests/test_edge_gaps.py"

STATUSES = {"✅": "✅ tested", "🟡": "🟡 by design, untested", "❌": "❌ gap", "⛔": "⛔ out of scope by design"}
ID_RE = re.compile(r"^EC-[A-Z]{3}-\d{2}$")


def rows():
    out = []
    for line in REGISTER.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| EC-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        assert len(cells) == 5, f"row should have 5 columns: {line[:60]}"
        out.append(dict(id=cells[0], scenario=cells[1], expected=cells[2], status=cells[3], test=cells[4]))
    return out


def node_ids(cell):
    return re.findall(r"`([^`]+\.py::[^`]+)`", cell)


def functions(path):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def xfail_reason(fn):
    """(strict, reason) of the pytest.mark.xfail decorator on fn, or None."""
    for d in fn.decorator_list:
        if isinstance(d, ast.Call) and ast.unparse(d.func).endswith("xfail"):
            kw = {k.arg: k.value for k in d.keywords}
            strict = isinstance(kw.get("strict"), ast.Constant) and kw["strict"].value is True
            reason = kw.get("reason")
            return strict, (reason.value if isinstance(reason, ast.Constant) else "")
    return None


def test_register_has_rows_and_valid_ids():
    rs = rows()
    assert len(rs) > 50
    assert all(ID_RE.match(r["id"]) for r in rs), [r["id"] for r in rs if not ID_RE.match(r["id"])]


def test_ids_are_unique():
    ids = [r["id"] for r in rows()]
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})


def test_every_status_is_known():
    for r in rows():
        assert r["status"] in STATUSES.values(), f"{r['id']}: unknown status {r['status']!r}"


def test_tested_rows_point_at_tests_that_exist():
    cache = {}
    for r in rows():
        if not r["status"].startswith("✅"):
            continue
        ids = node_ids(r["test"])
        assert ids, f"{r['id']}: a tested row must name its test as `file.py::test_name`"
        for nid in ids:
            path, name = nid.split("::", 1)
            assert (ROOT / path).exists(), f"{r['id']}: no such file {path}"
            fns = cache.setdefault(path, functions(path))
            assert name in fns, f"{r['id']}: {path} has no test {name}"
            assert name.startswith("test"), f"{r['id']}: {name} is not a test"
            assert xfail_reason(fns[name]) is None, f"{r['id']}: {name} is an xfail, so the row cannot be tested"


def test_gap_rows_have_a_strict_xfail_with_their_id():
    fns = functions(GAPS_FILE)
    for r in rows():
        if not r["status"].startswith("❌"):
            continue
        ids = node_ids(r["test"])
        assert len(ids) == 1 and ids[0].startswith(GAPS_FILE + "::"), f"{r['id']}: name one test in {GAPS_FILE}"
        name = ids[0].split("::", 1)[1]
        assert name in fns, f"{r['id']}: {GAPS_FILE} has no test {name}"
        x = xfail_reason(fns[name])
        assert x is not None, f"{r['id']}: {name} needs @pytest.mark.xfail(strict=True, reason=...)"
        strict, reason = x
        assert strict, f"{r['id']}: xfail must be strict=True"
        assert r["id"] in reason, f"{r['id']}: xfail reason must contain the ID"


def test_no_orphan_xfail_in_gaps_file():
    gap_ids = {r["id"] for r in rows() if r["status"].startswith("❌")}
    for name, fn in functions(GAPS_FILE).items():
        x = xfail_reason(fn)
        if x is None:
            continue
        found = re.findall(r"EC-[A-Z]{3}-\d{2}", x[1])
        assert found and found[0] in gap_ids, f"{name}: xfail reason {x[1]!r} does not match a gap row in EDGE_CASES.md"


def test_non_tested_rows_carry_a_note():
    for r in rows():
        if r["status"].startswith(("🟡", "⛔")):
            assert r["test"], f"{r['id']}: give a note"
        if r["status"].startswith("⛔"):
            assert "Pitch answer" in r["expected"] or "Pitch answer" in r["scenario"], f"{r['id']}: out-of-scope rows need a pitch answer"


def test_summary_counts_match_the_rows():
    text = REGISTER.read_text(encoding="utf-8")
    actual = {label: 0 for label in STATUSES.values()}
    for r in rows():
        actual[r["status"]] += 1
    for label, n in actual.items():
        m = re.search(rf"^\| {re.escape(label)} \| (\d+) \|", text, re.M)
        assert m, f"summary row for {label!r} missing"
        assert int(m.group(1)) == n, f"summary says {m.group(1)} for {label}, rows say {n}"
