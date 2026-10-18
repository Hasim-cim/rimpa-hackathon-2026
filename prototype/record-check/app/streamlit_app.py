"""Record Check console. Run: uv run streamlit run app/streamlit_app.py"""

from __future__ import annotations

import html
import os
import sqlite3
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from recordcheck import citations as cit
from recordcheck import db, disposal, evidence, gate as gatemod, llm, passport, recall
from recordcheck import policy as policymod
from recordcheck.hashing import short
from recordcheck.models import AIEvent, DocumentType, Passport, Policy, QualityBar, Review

DEFAULT_DOC = "DOC-2026/0412-summary"
FALLBACK_MODEL = "northstar-8-2026-09-15"
FALLBACK_PROVIDER = "Northstar AI (fictional vendor)"

CITE_COLOURS = {"found": ("#d1f0dc", "#14532d"), "mismatch": ("#fde8b8", "#7a4a00"),
                "not_found": ("#f8d0d0", "#7f1d1d"), "not_checked": ("#e5e7eb", "#374151")}
WEIGHT_COLOURS = {"supported": ("#d1f0dc", "#14532d"), "weak": ("#fde8b8", "#7a4a00"),
                  "unsupported": ("#f8d0d0", "#7f1d1d"), "contradicted": ("#4b5563", "#ffffff")}
DISPOSAL_COLOURS = {"due": ("#fde8b8", "#7a4a00"), "on hold": ("#e5e7eb", "#374151")}
TIER_COLOURS = {"T0": ("#e5e7eb", "#374151"), "T1": ("#d6e6fb", "#1e3a8a"),
                "T2": ("#fde8b8", "#7a4a00"), "T3": ("#f8d0d0", "#7f1d1d")}

CSS = """
<style>
.rc-pill {display:inline-block; padding:1px 10px; border-radius:999px; font-size:0.82rem; font-weight:600; white-space:nowrap;}
.rc-sent {padding:2px 4px; border-radius:4px; line-height:2.0; box-decoration-break:clone; -webkit-box-decoration-break:clone;}
.rc-sup {font-size:0.62rem; font-weight:700; letter-spacing:0.04em; margin-left:2px; color:#374151;}
.rc-doc {font-size:1.02rem; color:#111827;}
.rc-kv {margin:0 0 4px 0; font-size:0.92rem;}
.rc-kv span.k {color:#6b7280;}
</style>
"""


# ---------- helpers ----------

@st.cache_resource
def get_conn() -> sqlite3.Connection:
    # db.open_db() builds and seeds the DB. Its connection is not usable across Streamlit's script threads,
    # so we reopen the same file with check_same_thread=False.
    db.open_db().close()
    conn = sqlite3.connect(db.db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_policy() -> Policy:
    """The saved (active) policy, loaded once per session. Setup edits a draft; only Save changes this."""
    if "policy" not in st.session_state:
        st.session_state["policy"] = policymod.load()
    return st.session_state["policy"]


def get_rules():
    return get_policy().tier_rules


GATE_COLOURS = {"ready": ("#d1f0dc", "#14532d", "Ready to file"), "attention": ("#fde8b8", "#7a4a00", "Needs attention"),
                "blocked": ("#f8d0d0", "#7f1d1d", "Blocked")}
TIERS = ["T0", "T1", "T2", "T3"]
DOC_TYPE_HINTS = (("summary", "decision-letter"), ("briefing", "briefing"), ("agent-note", "case-note"), ("eligibility", "case-note"))


def default_type_id(pol: Policy, doc) -> str:
    key = f"{doc.id} {doc.title}".lower()
    ids = [d.id for d in pol.document_types]
    for needle, tid in DOC_TYPE_HINTS:
        if needle in key and tid in ids:
            return tid
    return ids[0]


def gate_banner(result) -> None:
    bg, fg, label = GATE_COLOURS[result.status]
    items = "".join(f"<li>{esc(r.text)}</li>" for r in result.reasons)
    st.markdown(f'<div style="margin:8px 0"><span style="display:inline-block;padding:6px 22px;border-radius:999px;'
                f'font-size:1.4rem;font-weight:700;background:{bg};color:{fg}" data-testid="gate-pill">{label}</span>'
                f'<ul style="margin-top:8px">{items}</ul></div>', unsafe_allow_html=True)


def pill(text: str, colours: dict, key: str) -> str:
    bg, fg = colours.get(key, ("#e5e7eb", "#374151"))
    return f'<span class="rc-pill" style="background:{bg};color:{fg}">{html.escape(text)}</span>'


def kv(k: str, v: str) -> str:
    return f'<p class="rc-kv"><span class="k">{html.escape(k)}</span><br>{v}</p>'


def esc(v) -> str:
    return html.escape(str(v))


def online_on() -> bool:
    return os.environ.get("RECORDCHECK_ONLINE", "").lower() in ("1", "true", "yes", "on")


# ---------- Check ----------

def render_sentences(assessment) -> str:
    verdicts = {v.claim_id: v for v in assessment.verdicts}
    parts = []
    for c in sorted(assessment.claims, key=lambda c: c.position):
        v = verdicts.get(c.id)
        bg, fg = WEIGHT_COLOURS[v.weight] if v else ("#e5e7eb", "#374151")
        tip = esc(f"{v.weight}: {v.reason}") if v else ""
        parts.append(f'<span class="rc-sent" title="{tip}" style="background:{bg};color:{fg}">{esc(c.text)}'
                     f'<sup class="rc-sup" style="color:{fg}">{c.author.upper()}</sup></span>')
    return '<div class="rc-doc">' + " ".join(parts) + "</div>"


def tab_check(conn) -> None:
    docs = db.get_documents(conn)
    ids = [d.id for d in docs]
    doc_id = st.selectbox("Document", ids, index=ids.index(DEFAULT_DOC) if DEFAULT_DOC in ids else 0,
                          format_func=lambda i: f"{i}  {next(d.title for d in docs if d.id == i)}")
    doc = next(d for d in docs if d.id == doc_id)
    st.subheader(doc.title)
    st.caption(f"Case {doc.case_id or 'none'}. Draft as submitted:")
    st.write(doc.body.replace("$", "\\$"))  # bare $ would render as maths
    with st.expander("References as submitted"):
        st.text(doc.references)

    pol = get_policy()
    type_ids = [d.id for d in pol.document_types]
    dtype_id = st.selectbox("Document type", type_ids, index=type_ids.index(default_type_id(pol, doc)),
                            format_func=lambda i: policymod.doc_type(pol, i).name, key=f"dtype_{doc.id}_{pol.version}")
    dtype = policymod.doc_type(pol, dtype_id)

    if st.button("Run check", type="primary"):
        results = cit.check_document(doc.references, conn=conn)
        assessment = evidence.assess(doc, conn, results, policy=pol)
        st.session_state["check"] = {"doc_id": doc.id, "citations": results, "assessment": assessment,
                                     "policy_version": pol.version}

    state = st.session_state.get("check")
    if not state or state["doc_id"] != doc.id:
        st.info("Run the check to look up each reference and trace each sentence to authoritative records.")
        return
    if state.get("policy_version") != pol.version:
        st.info("The policy changed since this check ran. Run the check again so it uses the current policy.")
        return
    results, assessment = state["citations"], state["assessment"]

    # summary row
    csum = cit.summary(results)
    esum = evidence.summary(assessment.verdicts)
    cols = st.columns(8)
    for col, (label, val) in zip(cols, [*(("Citations " + k.replace("_", " "), v) for k, v in csum.items()),
                                        *((k.capitalize(), v) for k, v in esum.items())]):
        col.metric(label, val)

    st.markdown(f"#### Filing gate: {esc(dtype.name)}", unsafe_allow_html=True)
    gate_banner(gatemod.evaluate(assessment, results, None, dtype, dtype.default_tier))
    st.caption(f"Bar set by the information manager in policy v{pol.version}. Change it in the Setup tab.")

    st.markdown("#### Citations")
    for r in results:
        c1, c2 = st.columns([1, 6])
        c1.markdown(pill(r.status.replace("_", " "), CITE_COLOURS, r.status), unsafe_allow_html=True)
        c2.markdown(f"**[{r.citation.n}]** {esc(r.citation.raw)}<br><span style='color:#6b7280;font-size:0.88rem'>"
                    f"{esc(r.note)}</span>", unsafe_allow_html=True)

    st.markdown("#### The draft, sentence by sentence")
    st.markdown(render_sentences(assessment), unsafe_allow_html=True)
    leg = " ".join(pill(k, WEIGHT_COLOURS, k) for k in WEIGHT_COLOURS)
    st.markdown(f"<p style='margin-top:8px;font-size:0.85rem'>{leg} &nbsp; AI / HUMAN marks who wrote the sentence. "
                f"A weight says whether authoritative records support it, whoever wrote it.</p>", unsafe_allow_html=True)

    st.markdown("#### Trace")
    vmap = {v.claim_id: v for v in assessment.verdicts}
    claims = sorted(assessment.claims, key=lambda c: c.position)
    cid = st.selectbox("Claim", [c.id for c in claims],
                       format_func=lambda i: next(f"{c.position}. {c.text[:90]}" for c in claims if c.id == i))
    claim, v = next(c for c in claims if c.id == cid), vmap[cid]
    st.markdown(pill(v.weight, WEIGHT_COLOURS, v.weight) + f" &nbsp; Author: **{claim.author.upper()}**",
                unsafe_allow_html=True)
    st.write(claim.text)
    st.markdown(f"**Reason.** {v.reason}")
    if v.links:
        rows = []
        for l in v.links:
            rec = db.get_record(conn, l.record_id)
            rows.append({"Record id": l.record_id, "Title": rec.title if rec else "",
                         "System": rec.system if rec else "", "Status": rec.status if rec else "",
                         "Rule": l.rule, "Note": l.note})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    else:
        st.caption("No authoritative record is linked to this claim.")

    file_section(conn, doc, results, assessment, dtype)


def real_model() -> tuple[str, str, str]:
    """(model_requested, model_returned, provider)"""
    if llm.available():
        try:
            r = llm.complete("Reply with the single word: ready.")
            return r.model_requested, r.model_returned, "Anthropic"
        except Exception as e:  # network or key problems fall back to the example model
            st.warning(f"LLM call failed ({type(e).__name__}); using the example model id.")
    return FALLBACK_MODEL, FALLBACK_MODEL, FALLBACK_PROVIDER


def file_section(conn, doc, results, assessment, dtype: DocumentType) -> None:
    st.markdown("#### File as record")
    c1, c2 = st.columns(2)
    reviewer = c1.text_input("Reviewer name", "B. Team Leader")
    decision = c2.selectbox("Decision", ["approved", "approved_with_edits", "rejected"])
    flag = st.checkbox("Output informs a decision about a person, case or money", value=True)
    now = datetime.now(timezone.utc)
    review = Review(reviewer=reviewer.strip(), decision=decision, reviewed_at=now) if reviewer.strip() else None
    rules = get_rules()
    # the type's default tier is the floor; the escalation rules can only raise it
    probe = AIEvent(id="probe", app_id="agency-assistant", user="A. Caseworker", created=now, prompt="", output="",
                    model_requested="", model_returned="", provider="", exported_to_document=doc.id, decision_flag=flag)
    tier = max(dtype.default_tier, passport.classify(probe, rules), key=lambda t: passport.TIER_ORDER[t])
    result = gatemod.evaluate(assessment, results, review, dtype, tier)
    st.markdown(f"Gate with this review (tier {tier}):")
    gate_banner(result)
    blocked = result.status == "blocked"
    if blocked:
        st.error("Blocked by policy: fix the document or ask the information manager to change the bar.")
    if st.button("Issue passport", disabled=blocked):
        linked = sorted({l.record_id for v in assessment.verdicts for l in v.links})
        requested, returned, provider = real_model()
        event = AIEvent(
            id=f"EVT-{now:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:4]}", app_id="agency-assistant", user="A. Caseworker",
            created=now, prompt="Summarise the hardship policy for case 2026/0412 and cite authorities",
            output=doc.body, model_requested=requested, model_returned=returned, provider=provider,
            source_record_ids=linked, exported_to_document=doc.id, decision_flag=flag,
            function="Debt waiver assessment")
        p = passport.build(event, tier=tier, assessment=assessment, citations=results, review=review,
                           conn=conn, rules=rules, document_type=dtype.id, gate=result.status, policy=pol)
        st.session_state["last_record"] = p.record.id
        st.session_state["issued_msg"] = f"Passport issued: {p.record.id} ({tier})"
    if st.session_state.get("issued_msg"):
        st.success(st.session_state["issued_msg"] + ". Open the Passport tab to see it.")


# ---------- Setup ----------

def _draft() -> Policy:
    if "draft" not in st.session_state:
        st.session_state["draft"] = get_policy().model_copy(deep=True)
        st.session_state["draft_gen"] = st.session_state.get("draft_gen", 0) + 1
    return st.session_state["draft"]


def _set_draft(pol: Policy) -> None:
    st.session_state["draft"] = pol.model_copy(deep=True)
    st.session_state["draft_gen"] = st.session_state.get("draft_gen", 0) + 1


def _use_suggestion() -> None:
    sug = st.session_state.get("suggestion")
    if sug:
        st.session_state["setup_org"] = sug.organisation
        st.session_state["setup_preset"] = sug.preset.id


def tab_setup(conn) -> None:
    pol = get_policy()
    draft = _draft()
    gen = st.session_state["draft_gen"]
    presets = policymod.load_presets()
    pnames = {p.id: p.name for p in presets}
    st.caption("The information manager sets what good looks like once. The checks and the filing gate read this policy. "
               "An AI model may suggest a starting profile, but never sets a threshold, tier or gate.")

    # a. organisation
    st.markdown("#### Your organisation")
    st.session_state.setdefault("setup_org", pol.organisation)
    st.session_state.setdefault("setup_preset", pol.sector if pol.sector in pnames else presets[0].id)
    st.text_input("Organisation name", key="setup_org")
    st.selectbox("Sector preset", list(pnames), format_func=pnames.get, key="setup_preset")
    st.text_area("Describe your organisation in a sentence", key="setup_desc",
                 placeholder="e.g. A regional hospital using an AI scribe for clinic notes")
    if st.button("Suggest a profile"):
        if not llm.available():
            st.session_state["suggestion"] = None
            st.info("Suggestions need the LLM; pick a preset instead.")
        else:
            with st.spinner("Asking the model for a starting point..."):
                st.session_state["suggestion"] = policymod.suggest(st.session_state.get("setup_desc", ""))
            if st.session_state["suggestion"] is None:
                st.warning("No suggestion this time; pick a preset instead.")
    sug = st.session_state.get("suggestion")
    if sug:
        st.info(f"Suggested: **{sug.preset.name}** for {sug.organisation}. {sug.preset.description} "
                "This is a starting point; you confirm every field below.")
        st.button("Use this suggestion", on_click=_use_suggestion)
    replace_ok = st.checkbox("Replace my current policy", key="setup_replace")
    if st.button("Start from this preset", disabled=not replace_ok):
        new = policymod.from_preset(policymod.get_preset(st.session_state["setup_preset"]),
                                    st.session_state["setup_org"].strip() or policymod.DEFAULT_ORG,
                                    by=st.session_state.get("setup_by", "Information manager"))
        new.version = pol.version  # version numbers keep counting up across presets
        saved = policymod.save(new, by=st.session_state.get("setup_by", "Information manager"), conn=conn)
        st.session_state["policy"] = saved
        _set_draft(saved)
        st.session_state["setup_msg"] = f"Policy v{saved.version} saved from the {saved.sector_name} preset."
        st.rerun()

    # b. document types
    st.markdown("#### Document types and what good looks like")
    st.caption("Each type has a quality bar. Going over a 'blocked' limit stops filing; going over an 'attention' limit "
               "asks for a closer look.")
    for d in list(draft.document_types):
        k = f"{gen}-{d.id}"
        with st.expander(f"{d.name}  ({d.id}, default {d.default_tier})"):
            d.name = st.text_input("Name", d.name, key=f"{k}-name")
            d.description = st.text_input("Description", d.description, key=f"{k}-desc")
            d.default_tier = st.selectbox("Default tier", TIERS, index=TIERS.index(d.default_tier), key=f"{k}-tier")
            d.checks = st.multiselect("Checks that run", ["citations", "evidence"], default=d.checks, key=f"{k}-checks")
            q = d.quality
            c1, c2 = st.columns(2)
            q.max_unsupported = int(c1.number_input("Unsupported claims allowed (more = blocked)", 0, 100, q.max_unsupported, key=f"{k}-mu"))
            q.max_contradicted = int(c2.number_input("Contradicted claims allowed (more = blocked)", 0, 100, q.max_contradicted, key=f"{k}-mc"))
            unl_weak = c1.checkbox("Unlimited weak claims", value=q.max_weak is None, key=f"{k}-uw")
            q.max_weak = None if unl_weak else int(c1.number_input(
                "Weak claims allowed (more = needs attention)", 0, 100, q.max_weak if q.max_weak is not None else 0, key=f"{k}-mw"))
            unl_share = c2.checkbox("No minimum supported share", value=q.min_supported_share is None, key=f"{k}-us")
            q.min_supported_share = None if unl_share else float(c2.slider(
                "Minimum share of supported claims", 0.0, 1.0, q.min_supported_share if q.min_supported_share is not None else 0.6,
                0.05, key=f"{k}-ms"))
            q.citations_not_found_blocks = st.checkbox("A citation that cannot be found blocks filing", q.citations_not_found_blocks, key=f"{k}-nf")
            q.citations_mismatch_attention = st.checkbox("A citation with mismatched details needs attention", q.citations_mismatch_attention, key=f"{k}-mm")
            q.require_reviewer = st.checkbox("T2 and T3 need a named reviewer", q.require_reviewer, key=f"{k}-rr")
            if st.button("Remove this document type", key=f"{k}-rm", disabled=len(draft.document_types) <= 1):
                draft.document_types = [x for x in draft.document_types if x.id != d.id]
                st.session_state["draft_gen"] += 1
                st.rerun()
    with st.form(f"add_type_{gen}", clear_on_submit=True):
        st.markdown("**Add document type**")
        a1, a2, a3 = st.columns(3)
        nid = a1.text_input("Id (e.g. ministerial-reply)")
        nname = a2.text_input("Name")
        ntier = a3.selectbox("Default tier", TIERS, index=1)
        if st.form_submit_button("Add document type"):
            nid = nid.strip().lower().replace(" ", "-")
            if not nid or not nname.strip():
                st.warning("Give the new type an id and a name.")
            elif any(x.id == nid for x in draft.document_types):
                st.warning(f"A type with id {nid} already exists.")
            else:
                draft.document_types.append(DocumentType(id=nid, name=nname.strip(), default_tier=ntier, quality=QualityBar()))
                st.session_state["draft_gen"] += 1
                st.rerun()

    # c. authoritative systems
    st.markdown("#### Authoritative systems")
    systems = sorted({r.system for r in db.get_records(conn)} | set(draft.authoritative_systems))
    draft.authoritative_systems = st.multiselect(
        "Systems whose records count as evidence", systems, default=[x for x in draft.authoritative_systems if x in systems],
        key=f"{gen}-systems")
    st.caption("Anything not selected is treated as non-authoritative: records from it can never make a claim 'supported'. "
               "A saved web page can never be evidence unless you say so.")

    # d. apps and tiers
    st.markdown("#### Apps and tiers")
    tr = draft.tier_rules
    for app_id in list(tr.app_defaults):
        tr.app_defaults[app_id] = st.selectbox(f"{tr.app_names.get(app_id, app_id)}: default tier", TIERS,
                                               index=TIERS.index(tr.app_defaults[app_id]), key=f"{gen}-app-{app_id}")
    labels = {"exported_to_document": "Output filed into a document", "decision_flag": "Output informs a decision",
              "side_effect_tool_call": "Agent took an action with side effects"}
    st.markdown("Escalations (read-only here): " + "; ".join(f"{labels.get(k, k)} raises to at least {v}" for k, v in tr.escalations.items()))
    tr.retention_days["T0"] = int(st.number_input("T0 log retention (days)", 1, 3650, tr.retention_days.get("T0", 90), key=f"{gen}-ret"))

    # e. guidance
    st.markdown("#### Guidance this policy cites")
    g = st.text_area("One per line", "\n".join(draft.guidance), key=f"{gen}-guid")
    draft.guidance = [x.strip() for x in g.splitlines() if x.strip()]

    # f. footer
    st.divider()
    by = st.text_input("Name of the person saving", "Information manager", key="setup_by")
    draft.organisation = st.session_state["setup_org"].strip() or draft.organisation
    if st.button("Save policy", type="primary"):
        saved = policymod.save(draft.model_copy(deep=True), by=by.strip() or "Information manager", conn=conn)
        st.session_state["policy"] = saved
        _set_draft(saved)
        st.session_state["setup_msg"] = f"Policy v{saved.version} saved"
        st.rerun()
    if st.session_state.get("setup_msg"):
        st.success(st.session_state["setup_msg"])
    reset_ok = st.checkbox("Confirm: discard my policy and go back to the preset defaults", key="setup_reset_ok")
    if st.button("Reset to preset defaults", disabled=not reset_ok):
        base = policymod.from_preset(policymod.get_preset(pol.sector if pol.sector in pnames else policymod.DEFAULT_PRESET),
                                     pol.organisation, by=by.strip() or "Information manager")
        base.version = pol.version  # keep counting up so the history of versions stays monotonic
        saved = policymod.save(base, by=by.strip() or "Information manager", conn=conn)
        st.session_state["policy"] = saved
        _set_draft(saved)
        st.session_state["setup_msg"] = f"Policy v{saved.version} saved (reset to {saved.sector_name} defaults)"
        st.rerun()


# ---------- Passport ----------

def tab_passport(conn) -> None:
    ps = db.get_passports(conn)
    ids = [p.record.id for p in ps][::-1]  # latest first
    if not ids:
        st.info("No passports yet.")
        return
    default = st.session_state.get("last_record")
    sel = st.selectbox("Record", ids, index=ids.index(default) if default in ids else 0)
    p = db.get_passport(conn, sel)

    rep = passport.verify_chain(conn)
    if rep.ok:
        st.caption(f"Chain verified: {rep.detail}")
    else:
        st.error(f"Chain broken at {rep.first_break}: {rep.detail}")

    t = p.business.tier
    st.markdown(f"### {esc(p.record.title)} &nbsp; " + pill(t, TIER_COLOURS, t), unsafe_allow_html=True)

    def card(col, title, body):
        with col.container(border=True):
            st.markdown(f"**{title}**")
            st.markdown(body, unsafe_allow_html=True)

    r, a, b, pr, rv, ig, pd_ = p.record, p.agent, p.business, p.process, p.review, p.integrity, p.paradata
    row1 = st.columns(3)
    row2 = st.columns(3)
    card(row1[0], "Record",
         kv("Record id", esc(r.id)) + kv("Title", esc(r.title)) + kv("Created", esc(r.created.isoformat(sep=" ")))
         + kv("AI generated", "yes, in part" if r.ai_generated else "no")
         + kv("Final document", esc(r.final_document or "none")) + kv("Content hash", esc(short(r.content_hash))))
    card(row1[1], "Agent",
         kv("Person", esc(a.person)) + kv("AI system", esc(a.ai_system)) + kv("Model requested", esc(a.model_requested))
         + kv("Model returned", esc(a.model_returned)) + kv("Provider", esc(a.provider)))
    card(row1[2], "Business",
         kv("Function", esc(b.function)) + kv("Tier", pill(b.tier, TIER_COLOURS, b.tier)) + kv("Why this tier", esc(b.tier_reason))
         + (kv("Document type", esc(b.document_type)) if b.document_type else "")
         + (kv("Filing gate", pill(GATE_COLOURS[b.gate][2], {b.gate: GATE_COLOURS[b.gate][:2]}, b.gate)) if b.gate else "")
         + kv("Disposal", esc(b.disposal))
         + kv("Paradata", esc(f"{pd_.use_register_id}; {pd_.policy_version}"
                              + (f"; impact assessment {pd_.impact_assessment_ref}" if pd_.impact_assessment_ref else ""))))
    cs = " ".join(f"{k.replace('_', ' ')} {v}" for k, v in pr.citation_summary.items())
    es = " ".join(f"{k} {v}" for k, v in pr.evidence_summary.items())
    card(row2[0], "Process",
         kv("Prompt", esc(pr.prompt)) + kv("Source records", esc(", ".join(pr.source_record_ids) or "none"))
         + kv("Citation checks", esc(cs)) + kv("Evidence", esc(es))
         + kv("Tool calls", esc(", ".join(tc.name + (" (side effect)" if tc.side_effect else "") for tc in pr.tool_calls) or "none")))
    if rv:
        rbody = (kv("Reviewer", esc(rv.reviewer)) + kv("Decision", esc(rv.decision.replace("_", " ")))
                 + kv("Reviewed", esc(rv.reviewed_at.isoformat(sep=" "))) + (kv("Note", esc(rv.note)) if rv.note else ""))
    else:
        rbody = kv("Reviewer", "none recorded")
    card(row2[1], "Review", rbody)
    card(row2[2], "Integrity",
         kv("Hash", f"<code>{esc(short(ig.hash))}</code>") + kv("Previous hash", f"<code>{esc(short(ig.prev_hash))}</code>")
         + kv("Algorithm", esc(ig.algorithm)) + kv("Version", esc(ig.version))
         + (kv("Corrects", esc(ig.corrects)) if ig.corrects else ""))
    with row2[2].expander("Full hashes"):
        st.code(f"hash:      {ig.hash}\nprev_hash: {ig.prev_hash or '-'}", language=None)

    st.download_button("Download passport JSON", p.model_dump_json(indent=2),
                       file_name=f"{r.id.replace('/', '-')}.json", mime="application/json")


# ---------- Recall ----------

def tab_recall(conn) -> None:
    reg = db.get_model_registry(conn)
    st.markdown("#### Model registry")
    st.dataframe(pd.DataFrame([{"Model": e.model_id, "Provider": e.provider, "Status": e.status,
                                "Effective from": e.effective_from.isoformat() if e.effective_from else "",
                                "Reason": e.reason} for e in reg]), hide_index=True, width='stretch')

    ids = [e.model_id for e in reg]
    st.markdown("#### Mark a model")
    with st.form("mark_model"):
        c1, c2, c3 = st.columns(3)
        model_id = c1.selectbox("Model", ids, index=ids.index("northstar-7-2026-03-01") if "northstar-7-2026-03-01" in ids else 0)
        status = c2.selectbox("Status", ["faulty", "withdrawn"])
        eff = c3.date_input("Effective from", value=date(2026, 3, 1))
        reason = st.text_input("Reason", "Vendor bulletin: fabricated citations")
        if st.form_submit_button("Mark model"):
            recall.mark_model(conn, model_id, status, eff, reason, by="Information manager")
            st.session_state["recall_model"] = model_id
            st.rerun()

    model_id = st.session_state.get("recall_model", model_id)
    res = recall.recall(conn, model_id)
    st.markdown(f"#### Recall: {esc(model_id)}", unsafe_allow_html=True)
    e = res.entry
    st.caption(f"Status {e.status}"
               + (f", effective from {e.effective_from}" if e.effective_from else "")
               + (f". {e.reason}" if e.reason else ""))
    n = res.counts
    m = st.columns(4)
    m[0].metric("Records affected", n["T1"] + n["T2"] + n["T3"])
    m[1].metric("T2 decision-informing", n["T2"])
    m[2].metric("T1", n["T1"])
    m[3].metric("T3", n["T3"])
    if res.items:
        rows = "".join(
            f"<tr><td>{esc(i.record_id)}</td><td>{pill(i.tier, TIER_COLOURS, i.tier)}</td><td>{esc(i.function)}</td>"
            f"<td>{i.created:%Y-%m-%d}</td><td>{esc(i.reviewer or 'none')}</td><td>{'yes' if i.queued else 'no'}</td></tr>"
            for i in res.items)
        st.markdown("<table style='width:100%;font-size:0.9rem'><thead><tr><th align=left>Record id</th><th align=left>Tier</th>"
                    "<th align=left>Function</th><th align=left>Created</th><th align=left>Reviewer</th><th align=left>Queued</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>", unsafe_allow_html=True)
    else:
        st.info("No T1 to T3 records were made with this model.")

    t2 = [i.record_id for i in res.items if i.tier == "T2"]
    if st.button(f"Queue T2 records for re-review ({len(t2)})", disabled=not t2):
        why = f"Model {model_id} marked {e.status}: {e.reason or 'no reason given'}"
        k = recall.queue_for_review(conn, t2, by="Information manager", reason=why)
        st.session_state["queued_msg"] = f"Queued {k} T2 records for re-review ({len(t2) - k} were already queued)."
        st.session_state["recall_model"] = model_id
        st.rerun()
    if st.session_state.get("queued_msg"):
        st.success(st.session_state["queued_msg"])

    with st.expander("Audit trail (last 20)"):
        rows = conn.execute("SELECT at, actor, action, subject, detail FROM audit_log ORDER BY id DESC LIMIT 20").fetchall()
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), hide_index=True, width='stretch')


# ---------- Disposal ----------

def tab_disposal(conn) -> None:
    rules = get_rules()
    st.markdown("T0 log entries are kept 90 days, then destroyed with approval. T1 to T3 follow their business record.")
    st.caption(f"Disposal authority: {rules.disposal_authority}")
    as_of = st.date_input("As of", value=date.today(), key="disp_as_of")
    items = disposal.due_for_disposal(conn, as_of=as_of, rules=rules)
    approvable = [i.record_id for i in items if not i.on_hold]
    m = st.columns(2)
    m[0].metric("Due for destruction", len(approvable))
    m[1].metric("On hold", len(items) - len(approvable))

    st.markdown("#### Due for disposal")
    if items:
        rows = "".join(
            f"<tr><td>{esc(i.record_id)}</td><td>{esc(i.app_id)}</td><td>{esc(i.model_returned)}</td>"
            f"<td>{i.created:%Y-%m-%d}</td><td>{i.due:%Y-%m-%d}</td>"
            f"<td title=\"{esc(i.hold_reason)}\">{pill('on hold' if i.on_hold else 'due', DISPOSAL_COLOURS, 'on hold' if i.on_hold else 'due')}</td>"
            f"<td>{esc(i.hold_reason)}</td></tr>" for i in items)
        st.markdown("<table style='width:100%;font-size:0.9rem'><thead><tr><th align=left>Record id</th><th align=left>App</th>"
                    "<th align=left>Model</th><th align=left>Created</th><th align=left>Due</th><th align=left>Status</th>"
                    f"<th align=left>Reason</th></tr></thead><tbody>{rows}</tbody></table>", unsafe_allow_html=True)
    else:
        st.info("Nothing is past its retention period on this date.")

    st.markdown("#### Approve destruction")
    chosen = st.multiselect("Records to destroy", approvable, default=approvable, key=f"disp_sel_{as_of}_{len(approvable)}")
    c1, c2 = st.columns(2)
    approver = c1.text_input("Approver name", "Information manager")
    why = c2.text_input("Reason", "Transitory AI interaction past retention; no business value")
    if st.button("Approve destruction", type="primary", disabled=not chosen):
        done = disposal.approve_disposal(conn, chosen, approved_by=approver, reason=why, rules=rules, as_of=as_of)
        rep = passport.verify_chain(conn)
        st.session_state["disposal_msg"] = (
            f"Destroyed {len(done)} records. Hash stubs retained; chain verified." if rep.ok
            else f"Destroyed {len(done)} records, but the chain check failed at {rep.first_break}.", rep.detail, rep.ok)
        st.rerun()
    msg = st.session_state.get("disposal_msg")
    if msg:
        (st.success if msg[2] else st.error)(msg[0])
        st.caption(msg[1])

    st.markdown("#### Disposal register")
    reg = disposal.register(conn)
    if reg:
        st.dataframe(pd.DataFrame([{"Record id": e.record_id, "Tier": e.tier, "Created": e.created.isoformat(sep=" "),
                                    "Destroyed": e.disposed_at.isoformat(sep=" ", timespec="seconds"),
                                    "Approved by": e.approved_by, "Authority": e.authority, "Reason": e.reason,
                                    "Hash retained": short(e.hash_retained)} for e in reg]),
                     hide_index=True, width='stretch')
    else:
        st.caption("No records destroyed yet.")
    with st.expander("Audit trail (last 10 disposal rows)"):
        rows = conn.execute("SELECT at, actor, action, subject, detail FROM audit_log WHERE action LIKE 'disposal.%' "
                            "ORDER BY id DESC LIMIT 10").fetchall()
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), hide_index=True, width='stretch')


# ---------- Register ----------

def tab_register(conn) -> None:
    pol = get_policy()
    st.markdown("#### Active policy")
    st.markdown(f"**{esc(pol.organisation)}** | {esc(pol.sector_name)} | version {esc(pol.version)} | "
                f"updated by {esc(pol.updated_by)}"
                + (f" at {pol.updated_at:%Y-%m-%d %H:%M} UTC" if pol.updated_at else ""))
    st.markdown("Guidance this policy cites: " + ("; ".join(esc(g) for g in pol.guidance) or "none"))
    st.caption("Document types: " + ", ".join(d.name for d in pol.document_types)
               + ". Authoritative systems: " + (", ".join(pol.authoritative_systems) or "none") + ".")
    st.markdown("#### Authoritative records")
    st.dataframe(pd.DataFrame([{"Id": r.id, "Title": r.title, "System": r.system, "Status": r.status,
                                "Authoritative": "yes" if r.authoritative else "no", "Created": r.created.isoformat(),
                                "Created by": r.created_by} for r in db.get_records(conn)]),
                 hide_index=True, width='stretch')
    rules = get_rules()
    st.markdown("#### Registered AI apps")
    st.dataframe(pd.DataFrame([{"App id": a, "Name": rules.app_names.get(a, a), "Default tier": t}
                               for a, t in rules.app_defaults.items()]), hide_index=True, width='stretch')
    st.markdown("#### Escalation rules")
    labels = {"exported_to_document": "Output filed into a document", "decision_flag": "Output informs a decision",
              "side_effect_tool_call": "Agent took an action with side effects"}
    st.dataframe(pd.DataFrame([{"Rule": labels.get(k, k), "Raises tier to at least": v}
                               for k, v in rules.escalations.items()]), hide_index=True, width='stretch')
    st.markdown("#### Retention by tier")
    st.dataframe(pd.DataFrame([{"Tier": t, "Retention": s} for t, s in rules.retention.items()]),
                 hide_index=True, width='stretch')
    st.caption(f"Policy version: {rules.policy_version}")


# ---------- main ----------

def main() -> None:
    st.set_page_config(page_title="Record Check", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    conn = get_conn()
    with st.sidebar:
        st.title("Record Check")
        st.caption("Example data: invented case 2026/0412. All people, records and references are fictional.")
        st.markdown(f"Live lookups: **{'on' if online_on() else 'off'}**  \nLLM: **{'on' if llm.available() else 'off'}**")
    get_policy()
    t0, t1, t2, t3, t5, t4 = st.tabs(["Setup", "Check", "Passport", "Recall", "Disposal", "Register"])
    with t0:
        tab_setup(conn)
    with t1:
        tab_check(conn)
    with t2:
        tab_passport(conn)
    with t3:
        tab_recall(conn)
    with t5:
        tab_disposal(conn)
    with t4:
        tab_register(conn)


main()
