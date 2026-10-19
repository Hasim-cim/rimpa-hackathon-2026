"""One-page printed passport (PDF) for an AI-assisted record. Pure function: passport in, bytes out. No LLM."""

from __future__ import annotations

from fpdf import FPDF

from .models import ChainReport, Passport

# the PDF core fonts are Latin-1; map the few characters our reasons use, then drop anything else
_PLAIN = str.maketrans({"→": "->", "≤": "<=", "≥": ">=", "—": "-", "–": "-", "‘": "'", "’": "'", "“": '"',
                        "”": '"', "…": "...", "∞": "no limit"})
_GATE = {"ready": "Ready to file", "attention": "Needs attention", "blocked": "Blocked"}
_TIER = {"T0": "T0 transitory", "T1": "T1 retained output", "T2": "T2 decision-informing", "T3": "T3 agentic action"}


def _t(v) -> str:
    s = "" if v is None else str(v)
    return s.translate(_PLAIN).encode("latin-1", "replace").decode("latin-1")


def _clip(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 3] + "..."


def _counts(d: dict[str, int]) -> str:
    return ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in d.items() if v) or "no check recorded"


class _Doc(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(110)
        self.cell(0, 5, _t("Record Check prototype. Example data: every case, person and record is invented."),
                  align="C")


def passport_pdf(p: Passport, chain: ChainReport | None = None) -> bytes:
    pdf = _Doc(format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, _t("Record passport"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80)
    pdf.multi_cell(0, 5, _t(f"{p.record.title}  |  {p.record.id}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(1)

    # headline strip: tier, gate, model returned
    b = p.business
    strip = [("Tier", _TIER.get(b.tier, b.tier)),
             ("Filing gate", _GATE.get(b.gate, "not recorded") if b.gate else "not recorded"),
             ("Model returned", p.agent.model_returned)]
    pdf.set_fill_color(238, 242, 247)
    for label, value in strip:
        x, y = pdf.get_x(), pdf.get_y()
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(width / 3, 4, _t(label.upper()), fill=True, new_x="LEFT", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(width / 3, 6, _t(_clip(value, 34)), fill=True)
        pdf.set_xy(x + width / 3, y)
    pdf.ln(12)

    def group(title: str, rows: list[tuple[str, str]]) -> None:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_draw_color(180)
        pdf.cell(0, 6, _t(title), border="B", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)
        for k, v in rows:
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(90)
            pdf.cell(42, 4.4, _t(k))
            pdf.set_text_color(0)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.multi_cell(width - 42, 4.4, _t(v), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)

    r, a, pr, ig, pd = p.record, p.agent, p.process, p.integrity, p.paradata
    group("1  Record", [("Record id", r.id), ("Created", r.created.isoformat(sep=" ")),
                        ("AI generated", "yes, in part" if r.ai_generated else "no"),
                        ("Final document", r.final_document or "none"), ("Content hash", r.content_hash)])
    group("2  Agent", [("Person", a.person), ("AI system", a.ai_system), ("Model requested", a.model_requested),
                       ("Model returned", a.model_returned), ("Provider", a.provider)])
    group("3  Business", [("Function", b.function or "not stated"), ("Tier", _TIER.get(b.tier, b.tier)),
                          ("Why this tier", _clip(b.tier_reason, 220)), ("Disposal", b.disposal),
                          ("Document type", b.document_type or "not stated"),
                          ("Filing gate at issue", _GATE.get(b.gate, "not recorded") if b.gate else "not recorded")])
    tools = "; ".join(f"{t.name}{' (side effect)' if t.side_effect else ''}" for t in pr.tool_calls) or "none"
    group("4  Process", [("Prompt", _clip(pr.prompt, 260)),
                         ("Source records", ", ".join(pr.source_record_ids) or "none"),
                         ("Evidence", _counts(pr.evidence_summary)), ("Citations", _counts(pr.citation_summary)),
                         ("Tool calls", tools)])
    rv = p.review
    group("5  Review", [("Reviewer", rv.reviewer), ("Decision", rv.decision.replace("_", " ")),
                        ("Reviewed", rv.reviewed_at.isoformat(sep=" ")), ("Note", rv.note or "none")]
          if rv else [("Reviewer", "no review recorded")])
    chain_line = "not checked at print time"
    if chain is not None:
        chain_line = f"verified at print time ({chain.checked} passports)" if chain.ok else \
                     f"BROKEN at {chain.first_break}: {chain.detail}"
    group("6  Integrity and paradata", [("Hash", f"{ig.algorithm} {ig.hash}"), ("Previous hash", ig.prev_hash or "none (first)"),
                                        ("Chain", chain_line), ("Policy", pd.policy_version),
                                        ("Policy hash", pd.policy_hash or "not recorded"),
                                        ("Use register", pd.use_register_id)])
    return bytes(pdf.output())


def filename(p: Passport) -> str:
    return "passport-" + p.record.id.replace("/", "-") + ".pdf"
