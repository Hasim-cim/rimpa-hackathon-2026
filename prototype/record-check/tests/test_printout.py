"""Printed passport (B3): one page, offline, for seed and newly issued passports, and over the API."""
from __future__ import annotations

import importlib

import pytest

from recordcheck import db, passport, printout


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "p.sqlite"))
    c = db.open_db()
    yield c
    c.close()


def _pages(pdf: bytes) -> int:
    return pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages")


def test_every_seed_passport_prints_on_one_page(conn):
    chain = passport.verify_chain(conn)
    for p in db.get_passports(conn):
        pdf = printout.passport_pdf(p, chain)
        assert pdf.startswith(b"%PDF") and _pages(pdf) == 1, p.record.id


def test_long_text_and_unicode_still_fit_one_page(conn):
    p = db.get_passports(conn)[-1]
    p = p.model_copy(deep=True)
    p.process.prompt = "Summarise → check ≤ 21 days “quoted” — " * 40
    p.business.tier_reason = "Default T1; used in a decision → T2. " * 20
    assert _pages(printout.passport_pdf(p)) == 1


def test_filename_has_no_slash():
    assert printout.filename(type("P", (), {"record": type("R", (), {"id": "REC-2026/000001"})})()) == \
        "passport-REC-2026-000001.pdf"


def test_api_serves_the_pdf_and_still_serves_json(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("RECORDCHECK_DB", str(tmp_path / "api.sqlite"))
    monkeypatch.setenv("RECORDCHECK_POLICY", str(tmp_path / "policy.json"))
    import api.main as main
    main = importlib.reload(main)
    client = TestClient(main.app)
    rid = db.get_passports(main.conn)[0].record.id
    r = client.get(f"/passport/{rid}.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert client.get(f"/passport/{rid}").json()["record"]["id"] == rid
    assert client.get("/passport/REC-9999/1.pdf").status_code == 404
    main.conn.close()
