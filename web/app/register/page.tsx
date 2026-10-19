"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ATTN, BAD, ESCALATION_LABELS, GREY, OK, Pill, TIERS, TIER_COLOURS, type S } from "@/lib/ui";
import PageHead from "../page-head";

const STATUS: Record<string, [string, typeof OK]> = {
  current: ["✓ current", OK], draft: ["! draft", ATTN], superseded: ["✕ superseded", BAD], disposed: ["– disposed", GREY],
};
const yes = (b: boolean) => <Pill text={b ? "✓ yes" : "✕ no"} colours={b ? OK : BAD} />;
const LABEL_NOTE: Record<string, string> = { redundant: "Duplicate of another record", obsolete: "Superseded or out of date", trivial: "Little business value", draft: "Not yet final" };

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
  const tierPill = (t: string) => <Pill text={t} colours={TIER_COLOURS[t]} />;
  const rid = (id: string) => <Link className="rid mono" href={`/records?id=${encodeURIComponent(id)}`}>{id}</Link>;
  const overdue = (health.counts as Record<string, number>)["overdue"];
  const tiles: [string, string, number, string][] = [
    ["blue", "Source records", health.total, "In the register"],
    ["ok", "Eligible as evidence", health.eligible, `Of ${health.total} can support a claim`],
    ...labels.map((l): [string, string, number, string] => [(health.counts[l] ?? 0) > 0 ? (l === "draft" ? "attn" : "bad") : "grey", l[0].toUpperCase() + l.slice(1), health.counts[l] ?? 0, LABEL_NOTE[l]]),
    ...(overdue != null ? [["bad", "Overdue", overdue, "Past their review date"] as [string, string, number, string]] : []),
  ];

  return (
    <>
      <PageHead title="Register">The active policy, authoritative records, registered AI apps and retention rules, in one place for audit.</PageHead>

      <section className="panel polcard" aria-label="Active policy">
        <div>
          <span className="eyebrow" style={{ color: "var(--teal-ink)" }}>Active policy</span>
          <span className="org">{pol.organisation}</span>
          <span className="meta">
            <span>{pol.sector_name}</span><span className="vpill">v{pol.version}</span>
            <span>updated by {pol.updated_by}{pol.updated_at ? ` at ${pol.updated_at.replace("T", " ").slice(0, 16)} UTC` : ""}</span>
          </span>
          <span className="muted" style={{ marginTop: 6 }}>Document types: {pol.document_types.map((d) => d.name).join(", ")}.</span>
          <span className="muted">Authoritative systems: {pol.authoritative_systems.join(", ") || "none"}.</span>
        </div>
        <div>
          <h3>Guidance this policy cites</h3>
          {pol.guidance?.length ? <ul className="yb">{pol.guidance.map((g) => <li key={g}>{g}</li>)}</ul> : <p className="muted" style={{ margin: 0 }}>None</p>}
        </div>
      </section>

      <section className="panel panel-pad rsec" aria-label="Authoritative records">
        <h2>Authoritative records</h2>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Id</th><th>Title</th><th>System</th><th>Status</th><th>Authoritative</th><th>Created</th><th>Created by</th></tr></thead>
            <tbody>{records.map((r) => (
              <tr key={r.id}>
                <td>{rid(r.id)}</td><td>{r.title}</td><td>{r.system}</td>
                <td><Pill text={(STATUS[r.status] ?? [r.status, GREY])[0]} colours={(STATUS[r.status] ?? [r.status, GREY])[1]} /></td>
                <td>{yes(r.authoritative)}</td><td className="mono">{r.created}</td><td>{r.created_by}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <div className="cards">
        <section className="panel" aria-label="Registered AI apps">
          <h3>Registered AI apps</h3>
          <table className="tbl">
            <thead><tr><th>App id</th><th>Name</th><th>Default tier</th></tr></thead>
            <tbody>{Object.entries(tr.app_defaults).map(([a, t]) => <tr key={a}><td className="mono">{a}</td><td>{tr.app_names?.[a] ?? a}</td><td>{tierPill(t)}</td></tr>)}</tbody>
          </table>
        </section>
        <section className="panel" aria-label="Escalation rules">
          <h3>Escalation rules</h3>
          <table className="tbl">
            <thead><tr><th>Rule</th><th>Raises tier to at least</th></tr></thead>
            <tbody>{Object.entries(tr.escalations).map(([k, v]) => <tr key={k}><td>{ESCALATION_LABELS[k] ?? k}</td><td>{tierPill(v)}</td></tr>)}</tbody>
          </table>
        </section>
        <section className="panel" aria-label="Retention by tier">
          <h3>Retention by tier</h3>
          <table className="tbl">
            <thead><tr><th>Tier</th><th>Retention</th></tr></thead>
            <tbody>{retentionOrder.map((t) => <tr key={t}><td>{tierPill(t)}</td><td>{tr.retention[t]}</td></tr>)}</tbody>
          </table>
          <p className="muted">Policy version: {tr.policy_version}</p>
        </section>
      </div>

      <h2 className="sub-h" style={{ fontSize: 13, margin: "28px 0 10px" }}>Source record health</h2>
      <div className="dtiles">
        {tiles.map(([c, k, v, cap]) => <div key={k} className={`dtile ${c}`}><span className="l">{k}</span><span className="v">{v}</span><span className="p">{cap}</span></div>)}
      </div>
      <section className="panel panel-pad" aria-label="Source record health detail">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Record id</th><th>Title</th><th>System</th><th>Labels</th><th>Can count as evidence</th><th>Notes</th></tr></thead>
            <tbody>{health.items.map((i) => (
              <tr key={i.record_id}>
                <td>{rid(i.record_id)}</td><td>{i.title}</td><td>{i.system}</td>
                <td>{(i.labels ?? []).length ? (i.labels ?? []).map((l) => <span key={l}><Pill text={`! ${l}`} colours={l === "draft" ? ATTN : BAD} />{" "}</span>) : <Pill text="✓ none" colours={OK} />}</td>
                <td>{yes(i.eligible)}</td><td>{(i.notes ?? []).join(" ")}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className="muted">Records flagged redundant, obsolete, trivial or draft cannot make a claim supported. The information manager decides what to fix.</p>
      </section>
    </>
  );
}
