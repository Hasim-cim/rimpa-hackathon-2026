"""The simple Policy studio (Setup tab), and using it for NAA-facing documents. Offline.

Walkthrough: a Commonwealth information manager keeps the Commonwealth preset, adds two document types an agency
under NAA rules produces (a ministerial brief; a record of an agent's action, the area NAA says its guidance does not
yet cover), saves, and checks a document under the new type. The documents and the brief's text are invented.
"""
from __future__ import annotations

import importlib
import sys

import pytest

from recordcheck import citations as cit
from recordcheck import policy as policymod
from recordcheck.models import DocumentType

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_console import at, button, db_path, go, select, start_check  # noqa: E402,F401  (fixtures and helpers)

BRIEFING = "DOC-2026/briefing-waivers"

# an invented ministerial brief that cites NAA guidance and the Archives Act, as an NAA-facing document would
NAA_BRIEF = {
    "title": "Ministerial brief: AI-assisted debt waiver letters",
    "body": "AI-generated content created by the agency is a Commonwealth record [1]. "
            "The agency keeps prompts only where they give context to a retained output [1]. "
            "The Archives Act governs the disposal of Commonwealth records [2].",
    "references": "[1] National Archives of Australia (2026). Information management for current, emerging and "
                  "critical technologies. https://www.naa.gov.au/node/3660\n[2] Archives Act 1983 (Cth).",
}


# ---------- engine: levels ----------

def test_levels_match_the_commonwealth_preset_exactly():
    types = {d.id: d for d in policymod.get_preset("commonwealth-agency").document_types}
    assert policymod.level_of(types["decision-letter"]) == "strict"
    assert policymod.level_of(types["briefing"]) == "standard"
    assert policymod.level_of(types["case-note"]) == "light"
    assert policymod.level_of(types["correspondence"]) is None          # custom bars are kept, never rewritten


def test_new_type_and_describe():
    t = policymod.new_type("  Ministerial   brief ", "standard", "T2", [])
    assert (t.id, t.name, t.default_tier, policymod.level_of(t)) == ("ministerial-brief", "Ministerial brief", "T2",
                                                                     "standard")
    assert "a named reviewer at T2 and T3" in policymod.describe(t) and "references looked up" in policymod.describe(t)
    with pytest.raises(ValueError):
        policymod.new_type("ministerial brief", "strict", "T2", [t])     # same name, any case
    with pytest.raises(ValueError):
        policymod.new_type(" !! ", "strict", "T2", [])
    light = policymod.apply_level(DocumentType(id="x", name="X"), "light")
    assert policymod.describe(light).startswith("Blocked by more than 1 unsupported claim")


# ---------- the studio, clicked ----------

def _setup_form_add(at, name, level, tier):
    form_input = next(t for t in at.text_input if t.label == "Add a document type")
    form_input.set_value(name)
    strict = [s for s in at.selectbox if s.label == "Strictness" and s.options and "Strict" in s.options[0]]
    tiers = [s for s in at.selectbox if s.label == "Tier"]
    strict[-1].set_value(level)          # the add form's selects are the last ones on the tab
    tiers[-1].set_value(tier)
    next(b for b in at.button if b.label == "Add").click().run()
    assert not at.exception


def test_naa_walkthrough_in_the_studio(at, db_path):
    pol = policymod.load()
    assert pol.sector == "commonwealth-agency"
    go(at, "Information manager")
    # step 2: add two NAA-facing types, then save
    _setup_form_add(at, "Ministerial brief", "standard", "T2")
    _setup_form_add(at, "Agent action record", "strict", "T3")
    button(at, "Save policy").click().run()
    assert not at.exception
    saved = {d.id: d for d in policymod.load().document_types}
    assert policymod.level_of(saved["ministerial-brief"]) == "standard" and saved["ministerial-brief"].default_tier == "T2"
    assert policymod.level_of(saved["agent-action-record"]) == "strict" and saved["agent-action-record"].default_tier == "T3"

    # check the waivers briefing as a ministerial brief: same bar as a briefing, so it is blocked the same way
    go(at, "Records")
    start_check(at)
    select(at, "Document", BRIEFING)
    at.run()
    select(at, "Document type", "ministerial-brief")
    at.run()
    button(at, "Run check").click().run()
    assert not at.exception
    assert button(at, "Issue passport").disabled
    assert any("Blocked by policy" in e.value for e in at.error)


def test_changing_strictness_in_one_click(at):
    go(at, "Information manager")
    lvl = next(s for s in at.selectbox if s.label == "Strictness" and s.value == "custom")   # correspondence
    lvl.set_value("light").run()
    button(at, "Save policy").click().run()
    assert not at.exception
    corr = next(d for d in policymod.load().document_types if d.id == "correspondence")
    assert policymod.level_of(corr) == "light"


# ---------- an NAA-facing document over the API ----------

@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "api.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    pol = policymod.load()
    pol.document_types.append(policymod.new_type("Ministerial brief", "standard", "T2", pol.document_types))
    policymod.save(pol, by="IM")
    import api.main as main
    main = importlib.reload(main)
    yield TestClient(main.app)
    main.conn.close()


def test_naa_guidance_is_flagged_for_a_person_never_called_fabricated(client, monkeypatch):
    # live lookups on, and both indexes answer "no results": NAA's page and the Act are outside them
    monkeypatch.setenv("RECORDCHECK_ONLINE", "true")
    monkeypatch.setattr(cit, "_crossref", lambda c: [])
    monkeypatch.setattr(cit, "_openalex", lambda c: [])
    r = client.post("/check", json={**NAA_BRIEF, "document_type": "ministerial-brief"}).json()
    assert [c["status"] for c in r["citations"]] == ["not_checked", "found"]   # [2] the Archives Act, on the register
    assert "Government guidance" in r["citations"][0]["note"]
    gate = r["gate"]
    assert gate["status"] != "ready"
    assert not any("not found" in x["text"] for x in gate["reasons"])          # never "possibly fabricated"
    assert any("could not be checked automatically" in x["text"] for x in gate["reasons"])


def test_api_policy_levels_for_the_web_picker(client):
    j = client.get("/policy/levels").json()
    assert [lv["id"] for lv in j["levels"]] == ["strict", "standard", "light"]
    assert all(lv["summary"] and lv["use_for"] for lv in j["levels"])
    by_id = {t["id"]: t["level"] for t in j["document_types"]}
    assert by_id["decision-letter"] == "strict" and by_id["briefing"] == "standard" and by_id["case-note"] == "light"
    assert by_id["correspondence"] == "custom" and by_id["ministerial-brief"] == "standard"   # added in the fixture
