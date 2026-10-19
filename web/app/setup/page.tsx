"use client";

import { useEffect, useState } from "react";
import { api, ApiError, OK, ESCALATION_LABELS, TIERS, type S } from "@/lib/ui";
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

  function load(p: Policy) {
    setSaved(p); setDraft(structuredClone(p)); setOrg(p.organisation); setGuidance((p.guidance ?? []).join("\n"));
  }

  useEffect(() => {
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

  async function run(job: () => Promise<void>) {
    setBusy(true); setError(""); setMsg("");
    try { await job(); } catch (e) { setError(explain(e)); } finally { setBusy(false); }
  }
  const who = by.trim() || DEFAULT_BY;
  const fromPreset = (id: string, name: string, after: (p: Policy) => string) => run(async () => {
    const p = await api<Policy>("policy/preset", { json: { preset_id: id, organisation: name, by: who } });
    load(p); setReplaceOk(false); setResetOk(false); setMsg(after(p));
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
    load(p); setMsg(`Policy v${p.version} saved`);
  });

  function addType() {
    const id = newName.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    if (!id) return setAddWarn("Give the document type a name.");
    if (draft!.document_types.some((x) => x.id === id)) return setAddWarn(`A type with id ${id} already exists.`);
    edit((d) => { d.document_types.push({ id, name: newName.trim(), default_tier: newTier, description: "", checks: ["citations", "evidence"], quality: { ...BAR_DEFAULT } }); });
    setNewName(""); setNewTier("T1"); setAddWarn("");
  }

  const row = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0 16px" } as const;
  const check = (label: string, on: boolean, set: (v: boolean) => void) => (
    <label style={{ fontWeight: 400, margin: "8px 0", display: "flex", gap: 8, alignItems: "center" }}>
      <input type="checkbox" checked={on} onChange={(e) => set(e.target.checked)} /> {label}
    </label>
  );
  const input = { width: "100%", padding: 8, font: "inherit", border: "1px solid #9ca3af", borderRadius: 6 } as const;
  const btn = { padding: "8px 16px", font: "inherit", fontWeight: 600, border: "1px solid #9ca3af", borderRadius: 6, background: "#fff", cursor: "pointer" } as const;

  return (
    <>
      <PageHead title="Setup">The rules the information manager sets: document types, quality bars, and which systems count as evidence.</PageHead>
      <p className="muted">The checks and the filing gate read this policy. An AI model may suggest a starting profile, but never sets a threshold, tier or gate.</p>

      <h2>1. Start from your sector</h2>
      <label htmlFor="org">Organisation name</label>
      <input id="org" style={input} value={org} onChange={(e) => setOrg(e.target.value)} />
      <label htmlFor="preset">Sector preset</label>
      <select id="preset" value={presetId} onChange={(e) => setPresetId(e.target.value)}>
        {presets.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select>
      {check("Replace my current policy", replaceOk, setReplaceOk)}
      <button style={btn} disabled={!replaceOk || busy}
        onClick={() => fromPreset(presetId, org.trim() || "Your organisation", (p) => `Policy v${p.version} saved from the ${p.sector_name} preset.`)}>
        Start from this preset
      </button>

      <h2>2. Your document types</h2>
      <p className="muted">Pick the default tier for each type. Exact limits for what blocks filing are under Advanced.</p>
      {draft.document_types.map((t) => (
        <div key={t.id} style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", border: "1px solid #d1d5db", borderRadius: 12, background: "#fff", padding: "8px 14px", margin: "8px 0" }}>
          <b style={{ flex: "1 1 200px" }}>{t.name}</b>
          <select aria-label={`Default tier for ${t.name}`} style={{ width: 220 }} value={t.default_tier} onChange={(e) => editType(t.id, (x) => { x.default_tier = e.target.value as Tier; })}>
            {TIERS.map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
          <button style={btn} disabled={draft.document_types.length <= 1}
            onClick={() => edit((d) => { d.document_types = d.document_types.filter((x) => x.id !== t.id); })}>Remove</button>
        </div>
      ))}
      <form onSubmit={(e) => { e.preventDefault(); addType(); }} style={{ border: "1px solid #d1d5db", borderRadius: 12, background: "#fff", padding: "8px 14px", margin: "12px 0" }}>
        <b>Add a document type</b>
        <div style={row}>
          <div><label htmlFor="nname">Name (e.g. Ministerial brief)</label><input id="nname" style={input} value={newName} onChange={(e) => setNewName(e.target.value)} /></div>
          <div><label htmlFor="ntier">Default tier</label>
            <select id="ntier" value={newTier} onChange={(e) => setNewTier(e.target.value as Tier)}>{TIERS.map((x) => <option key={x}>{x}</option>)}</select></div>
        </div>
        <p><button type="submit" style={btn}>Add document type</button></p>
        {addWarn && <p className="muted" role="alert">{addWarn}</p>}
      </form>
      <h2>3. Which systems count as evidence</h2>
      <p style={{ margin: 0, fontWeight: 600 }}>Systems whose records count as evidence</p>
      {systems.map((s) => <div key={s}>{check(s, draft.authoritative_systems.includes(s), (on) => edit((d) => {
        d.authoritative_systems = on ? [...d.authoritative_systems, s] : d.authoritative_systems.filter((x) => x !== s);
      }))}</div>)}
      <p className="muted">Anything not selected is treated as non-authoritative: records from it can never make a claim &apos;supported&apos;. A saved web page can never be evidence unless you say so.</p>

      <hr style={{ margin: "24px 0", border: 0, borderTop: "1px solid #e5e7eb" }} />
      <label htmlFor="by">Name of the person saving</label>
      <input id="by" style={input} value={by} onChange={(e) => setBy(e.target.value)} />
      <button className="run" onClick={save} disabled={busy}>Save policy</button>
      {error && <p className="error" role="alert">{error}</p>}
      {msg && <p role="status" style={{ background: OK[0], color: OK[1], padding: "8px 12px", borderRadius: 6 }}>{msg}</p>}
@@7@@
      {SHOW_ALL && (
        <details className="card-d" style={{ marginTop: 24 }}>
          <summary>Advanced</summary>
      <label htmlFor="desc">Describe your organisation in a sentence</label>
      <textarea id="desc" style={input} rows={2} value={desc} onChange={(e) => setDesc(e.target.value)}
        placeholder="e.g. A regional hospital using an AI scribe for clinic notes" />
      <p><button style={btn} onClick={suggest} disabled={busy}>Suggest a profile</button></p>
      {notice && <p className="muted" role="status">{notice}</p>}
      {suggestion && (
        <div style={{ background: "#eff6ff", padding: "8px 12px", borderRadius: 6 }}>
          <p>Suggested: <b>{suggestion.preset.name}</b> for {suggestion.organisation}. {suggestion.preset.description} This is a starting point; you confirm every field below.</p>
          <button style={btn} onClick={() => { setOrg(suggestion.organisation); setPresetId(suggestion.preset.id); }}>Use this suggestion</button>
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
            <input id={`${k}-name`} style={input} value={t.name} onChange={(e) => editType(t.id, (x) => { x.name = e.target.value; })} />
            <label htmlFor={`${k}-desc`}>Description</label>
            <input id={`${k}-desc`} style={input} value={t.description} onChange={(e) => editType(t.id, (x) => { x.description = e.target.value; })} />
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
                <input id={`${k}-mu`} type="number" min={0} max={100} style={input} value={q.max_unsupported}
                  onChange={(e) => editBar(t.id, (b) => { b.max_unsupported = clamp(e.target.value, 0, 100); })} />
                {check("Unlimited weak claims", q.max_weak == null, (on) => editBar(t.id, (b) => { b.max_weak = on ? null : 0; }))}
                {q.max_weak != null && <>
                  <label htmlFor={`${k}-mw`}>Weak claims allowed (more = needs attention)</label>
                  <input id={`${k}-mw`} type="number" min={0} max={100} style={input} value={q.max_weak}
                    onChange={(e) => editBar(t.id, (b) => { b.max_weak = clamp(e.target.value, 0, 100); })} />
                </>}
              </div>
              <div>
                <label htmlFor={`${k}-mc`}>Contradicted claims allowed (more = blocked)</label>
                <input id={`${k}-mc`} type="number" min={0} max={100} style={input} value={q.max_contradicted}
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
            <button style={btn} disabled={draft.document_types.length <= 1}
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
      <input id="ret" type="number" min={1} max={3650} style={input} value={tr.retention_days?.T0 ?? 90}
        onChange={(e) => edit((d) => { d.tier_rules.retention_days = { ...d.tier_rules.retention_days, T0: clamp(e.target.value, 1, 3650) }; })} />

      <h2>Guidance this policy cites</h2>
      <label htmlFor="guid">One per line</label>
      <textarea id="guid" style={input} rows={4} value={guidance} onChange={(e) => setGuidance(e.target.value)} />

      <div style={{ marginTop: 16 }}>
        {check("Confirm: discard my policy and go back to the preset defaults", resetOk, setResetOk)}
        <button style={btn} disabled={!resetOk || busy}
          onClick={() => fromPreset(presets.some((p) => p.id === saved.sector) ? saved.sector : presets[0].id, saved.organisation,
            (p) => `Policy v${p.version} saved (reset to ${p.sector_name || presetName(p.sector)} defaults)`)}>
          Reset to preset defaults
        </button>
      </div>
        </details>
      )}
    </>
  );
}
