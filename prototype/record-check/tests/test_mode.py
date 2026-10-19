"""Deployment mode (V3b 2a): the AI splits claims only in demo mode and only on trial documents; pasted text never
reaches the model. The mode comes from the environment, never from the caller. Offline: the model is mocked."""
from __future__ import annotations

import importlib

import pytest

from recordcheck import llm


@pytest.fixture
def client_in(tmp_path, monkeypatch):
    def make(mode):
        from fastapi.testclient import TestClient
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "m.sqlite"))
        monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "p.json"))
        if mode is None:
            monkeypatch.delenv("RECORDCHECK_MODE", raising=False)
        else:
            monkeypatch.setenv("RECORDCHECK_MODE", mode)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")              # the model would be available...
        calls = []
        monkeypatch.setattr(llm, "split_claims", lambda t: calls.append(t) or [t])   # ...and is recorded, not called
        import api.main as main
        main = importlib.reload(main)
        return TestClient(main.app), calls, main
    return make


PASTED = {"title": "t", "body": "The applicant lives alone.", "case_id": "2026/0412"}


@pytest.mark.parametrize("mode", ["app", "demo", None])
def test_pasted_text_never_reaches_the_model(client_in, mode):
    client, calls, main = client_in(mode)
    r = client.post("/check", json=PASTED)
    assert r.status_code == 200 and r.json()["assessment"]["method"] == "sentence-split" and calls == []
    main.conn.close()


def test_demo_mode_uses_the_model_on_a_trial_document(client_in):
    client, calls, main = client_in("demo")
    r = client.post("/check", json={"document_id": "DOC-2026/0587-eligibility"})   # a trial document without seed claims
    assert r.status_code == 200 and len(calls) == 1 and r.json()["assessment"]["method"].startswith("llm:")
    main.conn.close()


def test_app_mode_never_uses_the_model_and_is_the_default(client_in):
    for mode in ("app", None):
        client, calls, main = client_in(mode)
        r = client.post("/check", json={"document_id": "DOC-2026/0587-eligibility"})
        assert r.json()["assessment"]["method"] == "sentence-split" and calls == []
        assert client.get("/health").json()["mode"] == "app"
        main.conn.close()


def test_a_caller_cannot_switch_the_mode(client_in):
    client, calls, main = client_in("app")
    r = client.post("/check", json={**PASTED, "mode": "demo", "use_llm": True})   # extra fields are ignored
    assert r.status_code == 200 and calls == [] and client.get("/health").json()["ai_for_pasted_text"] is False
    main.conn.close()
