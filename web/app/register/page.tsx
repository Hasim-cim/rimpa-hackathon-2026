"use client";

import { useEffect, useState } from "react";
import { api, ESCALATION_LABELS, GREY, Pill, TIERS, type S } from "@/lib/ui";
import PageHead from "../page-head";

const yn = (b: boolean) => (b ? "yes" : "no");

export default function Register() {
  const [pol, setPol] = useState<S["Policy"] | null>(null);
  const [records, setRecords] = useState<S["SourceRecord"][]>([]);
  const [health, setHealth] = useState<S["SourceHealthReport"] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<S["Policy"]>("policy"), api<S["SourceRecord"][]>("records"), api<S["SourceHealthReport"]>("sources/health")])
      .then(([p, r, h]) => { setPol(p); setRecords(r); setHealth(h); })
      .catch((e) => setError(e.message));
  }, []);

  if (!pol || !health) return error ? <p className="error" role="alert">{error}</p> : <p className="muted">Loading...</p>;
  const tr = pol.tier_rules;
  const labels = ["redundant", "obsolete", "trivial", "draft"];
  const retentionOrder = [...TIERS, ...Object.keys(tr.retention).filter((t) => !(TIERS as readonly string[]).includes(t))].filter((t) => t in tr.retention);

  return (
    <>
      <PageHead title="Register">The active policy, authoritative records, registered AI apps and retention rules, in one place for audit.</PageHead>
      <h2 style={{ marginTop: 0 }}>Active policy</h2>
      <p><b>{pol.organisation}</b> | {pol.sector_name} | version {pol.version} | updated by {pol.updated_by}
        {pol.updated_at ? ` at ${pol.updated_at.replace("T", " ").slice(0, 16)} UTC` : ""}</p>
      <p>Guidance this policy cites: {pol.guidance?.length ? pol.guidance.join("; ") : "none"}</p>
      <p className="muted">Document types: {pol.document_types.map((d) => d.name).join(", ")}. Authoritative systems: {pol.authoritative_systems.join(", ") || "none"}.</p>

      <h2>Authoritative records</h2>
      <table>
        <thead><tr><th>Id</th><th>Title</th><th>System</th><th>Status</th><th>Authoritative</th><th>Created</th><th>Created by</th></tr></thead>
        <tbody>{records.map((r) => (
          <tr key={r.id}><td>{r.id}</td><td>{r.title}</td><td>{r.system}</td><td>{r.status}</td><td>{yn(r.authoritative)}</td><td>{r.created}</td><td>{r.created_by}</td></tr>
        ))}</tbody>
      </table>

      <h2>Registered AI apps</h2>
      <table>
        <thead><tr><th>App id</th><th>Name</th><th>Default tier</th></tr></thead>
        <tbody>{Object.entries(tr.app_defaults).map(([a, t]) => <tr key={a}><td>{a}</td><td>{tr.app_names?.[a] ?? a}</td><td>{t}</td></tr>)}</tbody>
      </table>

      <h2>Escalation rules</h2>
      <table>
        <thead><tr><th>Rule</th><th>Raises tier to at least</th></tr></thead>
        <tbody>{Object.entries(tr.escalations).map(([k, v]) => <tr key={k}><td>{ESCALATION_LABELS[k] ?? k}</td><td>{v}</td></tr>)}</tbody>
      </table>

      <h2>Retention by tier</h2>
      <table>
        <thead><tr><th>Tier</th><th>Retention</th></tr></thead>
        <tbody>{retentionOrder.map((t) => <tr key={t}><td>{t}</td><td>{tr.retention[t]}</td></tr>)}</tbody>
      </table>
      <p className="muted">Policy version: {tr.policy_version}</p>

      <h2>Source record health</h2>
      <div className="counts">
        <div><b>{health.total}</b>Source records</div>
        <div><b>{health.eligible}</b>Eligible as evidence</div>
        {labels.map((l) => <div key={l}><b>{health.counts[l] ?? 0}</b>{l[0].toUpperCase() + l.slice(1)}</div>)}
      </div>
      <table>
        <thead><tr><th>Record id</th><th>Title</th><th>System</th><th>Labels</th><th>Can count as evidence</th><th>Notes</th></tr></thead>
        <tbody>{health.items.map((i) => (
          <tr key={i.record_id}>
            <td>{i.record_id}</td><td>{i.title}</td><td>{i.system}</td>
            <td>{(i.labels ?? []).map((l) => <span key={l}><Pill text={l} colours={GREY} />{" "}</span>)}</td>
            <td>{yn(i.eligible)}</td><td>{(i.notes ?? []).join(" ")}</td>
          </tr>
        ))}</tbody>
      </table>
      <p className="muted">Records flagged redundant, obsolete, trivial or draft cannot make a claim supported. The information manager decides what to fix.</p>
    </>
  );
}
