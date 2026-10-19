"""Record Check console. Run: uv run streamlit run app/streamlit_app.py"""

from __future__ import annotations

import html
import os
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from recordcheck import citations as cit
from recordcheck import db, disposal, evidence, gate as gatemod, llm, passport, printout, recall, sources
from recordcheck import policy as policymod
from recordcheck import view as vw
from recordcheck.hashing import short
from recordcheck.models import AIEvent, DocumentType, Policy, Review

DEFAULT_DOC = "DOC-2026/0412-summary"
AUTHOR = "A. Caseworker"            # the demo user who drafted with AI; cannot also review
FALLBACK_MODEL = "northstar-8-2026-09-15"
FALLBACK_PROVIDER = "Northstar AI (fictional vendor)"

CITE_COLOURS = {"found": ("#d1f0dc", "#14532d"), "mismatch": ("#fde8b8", "#7a4a00"),
                "not_found": ("#f8d0d0", "#7f1d1d"), "not_checked": ("#e5e7eb", "#374151")}
WEIGHT_COLOURS = {"supported": ("#d1f0dc", "#14532d"), "weak": ("#fde8b8", "#7a4a00"),
                  "unsupported": ("#f8d0d0", "#7f1d1d"), "contradicted": ("#4b5563", "#ffffff")}
DISPOSAL_COLOURS = {"due": ("#fde8b8", "#7a4a00"), "on hold": ("#e5e7eb", "#374151")}
ROT_COLOURS = {"redundant": ("#d6e6fb", "#1e3a8a"), "obsolete": ("#fde8b8", "#7a4a00"),
               "trivial": ("#e5e7eb", "#374151"), "draft": ("#f8d0d0", "#7f1d1d")}
ROT_NAMES = {"redundant": "Redundant", "obsolete": "Obsolete", "trivial": "Trivial", "draft": "Draft"}
OVERDUE_COLOURS = {"overdue": ("#ede9fe", "#4c1d95")}   # not ROT: an overdue record still counts as evidence
DEMO_OLD, DEMO_NEW = "REC-2026/004790", "REC-2026/004912"   # debt notice and its reissue (example data)
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
.rc-card {border:1px solid #d1d5db; border-radius:10px; padding:14px 18px 6px; background:#fbfbfa; margin:6px 0 14px;}
.rc-card .rc-card-head {display:flex; justify-content:space-between; font-size:0.78rem; letter-spacing:0.06em;
  text-transform:uppercase; color:#6b7280; border-bottom:1px solid #e5e7eb; padding-bottom:6px; margin-bottom:10px;}
.rc-grid {display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:4px 22px;}
.rc-group h5 {font-size:0.86rem; margin:4px 0 6px; color:#111827;}
.rc-mono {font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:0.85rem;}
@media (max-width: 900px) {.rc-grid {grid-template-columns:repeat(2, minmax(0, 1fr));}}
</style>
"""


# ---------- helpers ----------

@st.cache_resource
def get_conn():
    # builds and seeds the DB; SQLite, or Postgres when DATABASE_URL is set; safe across Streamlit's script threads
    return db.open_db()


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
        assessment = evidence.assess(doc, conn, results, policy=pol, document_type=dtype_id)
        st.session_state["check"] = {"doc_id": doc.id, "citations": results, "assessment": assessment,
                                     "policy_version": pol.version, "document_type": dtype_id}

    state = st.session_state.get("check")
    if not state or state["doc_id"] != doc.id:
        st.info("Run the check to look up each reference and trace each sentence to authoritative records.")
        return
    if state.get("policy_version") != pol.version:
        st.info("The policy changed since this check ran. Run the check again so it uses the current policy.")
        return
    if state.get("document_type") != dtype_id:
        st.info("The document type changed. Run the check again: a record's intended use can exclude some types.")
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
    st.caption("Steps run in order: your records, offline cache, Crossref/OpenAlex fuzzy match. "
               "No AI judge decides a weight.")
    for r in results:
        c1, c2 = st.columns([1, 6])
        c1.markdown(pill(r.status.replace("_", " "), CITE_COLOURS, r.status), unsafe_allow_html=True)
        stage, strength = cit.match_stage(r)
        c2.markdown(f"**[{r.citation.n}]** {esc(r.citation.raw)}<br><span style='color:#6b7280;font-size:0.88rem'>"
                    f"{esc(r.note)}<br>{esc(stage)} · {esc(strength)}</span>", unsafe_allow_html=True)

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
    stage, strength = evidence.claim_stage(v)
    st.caption(f"Matched by: {stage} · {strength}")
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
    pol = get_policy()
    c1, c2 = st.columns(2)
    reviewer = c1.text_input("Reviewer name", "B. Team Leader")
    decision = c2.selectbox("Decision", ["approved", "approved_with_edits", "rejected"])
    flag = st.checkbox("Output informs a decision about a person, case or money", value=True)
    now = datetime.now(timezone.utc)
    review = Review(reviewer=reviewer.strip(), decision=decision, reviewed_at=now) if reviewer.strip() else None
    rules = get_rules()
    # the type's default tier is the floor; the escalation rules can only raise it
    probe = AIEvent(id="probe", app_id="agency-assistant", user=AUTHOR, created=now, prompt="", output="",
                    model_requested="", model_returned="", provider="", exported_to_document=doc.id, decision_flag=flag)
    tier = max(dtype.default_tier, passport.classify(probe, rules), key=lambda t: passport.TIER_ORDER[t])
    result = gatemod.evaluate(assessment, results, review, dtype, tier, author=AUTHOR)
    st.markdown(f"Gate with this review (tier {tier}):")
    gate_banner(result)
    blocked = result.status == "blocked"
    if blocked:
        st.error("Blocked by policy: fix the document or ask the information manager to change the bar.")
    if st.button("Issue passport", disabled=blocked):
        linked = evidence.relied_on(assessment, conn, pol, dtype.id)   # what the claims rest on, not every match
        requested, returned, provider = real_model()
        event = AIEvent(
            id=f"EVT-{now:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:4]}", app_id="agency-assistant", user=AUTHOR,
            created=now, prompt="Summarise the hardship policy for case 2026/0412 and cite authorities",
            output=doc.body, model_requested=requested, model_returned=returned, provider=provider,
            source_record_ids=linked, exported_to_document=doc.id, decision_flag=flag,
            function="Debt waiver assessment")
        try:
            p = passport.build(event, tier=tier, assessment=assessment, citations=results, review=review,
                               conn=conn, rules=rules, document_type=dtype.id, policy=pol)
        except ValueError as e:  # the engine re-runs the gate and the tier, self-review and record-id rules
            st.error(f"Not filed: {e}")
            return
        st.session_state["issued_msg"] = f"Passport issued: {p.record.id}. Here it is, with the checks done on it."
        st.session_state["open_next"] = p.record.id   # back to Records, on the new passport
        st.session_state["checking"] = False
        st.rerun()


# ---------- Setup ----------

TIER_NAMES = {"T0": "T0 transitory log", "T1": "T1 retained output", "T2": "T2 informs a decision",
              "T3": "T3 agent action"}

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


def _save(conn, draft: Policy, by: str, msg: str) -> None:
    saved = policymod.save(draft.model_copy(deep=True), by=by.strip() or "Information manager", conn=conn)
    st.session_state["policy"] = saved
    _set_draft(saved)
    st.session_state["setup_msg"] = msg.format(v=saved.version, sector=saved.sector_name)


def tab_setup(conn) -> None:
    pol = get_policy()
    draft = _draft()
    gen = st.session_state["draft_gen"]
    presets = policymod.load_presets()
    pnames = {p.id: p.name for p in presets}
    levels = policymod.LEVELS
    st.caption("Set what good looks like once; every check and the filing gate follow it. Three questions, then save. "
               "An AI model never sets a threshold, tier or gate.")
    if st.session_state.get("setup_msg"):
        st.success(st.session_state.pop("setup_msg"))

    # 1. sector
    st.markdown("#### 1. Start from your sector")
    st.session_state.setdefault("setup_org", pol.organisation)
    st.session_state.setdefault("setup_preset", pol.sector if pol.sector in pnames else presets[0].id)
    c1, c2 = st.columns([2, 1])
    c1.radio("Sector", list(pnames), format_func=pnames.get, key="setup_preset", horizontal=True,
             label_visibility="collapsed")
    c2.text_input("Organisation", key="setup_org")
    chosen = policymod.get_preset(st.session_state["setup_preset"])
    st.caption(f"{chosen.description} Document types: {', '.join(d.name for d in chosen.document_types)}.")
    if chosen.id == pol.sector:
        st.caption(f"In use: policy v{pol.version}, from this preset.")
    elif st.button(f"Use the {chosen.name} preset (replaces policy v{pol.version})"):
        new = policymod.from_preset(chosen, st.session_state["setup_org"].strip() or policymod.DEFAULT_ORG,
                                    by=st.session_state.get("setup_by", "Information manager"))
        new.version = pol.version  # version numbers keep counting up across presets
        _save(conn, new, st.session_state.get("setup_by", "Information manager"),
              "Policy v{v} saved from the {sector} preset.")
        st.rerun()

    # 2. document types
    st.markdown("#### 2. Your document types")
    st.caption("Pick how strict each type is. " + " ".join(f"**{lv.name}**: {lv.use_for}." for lv in levels.values()))
    level_opts = list(levels) + ["custom"]
    level_name = lambda k: levels[k].name if k in levels else "Custom (set under Advanced)"
    for i, d in enumerate(list(draft.document_types)):
        k = f"{gen}-{d.id}"
        with st.container(border=True):
            a, b, c, x = st.columns([3, 2, 2, 1])
            a.markdown(f"**{esc(d.name)}**", unsafe_allow_html=True)
            cur = policymod.level_of(d) or "custom"
            pick = b.selectbox("Strictness", level_opts, index=level_opts.index(cur), format_func=level_name,
                               key=f"{k}-lvl", label_visibility="collapsed")
            if pick != cur and pick in levels:
                draft.document_types[i] = d = policymod.apply_level(d, pick)
            d.default_tier = c.selectbox("Tier", TIERS, index=TIERS.index(d.default_tier), key=f"{k}-tier",
                                         format_func=lambda t: TIER_NAMES.get(t, t), label_visibility="collapsed")
            if x.button("Remove", key=f"{k}-rm", disabled=len(draft.document_types) <= 1):
                draft.document_types = [y for y in draft.document_types if y.id != d.id]
                st.session_state["draft_gen"] += 1
                st.rerun()
            st.caption(policymod.describe(d))
    with st.form(f"add_type_{gen}", clear_on_submit=True):
        a, b, c = st.columns([3, 2, 2])
        nname = a.text_input("Add a document type", placeholder="e.g. Ministerial brief")
        nlvl = b.selectbox("Strictness", list(levels), index=1, format_func=level_name)
        ntier = c.selectbox("Tier", TIERS, index=1, format_func=lambda t: TIER_NAMES.get(t, t))
        if st.form_submit_button("Add"):
            try:
                draft.document_types.append(policymod.new_type(nname, nlvl, ntier, draft.document_types))
                st.session_state["draft_gen"] += 1
                st.rerun()
            except ValueError as e:
                st.warning(str(e))

    # 3. evidence systems
    st.markdown("#### 3. Which systems count as evidence")
    systems = sorted({r.system for r in db.get_records(conn)} | set(draft.authoritative_systems))
    draft.authoritative_systems = st.multiselect(
        "Systems of record", systems, default=[x for x in draft.authoritative_systems if x in systems],
        key=f"{gen}-systems", label_visibility="collapsed")
    st.caption("Only records from these systems can make a claim supported. Anything else (a shared drive, a saved "
               "web page) reads weak at most.")

    # save
    a, b = st.columns([3, 1])
    by = a.text_input("Saved by (written to the audit log)", "Information manager", key="setup_by")
    b.write("")
    if b.button("Save policy", type="primary"):
        draft.organisation = st.session_state["setup_org"].strip() or draft.organisation
        _save(conn, draft, by, "Policy v{v} saved.")
        st.rerun()

    # advanced: everything an information manager rarely changes
    with st.expander("Advanced"):
        st.markdown("**Exact thresholds per document type**")
        for d in draft.document_types:
            k = f"{gen}-{d.id}-adv"
            with st.container(border=True):
                st.markdown(f"*{esc(d.name)}* ({d.id})", unsafe_allow_html=True)
                d.description = st.text_input("Description", d.description, key=f"{k}-desc")
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
                q.citations_not_checked_attention = st.checkbox("A citation that could not be checked needs attention", q.citations_not_checked_attention, key=f"{k}-nc")
                q.require_reviewer = st.checkbox("T2 and T3 need a named reviewer", q.require_reviewer, key=f"{k}-rr")

        st.markdown("**Apps and tiers**")
        tr = draft.tier_rules
        for app_id in list(tr.app_defaults):
            tr.app_defaults[app_id] = st.selectbox(f"{tr.app_names.get(app_id, app_id)}: default tier", TIERS,
                                                   index=TIERS.index(tr.app_defaults[app_id]), key=f"{gen}-app-{app_id}")
        labels = {"exported_to_document": "Output filed into a document", "decision_flag": "Output informs a decision",
                  "side_effect_tool_call": "Agent took an action with side effects"}
        st.caption("Escalations: " + "; ".join(f"{labels.get(k, k)} raises to at least {v}" for k, v in tr.escalations.items()))
        tr.retention_days["T0"] = int(st.number_input("T0 log retention (days)", 1, 3650, tr.retention_days.get("T0", 90), key=f"{gen}-ret"))

        st.markdown("**Guidance this policy cites**")
        g = st.text_area("One per line", "\n".join(draft.guidance), key=f"{gen}-guid")
        draft.guidance = [x.strip() for x in g.splitlines() if x.strip()]

        st.markdown("**Ask the model for a starting preset**")
        st.text_area("Describe your organisation in a sentence", key="setup_desc",
                     placeholder="e.g. A regional hospital using an AI scribe for clinic notes")
        if st.button("Suggest a preset"):
            if not llm.available():
                st.session_state["suggestion"] = None
                st.info("Suggestions need the LLM; pick a sector instead.")
            else:
                with st.spinner("Asking the model for a starting point..."):
                    st.session_state["suggestion"] = policymod.suggest(st.session_state.get("setup_desc", ""))
                if st.session_state["suggestion"] is None:
                    st.warning("No suggestion this time; pick a sector instead.")
        sug = st.session_state.get("suggestion")
        if sug:
            st.info(f"Suggested: **{sug.preset.name}** for {sug.organisation}. {sug.preset.description} "
                    "A starting point only: you confirm it in step 1.")
            st.button("Use this suggestion", on_click=_use_suggestion)

        st.markdown("**Start again**")
        reset_ok = st.checkbox("Confirm: discard my changes and go back to the preset defaults", key="setup_reset_ok")
        if st.button("Reset to preset defaults", disabled=not reset_ok):
            base = policymod.from_preset(policymod.get_preset(pol.sector if pol.sector in pnames else policymod.DEFAULT_PRESET),
                                         pol.organisation, by=by.strip() or "Information manager")
            base.version = pol.version  # keep counting up so the history of versions stays monotonic
            _save(conn, base, by, "Policy v{v} saved (reset to {sector} defaults).")
            st.rerun()


# ---------- Records (passport-first) ----------

STATUS_MD = {"ok": ":green[**OK**]", "attention": ":orange[**Check**]", "problem": ":red[**Problem**]"}
TIER_WORDS = {"T0": "T0, a transitory log", "T1": "T1, a retained output", "T2": "T2, informs a decision",
              "T3": "T3, an agent's action"}
WEIGHT_WORDS = {"supported": "Supported", "weak": "Weak", "unsupported": "Unsupported", "contradicted": "Contradicted"}
CITE_WORDS = {"found": "Found", "mismatch": "Details differ", "not_found": "Not found (possibly fabricated)",
              "not_checked": "For a person to confirm"}


def _headline(v, p) -> tuple[str, str]:
    """(headline, colour) in plain words: what a records person needs to know first."""
    c = {x.id: x for x in v.checks}
    if v.disposed:
        return "Disposed: the content was destroyed under an approved authority; its hash is kept in the chain.", "gray"
    if "since" in c and c["since"].status == "problem":
        return "Changed since filing: " + c["since"].summary.removeprefix("Since filing: "), "red"
    if not v.at_issue:
        return f"Older record: summary only. {TIER_WORDS[v.tier].capitalize()}.", "gray"
    ev = c["evidence"]
    if v.gate == "ready":
        line = ("every statement is supported by authoritative records" if ev.status == "ok"
                else ev.summary[0].lower() + ev.summary[1:].rstrip("."))
        return f"Ready to file: {line}.", "green"
    if v.gate == "attention":
        return f"Filed with items to check: {ev.summary[0].lower() + ev.summary[1:]}", "orange"
    return f"Filed: {ev.summary}", "blue"


def _sentences(c) -> None:
    """A check's detail in sentences and small tables; never raw booleans. Status is already in the row."""
    d = c.details
    if c.id == "citations" and d.get("items"):
        st.dataframe(pd.DataFrame([{"Ref": f"[{i['n']}]", "Reference": i["reference"],
                                    "Result": CITE_WORDS.get(i["status"], i["status"]), "Note": i["note"]}
                                   for i in d["items"]]), hide_index=True, width='stretch')
    elif c.id == "evidence" and d.get("items"):
        st.dataframe(pd.DataFrame([{"Statement": i["text"], "Result": WEIGHT_WORDS[i["weight"]], "Why": i["reason"],
                                    "Records": ", ".join(dict.fromkeys(l["record_id"] for l in i["links"])) or "none"}
                                   for i in d["items"]]), hide_index=True, width='stretch')
    elif c.id == "sources" and d.get("items"):
        st.dataframe(pd.DataFrame([{"Record": s["record_id"], "Title": s["title"], "System": s["system"],
                                    "At filing": "Counted as evidence" if s["counted"] else f"Did not count: {s['why_not']}"}
                                   for s in d["items"]]), hide_index=True, width='stretch')
    elif c.id == "gate":
        for r in d.get("reasons", []):
            st.markdown(f"- {esc(r)}")
        st.caption(f"Judged against {d.get('policy_version')}.")
    elif c.id == "review" and d:
        st.markdown(f"{esc(d['reviewer'])} {d['decision'].replace('_', ' ')} it on {d['reviewed_at'][:10]}."
                    + (f" Note: {esc(d['note'])}" if d.get("note") else ""))
    elif c.id == "integrity":
        st.markdown("The passport's content matches its hash, and it sits unbroken in the chain of all passports."
                    if c.status == "ok" else esc(c.summary))
        if st.toggle("Technical details", key=f"tech_{c.id}_{d.get('hash', '')[:8]}"):
            st.code(f"{d['algorithm']} {d['hash']}\nprevious {d.get('prev_hash') or 'none (first)'}\n"
                    f"checks   {d.get('checks_hash') or 'not stored (older record)'}\n{d.get('chain', '')}")
    elif c.id == "retention":
        days = d.get("retention_days")
        st.markdown(f"{TIER_WORDS[d['tier']].capitalize()}. "
                    + (f"Kept {days} days, then destroyed with a named person's approval. " if days else
                       "Kept for as long as the business record it supports. ")
                    + f"Disposal authority: {esc(d['authority'])}.")
    elif c.id == "since":
        for x in d.get("sources_changed", []):
            st.markdown(f"- Source {esc(x['record_id'])} is now {esc(x['why'])}.")
        st.markdown(f"Model {esc(d['model'])}: {'not registered' if d['model_status'] == 'not registered' else d['model_status']}. "
                    + ("Queued for re-review." if d.get("queued") else "Not queued for review."))
        st.caption("The one live check: it reads the records and the model register as they are now.")



def _passport_card(conn, p, v, pol) -> str:
    """The passport itself, as a document: six groups in plain words; hashes shortened, in monospace."""
    mono = lambda h: f'<span class="rc-mono">{esc(short(h, 6))}</span>' if h else "none"
    r, a, b, pr, rv, ig, pd_ = p.record, p.agent, p.business, p.process, p.review, p.integrity, p.paradata
    dname = next((d.name for d in pol.document_types if d.id == b.document_type), b.document_type) if b.document_type else "not stated"
    ev = ", ".join(f"{n} {w}" for w, n in pr.evidence_summary.items() if n) or "no check recorded"
    ci = ", ".join(f"{n} {CITE_WORDS[k].lower()}" for k, n in pr.citation_summary.items() if n) or "none checked"
    tools = "; ".join(t.name + (" (changed something)" if t.side_effect else "") for t in pr.tool_calls) or "none"
    prompt = pr.prompt if len(pr.prompt) <= 160 else pr.prompt[:157] + "..."
    groups = [
        ("Record", [("Title", esc(r.title)), ("Created", esc(r.created.astimezone().strftime("%d %b %Y, %H:%M")
                                                         if r.created.tzinfo else r.created.strftime("%d %b %Y, %H:%M"))),
                    ("Made with AI", "Yes, in part" if r.ai_generated else "No"),
                    ("Filed into", esc(r.final_document or "no document")), ("Content fingerprint", mono(r.content_hash))]),
        ("Agent", [("Person", esc(a.person)), ("AI system", esc(a.ai_system)), ("Model asked for", esc(a.model_requested)),
                   ("Model that answered", esc(a.model_returned)), ("Provider", esc(a.provider))]),
        ("Business", [("Function", esc(b.function or "not stated")), ("Risk tier", esc(TIER_WORDS[b.tier])),
                      ("Why this tier", esc(b.tier_reason)), ("Document type", esc(dname)),
                      ("Filing gate", esc(GATE_COLOURS[b.gate][2]) if b.gate else "not recorded"),
                      ("Keep for", esc(b.disposal))]),
        ("Process", [("Prompt", esc(prompt)), ("Source records", esc(", ".join(pr.source_record_ids) or "none")),
                     ("Statements", esc(ev)), ("References", esc(ci)), ("Agent actions", esc(tools))]),
        ("Review", [("Reviewer", esc(rv.reviewer)), ("Decision", esc(rv.decision.replace("_", " ").capitalize())),
                    ("Reviewed", esc(rv.reviewed_at.astimezone().strftime("%d %b %Y, %H:%M"))),
                    ("Note", esc(rv.note or "none"))] if rv else [("Reviewer", "No review recorded")]),
        ("Integrity and policy", [("Fingerprint", mono(ig.hash)), ("Previous in chain", mono(ig.prev_hash)),
                                  ("Checks at filing", mono(pr.checks_hash) if pr.checks_hash else "not stored (older record)"),
                                  ("Judged against", esc(pd_.policy_version)), ("Policy fingerprint", mono(pd_.policy_hash)),
                                  ("AI use register", esc(pd_.use_register_id))]),
    ]
    body = "".join(f'<div class="rc-group"><h5>{g}</h5>' + "".join(kv(k, val) for k, val in rows) + "</div>"
                   for g, rows in groups)
    return (f'<div class="rc-card"><div class="rc-card-head"><span>Record passport</span><span>{esc(r.id)}</span></div>'
            f'<div class="rc-grid">{body}</div></div>')


def _records_table(views, current: str) -> str | None:
    """A compact table to pick from; returns the record id clicked, if any."""
    df = pd.DataFrame([{"Record": ("> " if v.record_id == current else "") + v.title.split(" (")[0]
                                  + f", {v.filed.strftime('%d %b')}",
                        "Status": ("Disposed" if v.disposed else
                                   "Changed since filing" if any(c.id == "since" and c.status == "problem" for c in v.checks)
                                   else {"ready": "Ready", "attention": "To check"}.get(v.gate, "Older"))}
                       for v in views])
    ev = st.dataframe(df, hide_index=True, width='stretch', height=520, on_select="rerun",
                      selection_mode="single-row", key="records_table")
    rows = ev.selection.rows if ev and ev.selection else []
    if rows and rows != st.session_state.get("records_table_seen"):
        st.session_state["records_table_seen"] = rows
        return views[rows[0]].record_id
    return None


def page_records(conn) -> None:
    if st.session_state.get("checking"):
        if st.button("Back to records"):
            st.session_state["checking"] = False
            st.rerun()
        tab_check(conn)
        return
    pol = get_policy()
    views = vw.view_all(conn, pol)
    if st.button("Check a document", type="primary"):
        st.session_state["checking"] = True
        st.rerun()
    if st.session_state.get("issued_msg"):
        st.success(st.session_state.pop("issued_msg"))
    if not views:
        st.info("File a document to see its passport.")
        return
    ids = [v.record_id for v in views]
    if st.session_state.get("open_next") in ids:
        st.session_state["records_open"] = st.session_state.pop("open_next")
    if st.session_state.get("records_open") not in ids:
        full = [v for v in views if v.at_issue and not v.disposed]
        if not full:
            st.info("File a document to see its passport with every check. Older records on the left carry summary counts only.")
        st.session_state["records_open"] = (full or views)[0].record_id
    v = next(x for x in views if x.record_id == st.session_state["records_open"])
    p = db.get_passport(conn, v.record_id)

    left, right = st.columns([1.25, 2.5], gap="medium")
    with left:
        st.markdown("#### Records")
        st.caption("Newest first. Click a row to open it.")
        clicked = _records_table(views, v.record_id)
        if clicked and clicked != v.record_id:
            st.session_state["records_open"] = clicked
            st.rerun()
    with right:
        head, colour = _headline(v, p)
        st.markdown(f"### :{colour}[{esc(head)}]")
        st.markdown(f"{esc(v.title)}. Filed {(v.filed.astimezone() if v.filed.tzinfo else v.filed).strftime('%d %b %Y, %H:%M')} "
                    f"by {esc(p.agent.person)} with {esc(p.agent.ai_system)}; "
                    + (f"reviewed by {esc(v.reviewer)}." if v.reviewer else "no reviewer."))
        if p is not None:
            st.markdown(_passport_card(conn, p, v, pol), unsafe_allow_html=True)
        st.markdown("#### Checks done on this record")
        ran = [c for c in v.checks if c.status != "not_run"]
        skipped = [c.name for c in v.checks if c.status == "not_run"]
        for c in ran:
            with st.expander(f"{STATUS_MD[c.status]} {c.name}: {c.summary}", expanded=c.status == "problem"):
                _sentences(c)
        if skipped:
            st.caption(("Not recorded for this older record: " if not v.at_issue else "Not run for this document: ")
                       + ", ".join(skipped) + ".")
        if p and not v.disposed:
            st.download_button("Download as PDF", printout.passport_pdf(p, passport.verify_chain(conn)),
                               file_name=printout.filename(p), mime="application/pdf", key=f"rec_pdf_{v.record_id}")


# ---------- Recall ----------

def recall_table(items) -> None:
    rows = "".join(
        f"<tr><td>{esc(i.record_id)}</td><td>{pill(i.tier, TIER_COLOURS, i.tier)}</td><td>{esc(i.function)}</td>"
        f"<td>{i.created:%Y-%m-%d}</td><td>{esc(i.reviewer or 'none')}</td><td>{'yes' if i.queued else 'no'}</td></tr>"
        for i in items)
    st.markdown("<table style='width:100%;font-size:0.9rem'><thead><tr><th align=left>Record id</th><th align=left>Tier</th>"
                "<th align=left>Function</th><th align=left>Created</th><th align=left>Reviewer</th><th align=left>Queued</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>", unsafe_allow_html=True)


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
        recall_table(res.items)
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


# ---------- Sources ----------

def tab_sources(conn) -> None:
    h = sources.health(conn, get_policy())
    st.markdown("The records your AI draws on, checked for ROT. Only current records from authoritative systems "
                "count as evidence; everything flagged here makes a claim read weak at most.")
    rel = sources.reliability(conn, get_policy())
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        if rel.share is None:
            c1.metric("Retained AI outputs resting on current authoritative records", "no sources listed")
        else:
            c1.metric("Retained AI outputs that cite records", f"{rel.sources_ok} of {rel.with_sources}",
                      help="Retained outputs (T1 to T3, not disposed) whose source records all still count as "
                           "evidence. It drops the moment a source is superseded.")
            c1.caption(f"{rel.sources_ok} of {rel.with_sources} retained AI outputs that cite records rest on current "
                       f"authoritative records ({rel.share:.0%}). Claim checks recorded: "
                       + (f"{rel.claim_supported} of {rel.claim_checked} with every claim supported by authoritative "
                          "records." if rel.claim_checked else "none yet."))
        if rel.drag:
            c2.markdown("**Sources pulling it down**")
            c2.markdown("".join(f"- {esc(d.record_id)} {esc(d.title)}: {esc(d.why)}; relied on by {d.outputs} "
                                f"output{'s' if d.outputs != 1 else ''}\n" for d in rel.drag))
        else:
            c2.markdown("Every source these outputs list still counts as evidence.")
        if rel.overdue:
            c2.markdown("**Relied on but overdue for review** (still counts; the owner should confirm it)")
            c2.markdown("".join(f"- {esc(d.record_id)} {esc(d.title)}: {esc(d.why)}; relied on by {d.outputs} "
                                f"output{'s' if d.outputs != 1 else ''}\n" for d in rel.overdue))
    m = st.columns(6)
    m[0].metric("Count as evidence", f"{h.eligible} of {h.total}")
    for col, label in zip(m[1:], sources.LABELS):
        col.metric(ROT_NAMES[label], h.counts[label])
    m[5].metric("Overdue for review", h.overdue)

    st.markdown("#### Flagged records")
    flagged = [i for i in h.items if i.labels or i.overdue]
    if flagged:
        rows = "".join(
            f"<tr><td>{esc(i.record_id)}</td><td>{esc(i.title)}</td><td>{esc(i.system)}</td>"
            f"<td>{' '.join(pill(ROT_NAMES[l], ROT_COLOURS, l) for l in i.labels)}"
            f"{' ' + pill('Overdue for review', OVERDUE_COLOURS, 'overdue') if i.overdue else ''}</td>"
            f"<td>{esc('; '.join(i.notes))}</td></tr>" for i in flagged)
        st.markdown("<table style='width:100%;font-size:0.9rem'><thead><tr><th align=left>Record id</th><th align=left>Title</th>"
                    "<th align=left>System</th><th align=left>Flags</th><th align=left>Why</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>", unsafe_allow_html=True)
    else:
        st.info("No redundant, obsolete, trivial, draft or overdue records.")

    scoped = [i for i in h.items if i.purpose or i.not_for]
    if scoped:
        st.markdown("#### Intended use")
        st.caption("A record does not count as evidence for a document type its intended use excludes.")
        pol = get_policy()
        names = lambda ids: ", ".join(policymod.doc_type(pol, t).name if policymod.doc_type(pol, t) else t for t in ids)
        rows = "".join(f"<tr><td>{esc(i.record_id)}</td><td>{esc(i.title)}</td><td>{esc(i.purpose)}</td>"
                       f"<td>{esc(names(i.not_for))}</td></tr>" for i in scoped)
        st.markdown("<table style='width:100%;font-size:0.9rem'><thead><tr><th align=left>Record id</th>"
                    "<th align=left>Title</th><th align=left>Intended use</th><th align=left>Not for</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>", unsafe_allow_html=True)

    records = db.get_records(conn)
    ids = [r.id for r in records]
    current = [r.id for r in records if r.status == "current"]
    st.markdown("#### Mark a source superseded")
    st.caption("A new version replaces a record (a reissued notice, a new policy). It stops counting as evidence at once, "
               "and recall lists every AI output that relied on it.")
    if current:
        with st.form("mark_source"):
            c1, c2 = st.columns(2)
            rid = c1.selectbox("Record", current, index=current.index(DEMO_OLD) if DEMO_OLD in current else 0)
            others = ["(none)"] + [i for i in ids if i != rid]
            by_id = c2.selectbox("Superseded by", others, index=others.index(DEMO_NEW) if DEMO_NEW in others else 0)
            reason = st.text_input("Reason", "Debt recalculated; notice reissued with a corrected amount")
            if st.form_submit_button("Mark superseded"):
                try:
                    recall.mark_superseded(conn, rid, None if by_id == "(none)" else by_id, reason,
                                           by="Information manager")
                    st.session_state["recall_record"] = rid
                    st.session_state.pop("source_queued_msg", None)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.markdown("#### Recall by source record")
    default = st.session_state.get("recall_record", DEMO_OLD if DEMO_OLD in ids else ids[0])
    rid = st.selectbox("Outputs that relied on", ids, index=ids.index(default) if default in ids else 0, key="recall_record_pick")
    res = recall.recall_by_record(conn, rid)
    r = res.record
    st.caption(f"{r.title}. Status {r.status}" + (f", superseded by {r.superseded_by}" if r.superseded_by else "") + ".")
    n = res.counts
    m = st.columns(4)
    m[0].metric("Outputs affected", n["T1"] + n["T2"] + n["T3"])
    m[1].metric("T2 decision-informing", n["T2"])
    m[2].metric("T1", n["T1"])
    m[3].metric("T3", n["T3"])
    if res.items:
        recall_table(res.items)
    else:
        st.info("No T1 to T3 output lists this record as a source.")
    t2 = [i.record_id for i in res.items if i.tier == "T2"]
    if st.button(f"Queue T2 outputs for re-review ({len(t2)})", disabled=not t2, key="queue_source_t2"):
        why = f"Source {rid} is {r.status}" + (f" (superseded by {r.superseded_by})" if r.superseded_by else "")
        k = recall.queue_for_review(conn, t2, by="Information manager", reason=why)
        st.session_state["source_queued_msg"] = f"Queued {k} T2 outputs for re-review ({len(t2) - k} were already queued)."
        st.session_state["recall_record"] = rid
        st.rerun()
    if st.session_state.get("source_queued_msg"):
        st.success(st.session_state["source_queued_msg"])


# ---------- Disposal ----------

def tab_disposal(conn) -> None:
    rules = get_rules()
    st.markdown("T0 log entries are kept 90 days, then destroyed with approval. T1 to T3 follow their business record.")
    st.caption("Retention here is a decision, not a timer: nothing is destroyed until a named person approves it, "
               "and the approval is recorded with its authority and hash.")
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
        st.radio("Go to", ["Records", "Information manager"], key="place")
        st.markdown(f"Live lookups: **{'on' if online_on() else 'off'}**  \nLLM: **{'on' if llm.available() else 'off'}**")
    get_policy()
    if st.session_state.get("place") == "Information manager":
        st.caption("Where the information manager sets the policy, watches the sources, recalls and disposes.")
        t0, t6, t3, t5, t4 = st.tabs(["Setup", "Sources", "Recall", "Disposal", "Register"])
        with t0:
            tab_setup(conn)
        with t6:
            tab_sources(conn)
        with t3:
            tab_recall(conn)
        with t5:
            tab_disposal(conn)
        with t4:
            tab_register(conn)
    else:
        page_records(conn)


main()
