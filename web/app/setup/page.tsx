"use client";

import { useEffect, useState } from "react";
import { api, ApiError, ESCALATION_LABELS, TIERS, type S } from "@/lib/ui";
import PageHead from "../page-head";

type Policy = S["Policy"];
type DocType = S["DocumentType"];
type Tier = (typeof TIERS)[number];
// Advanced settings (suggest, exact limits, apps, guidance, reset) show only in a build with NEXT_PUBLIC_SHOW_ALL=1.
const SHOW_ALL = process.env.NEXT_PUBLIC_SHOW_ALL === "1";
const DEFAULT_BY = "Information manager";
const BAR_DEFAULT: S["QualityBar"] = {
  max_unsupported: 0, max_contradicted: 0, citations_not_found_blocks: true,
  citations_mismatch_attention: true, citations_not_checked_attention: true, require_reviewer: true,
};

/** Readable text for an API error: a string, or a FastAPI validation array. */
function explain(e: unknown): string {
  if (e instanceof ApiError && Array.isArray(e.detail)) {
    return e.detail.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(" / ")}: ${d.msg}`).join("; ");
  }
  return (e as Error).message;
}
const clamp = (v: string, lo: number, hi: number) => Math.min(hi, Math.max(lo, Math.round(Number(v)) || 0));

export default function Setup() {
  const [saved, setSaved] = useState<Policy | null>(null);
  const [draft, setDraft] = useState<Policy | null>(null);
  const [presets, setPresets] = useState<S["SectorPreset"][]>([]);
  const [systems, setSystems] = useState<string[]>([]);
  const [org, setOrg] = useState("");
  const [presetId, setPresetId] = useState("");
  const [desc, setDesc] = useState("");
  const [suggestion, setSuggestion] = useState<S["Suggestion"] | null>(null);
  const [notice, setNotice] = useState("");
  const [replaceOk, setReplaceOk] = useState(false);
  const [resetOk, setResetOk] = useState(false);
  const [by, setBy] = useState(DEFAULT_BY);
  const [guidance, setGuidance] = useState("");
  const [newName, setNewName] = useState("");
  const [newTier, setNewTier] = useState<Tier>("T1");
  const [addWarn, setAddWarn] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [levels, setLevels] = useState<S["LevelsResponse"] | null>(null);
  const [picked, setPicked] = useState<Record<string, string>>({});  // strictness chosen in this draft, by type id

  function load(p: Policy) {
    setSaved(p); setDraft(structuredClone(p)); setOrg(p.organisation); setGuidance((p.guidance ?? []).join("\n"));
  }

  const loadLevels = () => api<S["LevelsResponse"]>("policy/levels").then((l) => { setLevels(l); setPicked({}); }).catch(() => {});

  useEffect(() => {
    loadLevels();
    Promise.all([api<Policy>("policy"), api<S["SectorPreset"][]>("presets"), api<S["SourceRecord"][]>("records")])
      .then(([p, ps, recs]) => {
        load(p); setPresets(ps);
        setPresetId(ps.some((x) => x.id === p.sector) ? p.sector : ps[0]?.id ?? "");
        setSystems([...new Set([...recs.map((r) => r.system), ...p.authoritative_systems])].sort());
      })
      .catch((e) => setError(explain(e)));
  }, []);

  if (!draft || !saved) return error ? <p className="error" role="alert">{error}</p> : <p className="muted">Loading...</p>;

  const edit = (fn: (d: Policy) => void) => setDraft((cur) => { const n = structuredClone(cur!); fn(n); return n; });
  const editType = (id: string, fn: (t: DocType) => void) => edit((d) => { const t = d.document_types.find((x) => x.id === id); if (t) fn(t); });
  const editBar = (id: string, fn: (q: S["QualityBar"]) => void) => editType(id, (t) => { t.quality = { ...BAR_DEFAULT, ...t.quality }; fn(t.quality); });
  const presetName = (id: string) => presets.find((p) => p.id === id)?.name ?? id;
  const tr = draft.tier_rules;
  const levelOf = (id: string) => picked[id] ?? levels?.document_types.find((x) => x.id === id)?.level ?? "standard";
  const levelDef = (id: string) => levels?.levels.find((l) => l.id === id);
  function setLevel(typeId: string, id: string) {
    const lv = levelDef(id);
    if (!lv) return;
    editType(typeId, (t) => { t.quality = lv.quality as S["QualityBar"]; t.checks = lv.checks as DocType["checks"]; });
    setPicked((c) => ({ ...c, [typeId]: id }));
  }

  async function run(job: () => Promise<void>) {
    setBusy(true); setError(""); setMsg("");
    try { await job(); } catch (e) { setError(explain(e)); } finally { setBusy(false); }
  }
  const who = by.trim() || DEFAULT_BY;
  const fromPreset = (id: string, name: string, after: (p: Policy) => string) => run(async () => {
    const p = await api<Policy>("policy/preset", { json: { preset_id: id, organisation: name, by: who } });
    load(p); setReplaceOk(false); setResetOk(false); setMsg(after(p)); await loadLevels();
  });

  const suggest = () => run(async () => {
    const s = await api<S["Suggestion"] | null>("policy/suggest", { json: { description: desc } });
    setSuggestion(s); setNotice(s ? "" : "Suggestions need the LLM; pick a preset instead.");
  });

  const save = () => run(async () => {
    const body = structuredClone(draft);
    body.organisation = org.trim() || body.organisation;
    body.guidance = guidance.split("\n").map((x) => x.trim()).filter(Boolean);
    const p = await api<Policy>("policy", { method: "PUT", json: { policy: body, by: who } });
    load(p); setMsg(`Policy v${p.version} saved`); await loadLevels();
  });

  function addType() {
    const id = newName.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    if (!id) return setAddWarn("Give the document type a name.");
    if (draft!.document_types.some((x) => x.id === id)) return setAddWarn(`A type with id ${id} already exists.`);
    const std = levelDef("standard");
    edit((d) => { d.document_types.push({ id, name: newName.trim(), default_tier: newTier, description: "", checks: (std?.checks ?? ["citations", "evidence"]) as DocType["checks"], quality: (std?.quality as S["QualityBar"] | undefined) ?? { ...BAR_DEFAULT } }); });
    setPicked((c) => ({ ...c, [id]: "standard" }));
    setNewName(""); setNewTier("T1"); setAddWarn("");
  }

  const row = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0 16px" } as const;
  const check = (label: string, on: boolean, set: (v: boolean) => void) => (
    <label style={{ fontWeight: 400, margin: "8px 0", display: "flex", gap: 8, alignItems: "center" }}>
      <input type="checkbox" checked={on} onChange={(e) => set(e.target.checked)} style={{ width: 16, height: 16, accentColor: "var(--teal)" }} /> {label}
    </label>
  );
  const Sec = ({ n, title, children }: { n: number; title: string; children: React.ReactNode }) => (
    <>
      <div className="sec"><span className="num" aria-hidden="true">{n}</span><h2>{title}</h2></div>
      <p className="sec-note">{children}</p>
    </>
  );

  return (
    <>
      <PageHead title="Setup">The rules the information manager sets: document types, quality bars, and which systems count as evidence.</PageHead>
      <p className="muted" style={{ margin: "-8px 0 0" }}>The checks and the filing gate read this policy. An AI model may suggest a starting profile, but never sets a threshold, tier or gate.</p>

      <Sec n={1} title="Start from your sector">Pick a sector preset as a starting point. These are our starting points, not a regulator&apos;s rules.</Sec>
      <section className="panel panel-pad" aria-label="Start from your sector">
        <div className="field-row">
          <div><label htmlFor="org" style={{ marginTop: 0 }}>Organisation name</label>
            <input id="org" value={org} onChange={(e) => setOrg(e.target.value)} /></div>
          <div><label htmlFor="preset" style={{ marginTop: 0 }}>Sector preset</label>
            <select id="preset" value={presetId} onChange={(e) => setPresetId(e.target.value)}>
              {presets.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select></div>
        </div>
        {check("Replace my current policy", replaceOk, setReplaceOk)}
        <button className="btn-line" disabled={!replaceOk || busy}
          onClick={() => fromPreset(presetId, org.trim() || "Your organisation", (p) => `Policy v${p.version} saved from the ${p.sector_name} preset.`)}>
          Start from this preset
        </button>
      </section>

      <Sec n={2} title="Your document types">Pick how strict each type is, and its default tier. Exact limits for what blocks filing are under Advanced.</Sec>
      <div className="dtypes">
        {draft.document_types.map((t) => {
          const cur = levelOf(t.id);
          const lv = levelDef(cur);
          const summary = lv?.summary ?? levels?.document_types.find((x) => x.id === t.id)?.summary;
          return (
            <div key={t.id} className="dtype">
              <div className="top">
                <b>{t.name}</b>
                <button className="btn-line small" disabled={draft.document_types.length <= 1} aria-label={`Remove ${t.name}`}
                  onClick={() => edit((d) => { d.document_types = d.document_types.filter((x) => x.id !== t.id); })}>Remove</button>
              </div>
              <div className="ctl">
                <div>
                  <label htmlFor={`lv-${t.id}`}>Strictness</label>
                  <select id={`lv-${t.id}`} aria-label={`Strictness for ${t.name}`} value={cur} onChange={(e) => setLevel(t.id, e.target.value)} disabled={!levels}>
                    {levels?.levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                    {cur === "custom" && <option value="custom" disabled>Custom</option>}
                  </select>
                </div>
                <div>
                  <label htmlFor={`tr-${t.id}`}>Default tier</label>
                  <select id={`tr-${t.id}`} aria-label={`Default tier for ${t.name}`} value={t.default_tier} onChange={(e) => editType(t.id, (x) => { x.default_tier = e.target.value as Tier; })}>
                    {TIERS.map((x) => <option key={x} value={x}>{x}</option>)}
                  </select>
                </div>
              </div>
              {summary && <p>{summary}</p>}
              {lv && <p className="use">{lv.use_for}</p>}
            </div>
          );
        })}
        <form className="dtype add" onSubmit={(e) => { e.preventDefault(); addType(); }}>
          <div className="top"><b>Add a document type</b></div>
          <div className="ctl">
            <div><label htmlFor="nname">Name (e.g. Ministerial brief)</label><input id="nname" value={newName} onChange={(e) => setNewName(e.target.value)} /></div>
            <div><label htmlFor="ntier">Default tier</label>
              <select id="ntier" value={newTier} onChange={(e) => setNewTier(e.target.value as Tier)}>{TIERS.map((x) => <option key={x}>{x}</option>)}</select></div>
          </div>
          <div><button type="submit" className="btn-line">Add document type</button></div>
          {addWarn && <p className="muted" role="alert">{addWarn}</p>}
        </form>
      </div>

      <Sec n={3} title="Which systems count as evidence">Anything not selected is treated as non-authoritative: records from it can never make a claim &apos;supported&apos;. A saved web page can never be evidence unless you say so.</Sec>
      <section className="panel panel-pad" aria-label="Evidence systems">
        <div className="sysgrid" role="group" aria-label="Systems whose records count as evidence">
          {systems.map((s) => {
            const on = draft.authoritative_systems.includes(s);
            return (
              <label key={s} className={`syschip${on ? " on" : ""}`}>
                <input type="checkbox" checked={on} onChange={(e) => edit((d) => {
                  d.authoritative_systems = e.target.checked ? [...d.authoritative_systems, s] : d.authoritative_systems.filter((x) => x !== s);
                })} />
                {s}<span className="tag">{on ? "✓ evidence" : "– not evidence"}</span>
              </label>
            );
          })}
        </div>
      </section>

      <section className="approve" aria-label="Save policy" style={{ marginTop: 24 }}>
        <h2>Save policy</h2>
        <p>The version goes up and the change is written to the audit trail with your name.</p>
        <div className="row2">
          <div><label htmlFor="by">Name of the person saving</label>
            <input id="by" value={by} onChange={(e) => setBy(e.target.value)} /></div>
          <button className="btn-mag" onClick={save} disabled={busy}>Save policy</button>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {msg && <p role="status" className="ok-box"><span className="ic" aria-hidden="true">✓</span>{msg}</p>}
      </section>
      {SHOW_ALL && (
        <details className="panel fold">
          <summary>Advanced</summary>
          <div className="fold-body">
      <label htmlFor="desc">Describe your organisation in a sentence</label>
      <textarea id="desc" rows={2} value={desc} onChange={(e) => setDesc(e.target.value)}
        placeholder="e.g. A regional hospital using an AI scribe for clinic notes" />
      <p><button className="btn-line" onClick={suggest} disabled={busy}>Suggest a profile</button></p>
      {notice && <p className="muted" role="status">{notice}</p>}
      {suggestion && (
        <div style={{ background: "#eff6ff", padding: "8px 12px", borderRadius: 6 }}>
          <p>Suggested: <b>{suggestion.preset.name}</b> for {suggestion.organisation}. {suggestion.preset.description} This is a starting point; you confirm every field below.</p>
          <button className="btn-line" onClick={() => { setOrg(suggestion.organisation); setPresetId(suggestion.preset.id); }}>Use this suggestion</button>
        </div>
      )}
      <h2>Exact limits per document type</h2>
      <p className="muted">Each type has a quality bar. Going over a &apos;blocked&apos; limit stops filing; going over an &apos;attention&apos; limit asks for a closer look.</p>
      {draft.document_types.map((t) => {
        const q = { ...BAR_DEFAULT, ...t.quality };
        const k = `t-${t.id}`;
        return (
          <details key={t.id} style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: "8px 12px", margin: "8px 0" }}>
            <summary style={{ cursor: "pointer", fontWeight: 600 }}>{t.name} ({t.id}, default {t.default_tier})</summary>
            <label htmlFor={`${k}-name`}>Name</label>
            <input id={`${k}-name`} value={t.name} onChange={(e) => editType(t.id, (x) => { x.name = e.target.value; })} />
            <label htmlFor={`${k}-desc`}>Description</label>
            <input id={`${k}-desc`} value={t.description} onChange={(e) => editType(t.id, (x) => { x.description = e.target.value; })} />
            <label htmlFor={`${k}-tier`}>Default tier</label>
            <select id={`${k}-tier`} value={t.default_tier} onChange={(e) => editType(t.id, (x) => { x.default_tier = e.target.value as Tier; })}>
              {TIERS.map((x) => <option key={x}>{x}</option>)}
            </select>
            <p style={{ margin: "16px 0 0", fontWeight: 600 }}>Checks that run</p>
            {(["citations", "evidence"] as const).map((c) =>
              <span key={c} style={{ marginRight: 16 }}>{check(c, (t.checks ?? []).includes(c), (on) => editType(t.id, (x) => {
                x.checks = (["citations", "evidence"] as const).filter((n) => (n === c ? on : (x.checks ?? []).includes(n)));
              }))}</span>)}
            <div style={row}>
              <div>
                <label htmlFor={`${k}-mu`}>Unsupported claims allowed (more = blocked)</label>
                <input id={`${k}-mu`} type="number" min={0} max={100} value={q.max_unsupported}
                  onChange={(e) => editBar(t.id, (b) => { b.max_unsupported = clamp(e.target.value, 0, 100); })} />
                {check("Unlimited weak claims", q.max_weak == null, (on) => editBar(t.id, (b) => { b.max_weak = on ? null : 0; }))}
                {q.max_weak != null && <>
                  <label htmlFor={`${k}-mw`}>Weak claims allowed (more = needs attention)</label>
                  <input id={`${k}-mw`} type="number" min={0} max={100} value={q.max_weak}
                    onChange={(e) => editBar(t.id, (b) => { b.max_weak = clamp(e.target.value, 0, 100); })} />
                </>}
              </div>
              <div>
                <label htmlFor={`${k}-mc`}>Contradicted claims allowed (more = blocked)</label>
                <input id={`${k}-mc`} type="number" min={0} max={100} value={q.max_contradicted}
                  onChange={(e) => editBar(t.id, (b) => { b.max_contradicted = clamp(e.target.value, 0, 100); })} />
                {check("No minimum supported share", q.min_supported_share == null, (on) => editBar(t.id, (b) => { b.min_supported_share = on ? null : 0.6; }))}
                {q.min_supported_share != null && <>
                  <label htmlFor={`${k}-ms`}>Minimum share of supported claims: {q.min_supported_share.toFixed(2)}</label>
                  <input id={`${k}-ms`} type="range" min={0} max={1} step={0.05} style={{ width: "100%" }} value={q.min_supported_share}
                    onChange={(e) => editBar(t.id, (b) => { b.min_supported_share = Math.min(1, Math.max(0, Number(e.target.value))); })} />
                </>}
              </div>
            </div>
            {check("A citation that cannot be found blocks filing", q.citations_not_found_blocks, (on) => editBar(t.id, (b) => { b.citations_not_found_blocks = on; }))}
            {check("A citation with mismatched details needs attention", q.citations_mismatch_attention, (on) => editBar(t.id, (b) => { b.citations_mismatch_attention = on; }))}
            {check("A citation that could not be checked needs attention", q.citations_not_checked_attention, (on) => editBar(t.id, (b) => { b.citations_not_checked_attention = on; }))}
            {check("T2 and T3 need a named reviewer", q.require_reviewer, (on) => editBar(t.id, (b) => { b.require_reviewer = on; }))}
            <button className="btn-line" disabled={draft.document_types.length <= 1}
              onClick={() => edit((d) => { d.document_types = d.document_types.filter((x) => x.id !== t.id); })}>
              Remove this document type
            </button>
          </details>
        );
      })}
      <h2>Apps and tiers</h2>
      {Object.keys(tr.app_defaults).map((a) => (
        <div key={a}>
          <label htmlFor={`app-${a}`}>{tr.app_names?.[a] ?? a}: default tier</label>
          <select id={`app-${a}`} value={tr.app_defaults[a]} onChange={(e) => edit((d) => { d.tier_rules.app_defaults[a] = e.target.value as Tier; })}>
            {TIERS.map((x) => <option key={x}>{x}</option>)}
          </select>
        </div>
      ))}
      <p>Escalations (read-only here): {Object.entries(tr.escalations).map(([k, v]) => `${ESCALATION_LABELS[k] ?? k} raises to at least ${v}`).join("; ")}</p>
      <label htmlFor="ret">T0 log retention (days)</label>
      <input id="ret" type="number" min={1} max={3650} value={tr.retention_days?.T0 ?? 90}
        onChange={(e) => edit((d) => { d.tier_rules.retention_days = { ...d.tier_rules.retention_days, T0: clamp(e.target.value, 1, 3650) }; })} />

      <h2>Guidance this policy cites</h2>
      <label htmlFor="guid">One per line</label>
      <textarea id="guid" rows={4} value={guidance} onChange={(e) => setGuidance(e.target.value)} />

      <div style={{ marginTop: 16 }}>
        {check("Confirm: discard my policy and go back to the preset defaults", resetOk, setResetOk)}
        <button className="btn-line" disabled={!resetOk || busy}
          onClick={() => fromPreset(presets.some((p) => p.id === saved.sector) ? saved.sector : presets[0].id, saved.organisation,
            (p) => `Policy v${p.version} saved (reset to ${p.sector_name || presetName(p.sector)} defaults)`)}>
          Reset to preset defaults
        </button>
      </div>
          </div>
        </details>
      )}
    </>
  );
}
