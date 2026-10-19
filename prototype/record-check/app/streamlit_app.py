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
from recordcheck import dashboard, db, disposal, evidence, gate as gatemod, llm, passport, printout, recall, sources
from recordcheck import policy as policymod
from recordcheck import view as vw
from recordcheck.hashing import short
from recordcheck.models import AIEvent, DocumentType, Policy, Review

SHOW_ALL = os.getenv("RECORDCHECK_SHOW_ALL") == "1"   # 1 brings back the Sources, Disposal and Register tabs and the extras
DEFAULT_DOC = "DOC-2026/0412-summary"
AUTHOR = "A. Caseworker"            # the demo user who drafted with AI; cannot also review
FALLBACK_MODEL = "northstar-8-2026-09-15"
FALLBACK_PROVIDER = "Northstar AI (fictional vendor)"

# status colours: blue = supported / in order, orange = needs a person, solid orange = blocked or changed, grey = not run
BLUE, ORANGE, SOLID, GREY = ("#d6e6fb", "#1e3a8a"), ("#fde8b8", "#7a4a00"), ("#c2410c", "#ffffff"), ("#e5e7eb", "#374151")
CITE_COLOURS = {"found": BLUE, "mismatch": ORANGE, "not_found": SOLID, "not_checked": ORANGE}
WEIGHT_COLOURS = {"supported": BLUE, "weak": ORANGE, "unsupported": ORANGE, "contradicted": SOLID}
DISPOSAL_COLOURS = {"due": ORANGE, "on hold": GREY}
ROT_COLOURS = {"redundant": BLUE, "obsolete": ORANGE, "trivial": GREY, "draft": SOLID}
ROT_NAMES = {"redundant": "Redundant", "obsolete": "Obsolete", "trivial": "Trivial", "draft": "Draft"}
OVERDUE_COLOURS = {"overdue": ("#ede9fe", "#4c1d95")}   # not ROT: an overdue record still counts as evidence
DEMO_OLD, DEMO_NEW = "REC-2026/004790", "REC-2026/004912"   # debt notice and its reissue (example data)
TIER_COLOURS = {"T0": GREY, "T1": BLUE, "T2": ORANGE, "T3": SOLID}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
/* the app font everywhere except Streamlit's icon spans: those draw arrows from an icon font's ligatures */
.stApp, .stApp *:not([data-testid="stIconMaterial"]):not([class*="material-symbols"]) {font-family:'IBM Plex Sans', system-ui, sans-serif;}
.stApp code, .stApp pre, .stApp pre * {font-family:'IBM Plex Mono', ui-monospace, monospace !important;}
.stApp {background:#f4f5f7;}
.rc-mono {font-family:'IBM Plex Mono', ui-monospace, monospace !important; font-size:0.9em;}
.rc-pill {display:inline-block; padding:1px 10px; border-radius:999px; font-size:0.82rem; font-weight:600; white-space:nowrap;}
.rc-sent {padding:2px 4px; border-radius:4px; line-height:2.0; box-decoration-break:clone; -webkit-box-decoration-break:clone;}
.rc-sup {font-size:0.62rem; font-weight:700; letter-spacing:0.04em; margin-left:2px; color:#374151;}
.rc-doc {font-size:1.02rem; color:#111827;}
.rc-kv {margin:0 0 4px 0; font-size:0.92rem;}
.rc-kv span.k {color:#4b5563;}
.rc-brand {display:flex; align-items:center; gap:10px; flex-wrap:wrap;}
.rc-brand .n {font-size:20px; font-weight:700; letter-spacing:-0.01em;}
.rc-tag {font-size:12px; font-weight:600; padding:3px 10px; border-radius:999px; background:#e5e7eb; color:#374151;}
.rc-article {background:#fff; border:1px solid #d1d5db; border-radius:12px; padding:22px 24px; display:flex;
  flex-direction:column; gap:10px; margin-bottom:16px;}
.rc-eyebrow {display:flex; gap:10px; align-items:center; font-size:12px; color:#4b5563;}
.rc-eyebrow span:first-child {font-weight:600; letter-spacing:0.06em; text-transform:uppercase;}
.rc-title {margin:0 !important; padding:0 !important; font-size:26px !important; font-weight:700 !important; line-height:1.25 !important;}
.rc-headline {padding:12px 16px; border-radius:10px; font-size:17px;}
.rc-who {margin:0; font-size:14px; color:#374151; line-height:1.5;}
.rc-passport {margin-top:8px; border:1px solid #c7ccd4; border-radius:10px; background:#fbfbf9; padding:18px 20px;}
.rc-passport-head {display:flex; justify-content:space-between; align-items:baseline; gap:12px;
  border-bottom:2px solid #111827; padding-bottom:8px; margin-bottom:14px;}
.rc-passport-head .t {font-size:13px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;}
.rc-passport-head .s {font-size:12px; color:#4b5563;}
.rc-passport-grid {display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:14px 24px;}
.rc-pgroup {display:flex; flex-direction:column; gap:6px;}
.rc-pgroup .g {font-size:12px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; color:#1e3a8a;}
.rc-prow {display:flex; flex-direction:column; font-size:14px; line-height:1.4;}
.rc-prow .k {font-size:12px; color:#4b5563;}
.rc-prow .v {word-break:break-word;}
.rc-older {background:#fff; border:1px dashed #9ca3af; border-radius:12px; padding:14px 18px; font-size:14px;
  color:#374151; margin-bottom:16px;}
.rc-checks-head {display:flex; justify-content:space-between; align-items:baseline; gap:12px; font-size:16px; margin-bottom:6px;}
.rc-checks-head span {font-size:13px; color:#4b5563;}
.rc-kvrow {display:flex; flex-wrap:wrap; gap:4px 16px; font-size:14px; line-height:1.5; margin-bottom:6px;}
.rc-kvrow .k {width:170px; flex-shrink:0; color:#4b5563;}
.rc-kvrow .v {flex:1 1 260px; min-width:0; word-break:break-word;}
.rc-sent-card {border:1px solid #e5e7eb; border-radius:8px; padding:10px 12px; display:flex; flex-direction:column;
  gap:6px; margin-bottom:8px; font-size:14px;}
.rc-sent-card .why {font-size:13px; color:#4b5563;}
.rc-rel {background:#fff; border:1px solid #d1d5db; border-radius:12px; padding:22px 24px; display:flex; flex-wrap:wrap;
  gap:24px; align-items:center; margin-bottom:16px;}
.rc-rel .l {flex:1 1 280px; display:flex; flex-direction:column; gap:6px; font-size:14px; color:#374151;}
.rc-rel .e {font-size:12px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:#4b5563;}
.rc-rel .note {font-size:13px; color:#4b5563;}
.rc-rel .big {font-size:40px; font-weight:700; line-height:1.1; color:#111827;}
.rc-kpi {border-radius:12px; padding:16px 18px; min-height:150px; display:flex; flex-direction:column; gap:6px;}
.rc-kpi .l {font-size:14px; line-height:1.35;}
.rc-kpi .v {font-size:34px; font-weight:700; line-height:1.1;}
.rc-kpi .p {font-size:13px; line-height:1.4; opacity:0.9;}
.rc-rel .r {flex:1 1 320px; font-size:14px; color:#374151; line-height:1.5; border-left:1px solid #e5e7eb; padding-left:20px;}
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


GATE_COLOURS = {"ready": (*BLUE, "Ready to file"), "attention": (*ORANGE, "Needs review"), "blocked": (*SOLID, "Blocked")}
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
            created=now, prompt=f"Draft the {doc.title.split(',')[0].lower()}"
                                + (f" for case {doc.case_id}" if doc.case_id else "") + " and cite the records relied on",
            output=doc.body, model_requested=requested, model_returned=returned, provider=provider,
            source_record_ids=linked, exported_to_document=doc.id, decision_flag=flag,
            function=_doc_function(doc, dtype))
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

    if not SHOW_ALL:   # minimal demo: the three questions and Save only
        return
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


# ---------- Records (laid out as Hasim's mockup: list left, passport and its checks right) ----------

TIER_WORDS = {"T0": "T0, a transitory log", "T1": "T1, a retained output", "T2": "T2, informs a decision",
              "T3": "T3, an agent's action"}
WEIGHT_WORDS = {"supported": "Supported", "weak": "Weak", "unsupported": "Unsupported", "contradicted": "Contradicted"}
CITE_WORDS = {"found": "Found", "mismatch": "Details differ", "not_found": "Not found (possibly fabricated)",
              "not_checked": "For a person to confirm"}
TONE = {"ok": BLUE, "attention": ORANGE, "problem": SOLID, "not_run": GREY}
# the round mark at the start of each check row: a sign, never an emoji
MARK_MD = {"ok": ":blue-background[**✓**]", "attention": ":orange-background[**!**]",
           "problem": ":orange-background[**✕**]", "not_run": ":gray-background[**–**]"}


def _local(dt):
    """Stored times are UTC (naive, see models.naive_utc); show them in the viewer's local time."""
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone()


def _when(dt) -> str:
    return _local(dt).strftime("%d %b %Y")


def _kept(v) -> str:
    rt = next((c for c in v.checks if c.id == "retention"), None)
    days = rt.details.get("retention_days") if rt else None
    return "Disposed" if v.disposed else (f"Kept {days} days" if days else "Kept with the case file")


def _row_status(v) -> tuple[str, str]:
    """(word, tone) for a row in the records list."""
    if v.disposed:
        return "Disposed", "not_run"
    if any(c.id == "since" and c.status == "problem" for c in v.checks):
        return "Changed since filing", "problem"
    return {"ready": ("Ready to file", "ok"), "attention": ("Needs review", "attention")}.get(v.gate, ("Filed", "not_run"))


def _pill_md(word: str, tone: str) -> str:
    colour = {"ok": "blue", "attention": "orange", "problem": "orange", "not_run": "gray"}[tone]
    return f":{colour}-background[{word}]"


def _pill_html(word: str, tone: str) -> str:
    bg, fg = TONE[tone]
    return (f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;'
            f'background:{bg};color:{fg}">{esc(word)}</span>')


def _kv_rows(rows: list[tuple[str, str, bool]]) -> str:
    """Key-value lines inside an opened check; the bool marks monospace (ids and fingerprints)."""
    return "".join(
        f'<div class="rc-kvrow"><span class="k">{esc(k)}</span>'
        f'<span class="v{" rc-mono" if mono else ""}">{esc(v)}</span></div>' for k, v, mono in rows)


def _passport_card(conn, p, v, pol) -> str:
    """The passport itself: six groups, plain labels, ids and fingerprints in monospace."""
    r, a, b, pr, rv, ig, pd_ = p.record, p.agent, p.business, p.process, p.review, p.integrity, p.paradata
    ev = ", ".join(f"{n} {w}" for w, n in pr.evidence_summary.items() if n)
    groups = [
        ("Record", [("Identifier", r.id, True), ("Title", r.title, False),
                    ("AI-generated", "Yes, reviewed by a person" if rv else "Yes", False)]),
        ("Agent", [("Person", a.person, False), ("AI model returned", a.model_returned, True), ("Provider", a.provider, False)]),
        ("Business", [("Function", b.function or "not stated", False), ("Risk tier", TIER_WORDS[b.tier], False),
                      ("Disposal", _kept(v) if b.tier == "T0" else "Follows the case file", False)]),
        ("Process", [("Source records", ", ".join(pr.source_record_ids) or "none", True),
                     ("Evidence at filing", ev or ("Counts only (older record)" if not v.at_issue else "no statements checked"),
                      False)]),
        ("Review", [("Reviewer", f"{rv.reviewer}, {rv.decision.replace('_', ' ')} {_when(rv.reviewed_at)}" if rv
                     else ("None required at " + b.tier if b.tier in ("T0", "T1") else "Not reviewed"), False)]),
        ("Integrity and policy", [("Hash", short(ig.hash, 4), True), ("Previous in chain", short(ig.prev_hash, 4) if ig.prev_hash else "–", True),
                                  ("Policy", pd_.policy_version, False)]),
    ]
    body = "".join(
        f'<div class="rc-pgroup"><span class="g">{esc(g)}</span>'
        + "".join(f'<div class="rc-prow"><span class="k">{esc(k)}</span><span class="v{" rc-mono" if m else ""}">{esc(val)}</span></div>'
                  for k, val, m in rows) + "</div>" for g, rows in groups)
    return ('<div class="rc-passport"><div class="rc-passport-head"><span class="t">Passport</span>'
            '<span class="s">The record package kept with this output</span></div>'
            f'<div class="rc-passport-grid">{body}</div></div>')


def _check_rows(v, p) -> list:
    """The checks people see, in the mockup's order. An older record folds what was not kept into one 'At filing' line."""
    c = {x.id: x for x in v.checks}
    if v.at_issue:
        order = ["citations", "evidence", "sources", "bias", "gate", "review", "integrity", "retention", "since"]
        return [c[i] for i in order if i in c]
    ev = p.process.evidence_summary
    n = sum(ev.values())
    at = (f"{ev.get('supported', 0)} statements supported" if n else "Filed") + \
         ("; filed with a named reviewer." if p.review else "; detailed checks were not kept for older records.")
    from recordcheck.models import CheckSummary
    at_filing = CheckSummary(id="at_filing", name="At filing", status="ok", summary=at,
                             details={"sources": p.process.source_record_ids})
    rows = [at_filing] + ([c["bias"]] if "bias" in c and c["bias"].status != "not_run" else []) + [c["integrity"], c["retention"]]
    if "since" in c:
        rows = ([c["since"]] + rows) if c["since"].status == "problem" else rows + [c["since"]]
    return rows


def _check_detail(conn, c, v, p, pol) -> None:
    """What opens under a check: key-value lines, and sentence cards for the evidence."""
    d = c.details
    if c.id == "evidence" and d.get("items"):
        recs = {r.id: r for r in db.get_records(conn)}
        cards = []
        for i in d["items"]:
            ids = list(dict.fromkeys(l["record_id"] for l in i["links"]))
            why = ("; ".join(f"{x} {recs[x].title}" if x in recs else x for x in ids) if i["weight"] == "supported" and ids
                   else i["reason"])
            tone = {"supported": "ok", "weak": "attention", "unsupported": "attention", "contradicted": "problem"}[i["weight"]]
            cards.append(f'<div class="rc-sent-card"><div>{_pill_html(WEIGHT_WORDS[i["weight"]], tone)} '
                         f'<span>{esc(i["text"])}</span></div><span class="why">{esc(why)}</span></div>')
        st.markdown("".join(cards), unsafe_allow_html=True)
        return
    rows: list[tuple[str, str, bool]] = []
    if c.id == "citations":
        rows = [(f"[{i['n']}]", f"{CITE_WORDS.get(i['status'], i['status'])}. {i['note']}".strip(), False) for i in d.get("items", [])]
    elif c.id == "sources":
        items = d.get("items", [])
        relied = [s["record_id"] for s in items if s["counted"]]
        other = [f"{s['record_id']} ({s['why_not']})" for s in items if not s["counted"]]
        rows = ([("Relied on", ", ".join(relied), True)] if relied else []) + ([("Did not count", "; ".join(other), False)] if other else [])
    elif c.id == "gate":
        dtype = next((x for x in pol.document_types if x.id == v.document_type), None)
        if dtype:
            lvl = policymod.level_of(dtype)
            rows.append(("Bar", (policymod.LEVELS[lvl].name + ": " if lvl else "Custom: ") + policymod.describe(dtype), False))
        rows += [("Reason", r, False) for r in d.get("reasons", []) if not r.startswith("Meets the bar")]
        rows.append(("Policy", d.get("policy_version") or "", False))
    elif c.id == "review" and d:
        rows = [("Decision", f"{d['decision'].replace('_', ' ').capitalize()}, {d['reviewed_at'][:16].replace('T', ' ')}", False)]
        if d.get("note"):
            rows.append(("Note", d["note"], False))
    elif c.id == "integrity":
        rows = [("Chain", d.get("chain", ""), False), ("Technical detail", f"{d.get('algorithm')} {short(d.get('hash'), 4)}", True)]
    elif c.id == "retention":
        rows = [("Category", TIER_WORDS[d["tier"]], False), ("Disposal authority", d["authority"], False)]
    elif c.id == "since":
        rows = [("What changed", f"{x['record_id']} is now {x['why']}", False) for x in d.get("sources_changed", [])]
        if d.get("model_status") not in (None, "not registered", "active", "current"):
            rows.append(("AI model", f"{d['model']} marked {d['model_status']}", False))
        rows.append(("Action", "Queued for review by the information manager" if d.get("queued") else "Not queued for review", False))
    elif c.id == "bias":
        rows = [("Sources", f"{s_['record_id']} {s_['title']} ({s_['system']}): {s_['why']}", False) for s_ in d.get("sources", [])]
        rows += [("Narrow statement", f"{s_['text'] or 'This record'}: {s_['why']}", False)
                 for s_ in d.get("statements", []) if s_.get("narrow")]
        if d.get("suggestion"):
            rows.append(("Suggestion", d["suggestion"], False))
        rows.append(("What this checks", d.get("method", ""), False))
    elif c.id == "at_filing":
        rows = [("Sources then", ", ".join(d.get("sources", [])) or "none", True)]
    if rows:
        st.markdown(_kv_rows(rows), unsafe_allow_html=True)


def _doc_function(doc, dtype) -> str:
    """The business function a filed document performs, from the document itself (not a fixed demo string)."""
    title = doc.title.split(",")[0]
    for prefix in ("Briefing: ", "Case note drafted by"):
        if title.startswith(prefix):
            return "Policy briefing" if prefix.startswith("Briefing") else "Case note summary"
    return title.removesuffix(" note").removesuffix(" summary") or dtype.name


def page_records(conn) -> None:
    if st.session_state.get("checking"):
        if st.button("Back to records"):
            st.session_state["checking"] = False
            st.rerun()
        tab_check(conn)
        return
    pol = get_policy()
    views = vw.view_all(conn, pol)
    if st.session_state.get("issued_msg"):
        st.success(st.session_state.pop("issued_msg"))
    ids = [v.record_id for v in views]
    if st.session_state.get("open_next") in ids:
        st.session_state["records_open"] = st.session_state.pop("open_next")
    if views and st.session_state.get("records_open") not in ids:
        full = [v for v in views if v.at_issue and not v.disposed]
        st.session_state["records_open"] = (full or views)[0].record_id
    by_id = {v.record_id: v for v in views}

    left, right = st.columns([1, 2.3], gap="large")
    with left:
        with st.container(border=True):
            a, b = st.columns([1, 1.4], vertical_alignment="center")
            a.markdown("##### Records")
            if b.button("Check a document", type="primary", width="stretch"):
                st.session_state["checking"] = True
                st.rerun()
            if not views:
                st.caption("No records yet. Check a document and file it.")
            else:
                with st.container(height=720, border=False):
                    st.radio("Open a record", ids, key="records_open", label_visibility="collapsed",
                             format_func=lambda i: by_id[i].title.split(" (")[0]
                             + (" :orange[(changed)]" if _row_status(by_id[i])[0] == "Changed since filing" else ""),
                             captions=[f"{_pill_md(*_row_status(x))} · {_when(x.filed)} · {_kept(x)}" for x in views])
    if not views:
        with right:
            st.info("File a document to see its passport.")
        return
    v = by_id[st.session_state["records_open"]]
    p = db.get_passport(conn, v.record_id)
    head, status = vw.headline(v)
    word, _, rest = head.partition(": ")
    bg, fg = TONE[status]
    reviewed = f" · reviewed by {esc(v.reviewer)}" if v.reviewer else ""
    dtype = next((d.name for d in pol.document_types if d.id == v.document_type), None) if v.document_type else None
    who = (f"Filed by {esc(p.agent.person)} on {_local(v.filed).strftime('%d %b %Y, %H:%M')}"
           f" · drafted with {esc(v.model_returned)}{reviewed}" + (f" · document type: {esc(dtype.lower())}" if dtype else ""))
    with right:
        st.markdown(
            f'<div class="rc-article"><div class="rc-eyebrow"><span>Record passport</span>'
            f'<span class="rc-mono">{esc(v.record_id)}</span></div>'
            f'<h1 class="rc-title">{esc(v.title)}</h1>'
            f'<div class="rc-headline" style="background:{bg};color:{fg}" data-testid="headline">'
            f'<b>{esc(word)}:</b> <span>{esc(rest)}</span></div>'
            f'<p class="rc-who">{who}</p>{_passport_card(conn, p, v, pol)}</div>', unsafe_allow_html=True)
        if not v.at_issue and not v.disposed:
            st.markdown('<div class="rc-older">Older record: summary only. It was filed before detailed checks were kept '
                        'with passports, so only the counts are shown.</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="rc-checks-head"><b>Checks done on this record</b>'
                        '<span>Open any check for the detail</span></div>', unsafe_allow_html=True)
            for c in _check_rows(v, p):
                with st.expander(f"{MARK_MD[c.status]}  **{c.name}**  {c.summary}", expanded=c.status == "problem"):
                    _check_detail(conn, c, v, p, pol)
        if not v.disposed:
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
    if SHOW_ALL:
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

    if not SHOW_ALL:
        st.divider()
        source_recall(conn, compact=True)
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

    source_recall(conn)


def source_recall(conn, compact: bool = False) -> None:
    """Mark a source superseded, and recall by source record. On the Sources tab; folded into Recall in the minimal demo."""
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
    if compact:
        st.caption(f"{n['T1'] + n['T2'] + n['T3']} outputs affected: {n['T2']} T2 (decision-informing), "
                   f"{n['T1']} T1, {n['T3']} T3.")
    else:
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


KPI_COLOURS = {"filed_approved": BLUE, "needs_review": ORANGE, "narrow_evidence": ORANGE}


def _kpi_card(k) -> str:
    bg, fg = KPI_COLOURS.get(k.id, GREY)
    bold = ""
    if k.id == "recall_suggested":
        bg, fg = SOLID if k.count else GREY
        bold = "font-weight:700;" if k.count else ""
    return (f'<div class="rc-kpi" style="background:{bg}; color:{fg};"><div class="l" style="{bold}">{esc(k.label)}</div>'
            f'<div class="v">{esc(k.display)}</div><div class="p">{esc(k.plain)}</div></div>')


def tab_dashboard(conn) -> None:
    rep = dashboard.report(conn, get_policy())
    for col, k in zip(st.columns(4), rep.kpis):
        col.markdown(_kpi_card(k), unsafe_allow_html=True)
    for s in rep.model_signals:
        if s.suggested:
            st.markdown(f'<div class="rc-kpi" style="background:{SOLID[0]}; color:{SOLID[1]}; min-height:0; margin-top:10px;">'
                        f'<b>{esc(s.plain)}</b></div>', unsafe_allow_html=True)
            st.caption("Use the Recall tab to act on this signal.")
    left, right = st.columns(2)
    with left:
        st.markdown("**Last 10 filed**")
        if rep.recent:
            st.dataframe(pd.DataFrame([{"Record": r.record_id, "Title": r.title, "Function": r.function, "Tier": r.tier,
                                        "Status": r.status} for r in rep.recent]), hide_index=True, width="stretch")
        else:
            st.caption("None filed yet")
    with right:
        st.markdown("**Risk by business function**")
        if rep.by_function:
            st.dataframe(pd.DataFrame([{"Function": f.function, "Total": f.total, "Needs a person": f.needs_review,
                                        "Bias signals": f.narrow_evidence} for f in rep.by_function]),
                         hide_index=True, width="stretch")
        else:
            st.caption("None yet")
    a, b, c = st.columns(3)
    with a:
        st.markdown("**Latest statements supported by authoritative records**")
        if rep.recent_supported:
            for x in rep.recent_supported[:5]:
                st.caption(f"{x.record_id}: {x.text} (from {', '.join(x.source_record_ids) or 'no record listed'})")
        else:
            st.caption("None issued with stored checks yet")
    with b:
        st.markdown("**AI-written vs human-written statements**")
        if rep.authorship.ai or rep.authorship.human:
            st.caption(rep.authorship.plain)
        else:
            st.caption("None issued with stored checks yet")
    with c:
        st.markdown("**Sources and disposal**")
        st.caption(rep.rot.plain)
        st.caption(rep.disposal_due.plain)
    st.caption("Example data. Every figure comes from passports and records; narrow-evidence signals are rules to look at, "
               "not findings.")


# ---------- main ----------

IM_AREAS = {
    "Dashboard": "Across all retained AI-assisted records: filed, needing review, narrow evidence, recall.",
    "Setup": "Pick a sector preset, how strict each document type is, and which systems count as evidence.",
    "Sources": "Records flagged redundant, obsolete, trivial or draft. Mark a record superseded and see what relied on it.",
    "Recall": "Find every record a faulty or withdrawn AI model produced, by risk, and queue it for review.",
    "Disposal": "Short-term AI logs due for destruction, with holds while a recall is open.",
    "Register": "The active policy, the AI apps registered, and what each tier keeps.",
}
IM_TABS = {"Dashboard": "tab_dashboard", "Setup": "tab_setup", "Sources": "tab_sources", "Recall": "tab_recall",
           "Disposal": "tab_disposal", "Register": "tab_register"}

LOGO = ('<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#1e3a8a" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Record Check"><path d="M6 3h9l3 3v15H6z"/>'
        '<path d="M9 12l2 2 4-4"/></svg>')


def _header() -> None:
    a, b = st.columns([3, 1.4], vertical_alignment="center")
    a.markdown(f'<div class="rc-brand">{LOGO}<span class="n">Record Check</span>'
               '<span class="rc-tag">Example data: all cases, people and records are invented</span></div>',
               unsafe_allow_html=True)
    b.radio("Go to", ["Records", "Information manager"], key="place", horizontal=True, label_visibility="collapsed")


def page_im(conn) -> None:
    rel = sources.reliability(conn, get_policy())
    drag = "".join(f"<div>{esc(d.record_id)} {esc(d.title)}: {esc(d.why)} ({d.outputs} output{'s' if d.outputs != 1 else ''})</div>"
                   for d in rel.drag) or "<div>Every source these outputs cite still counts as evidence.</div>"
    figure = f"{rel.sources_ok} of {rel.with_sources}" if rel.share is not None else "none yet"
    st.markdown(f'<div class="rc-rel"><div class="l"><span class="e">AI search reliability</span>'
                f'<span class="big">{figure}</span><span>retained AI outputs that cite records rest on current '
                f'authoritative records</span><span class="note">These outputs cite records that are still current. '
                f'It says nothing about unsupported statements: see Needs a person on the Dashboard.</span></div>'
                f'<div class="r"><b>Pulling it down</b>{drag}</div></div>',
                unsafe_allow_html=True)
    names = list(IM_TABS) if SHOW_ALL else ["Dashboard", "Recall", "Setup"]
    for name, tab in zip(names, st.tabs(names)):
        with tab:
            st.caption(IM_AREAS[name])
            globals()[IM_TABS[name]](conn)


def main() -> None:
    st.set_page_config(page_title="Record Check", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)
    conn = get_conn()
    with st.sidebar:
        st.markdown(f"Live lookups: **{'on' if online_on() else 'off'}**  \nLLM: **{'on' if llm.available() else 'off'}**")
    get_policy()
    _header()
    if st.session_state.get("place") == "Information manager":
        page_im(conn)
    else:
        page_records(conn)

main()
