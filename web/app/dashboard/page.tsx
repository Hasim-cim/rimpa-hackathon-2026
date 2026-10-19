"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Reliability from "../reliability";
import { api, ATTN, GREY, OK, Pill, type S } from "@/lib/ui";
import PageHead from "../page-head";

// Every figure and sentence comes from GET /api/dashboard; nothing is computed here except bar widths and a few sums.
const pct = (n: number, total: number) => (total ? Math.round((100 * n) / total) : 0);
const tail = (label: string) => {
  const t = label.includes(": ") ? label.slice(label.indexOf(": ") + 2).replace(/^\d+ of \d+ /, "") : label;
  return t[0].toUpperCase() + t.slice(1);
};
const head = (label: string) => (label.includes(":") ? label.slice(0, label.indexOf(":")) : label);

function Tile({ k, flagged }: { k: S["KpiTile"]; flagged: S["ModelSignal"][] }) {
  if (k.id === "recall_suggested") {
    const s = flagged[0];
    return (
      <div className="kpi dark">
        <div className="l">Model recall</div>
        <span className="ic" aria-hidden="true">↺</span>
        <div className="v">{k.count} of {k.total}</div>
        <div className="mid">{s ? s.model_id : "No model flagged"}</div>
        <div className="p">{s && s.rate != null
          ? `${Math.round(s.rate * 100)}% of references not found (${s.references_not_found} of ${s.references_checked}). Your call.`
          : "Flagged when too many of a model's checked references are not found. Your call."}</div>
      </div>
    );
  }
  const cls = k.id === "filed_approved" ? "ok" : k.id === "needs_review" ? "bad" : k.id === "narrow_evidence" ? "attn" : "quiet";
  const icon = cls === "ok" ? "✓" : cls === "bad" ? "!" : "▲";
  const title = k.id === "filed_approved" ? "Approved" : head(k.label);
  return (
    <div className={`kpi ${cls}`}>
      <div className="l">{title}</div>
      <span className="ic" aria-hidden="true">{icon}</span>
      <div className="v">{k.percent == null ? "none yet" : `${Math.round(k.percent)}%`}</div>
      <div className="n">{k.count} of {k.total} passports</div>
      <div className="p">{k.id === "filed_approved" ? k.label : tail(k.label)}</div>
    </div>
  );
}

function ByFunction({ rows }: { rows: S["FunctionRow"][] }) {
  if (!rows.length) return <p className="muted">None yet</p>;
  const needs = rows.reduce((a, f) => a + f.needs_review, 0);
  const narrow = rows.reduce((a, f) => a + f.narrow_evidence, 0);
  // A passport can carry both flags, so the yellow segment never takes more than the room left after the magenta one.
  const seg = rows.map((f) => {
    const m = f.needs_review, y = Math.max(0, Math.min(f.narrow_evidence, f.total - m)), g = f.total - m - y;
    return { f, m, y, g };
  });
  const noFlag = seg.reduce((a, s) => a + s.g, 0);
  const max = Math.max(1, ...rows.map((f) => f.total));
  return (
    <>
      <div className="fn-legend">
        <span><i style={{ background: "var(--magenta)" }} />Needs a person ({needs})</span>
        <span><i style={{ background: "var(--yellow)" }} />Narrow evidence ({narrow})</span>
        <span><i style={{ background: "#d3d6d9" }} />No flag ({noFlag})</span>
      </div>
      <div className="fn-row fn-head" aria-hidden="true"><span>Function</span><span>Items</span><span style={{ textAlign: "right" }}>% flagged</span></div>
      {seg.map(({ f, m, y, g }) => {
        const flaggedPct = pct(m + y, f.total);
        return (
          <div className="fn-row" key={f.function}
            title={`${f.function}: ${f.total} passports, ${f.needs_review} need a person, ${f.narrow_evidence} rest on narrow evidence`}>
            <span>{f.function}</span>
            <div className="stacked" style={{ width: `${(f.total / max) * 100}%`, minWidth: 40 }} role="img"
              aria-label={`${f.total} passports: ${f.needs_review} need a person, ${f.narrow_evidence} narrow evidence, ${g} no flag`}>
              {m > 0 && <span className="m" style={{ flexGrow: m }}>{m}</span>}
              {y > 0 && <span className="y" style={{ flexGrow: y }}>{y}</span>}
              {g > 0 && <span className="g" style={{ flexGrow: g }}>{g}</span>}
            </div>
            <span className={flaggedPct ? "pc" : "pc zero"}>{flaggedPct}%</span>
          </div>
        );
      })}
    </>
  );
}

export default function Dashboard() {
  const [rep, setRep] = useState<S["DashboardReport"] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<S["DashboardReport"]>("dashboard").then(setRep).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!rep) return <p className="muted">Loading...</p>;
  const flagged = rep.model_signals.filter((s) => s.suggested);
  const maxWeek = Math.max(1, ...(rep.filed_by_week ?? []).map((w) => w.filed));  // bar scale only, not a figure

  return (
    <>
      <PageHead title="Information Integrity Dashboard">How much of what was filed rests on current authoritative records, and what needs a person.</PageHead>
      <div className="kpis">{rep.kpis.map((k) => <Tile key={k.id} k={k} flagged={flagged} />)}</div>
      {flagged.map((s) => {
        const [lead, ...rest] = s.plain.split(": ");
        return (
          <div key={s.model_id} className="banner bad recall-banner" role="status">
            <span className="txt">{rest.length ? <><b>{lead}:</b> {rest.join(": ")}</> : <b>{s.plain}</b>}</span>
            <Link href="/recall" className="btn-mag">Review in Recall →</Link>
          </div>
        );
      })}

      <Reliability />

      <div className="cards">
        <div className="panel">
          <h3>Risk by business function</h3>
          <ByFunction rows={rep.by_function} />
        </div>
        <div className="panel">
          <div className="head"><h3>Last 10 filed</h3><Link href="/records">All records →</Link></div>
          {rep.recent.length ? (
            <table>
              <thead><tr><th>Record</th><th>Title</th><th>Tier</th><th>Status</th></tr></thead>
              <tbody>{rep.recent.map((r) => (
                <tr key={r.record_id}>
                  <td><Link className="rid" href={`/records?id=${encodeURIComponent(r.record_id)}`}>{r.record_id}</Link></td>
                  <td>{r.title}</td><td><span className="tier">{r.tier}</span></td>
                  <td className={/needs a person/i.test(r.status) ? "flag-text" : undefined}>{r.status}</td>
                </tr>
              ))}</tbody>
            </table>
          ) : <p className="muted">None filed yet</p>}
        </div>
      </div>

      {(rep.bias || rep.queue || rep.filed_by_week?.length) ? (
        <div className="cards">
          {rep.bias && (
            <div className="panel">
              <h3>Bias check</h3>
              <p className="muted">{rep.bias.label ?? "How broad and how current the evidence is behind each filed output."}</p>
              <div className="counts">
                <div><b>{rep.bias.ok}</b><Pill text="✓ Broad evidence" colours={OK} /></div>
                <div><b>{rep.bias.attention}</b><Pill text="! Narrow evidence" colours={ATTN} /></div>
                <div><b>{rep.bias.not_run}</b><Pill text="– Not run" colours={GREY} /></div>
              </div>
            </div>
          )}
          {rep.queue && (
            <div className="panel">
              <h3>Review queue</h3>
              <div className="counts">
                <div><b>{rep.queue.open}</b>Open</div><div><b>{rep.queue.closed}</b>Closed</div>
                <div><b>{rep.queue.drafts_open}</b>Drafts waiting for review</div>
              </div>
              <p className="muted"><Link href="/recall">Open Recall</Link> to queue or review.</p>
            </div>
          )}
          {rep.filed_by_week?.length ? (
            <div className="panel">
              <h3>Filed per week</h3>
              {rep.filed_by_week.map((w) => (
                <div key={w.week_start} className="bar-row">
                  <span className="muted">{w.week_start}</span>
                  <span className="wbar" style={{ width: `${(w.filed / maxWeek) * 100}%` }} aria-hidden="true" />
                  <span>{w.filed} filed, {w.approved} approved</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {(rep.gate_by_type?.length || rep.by_model?.length) ? (
        <div className="cards">
          {rep.gate_by_type?.length ? (
            <div className="panel">
              <h3>Filing gate by document type</h3>
              <table>
                <thead><tr><th>Document type</th><th>Ready</th><th>Needs review</th><th>Blocked</th><th>Not recorded</th></tr></thead>
                <tbody>{rep.gate_by_type.map((g) => (
                  <tr key={g.document_type}><td>{g.name}</td><td>{g.ready}</td><td>{g.attention}</td><td>{g.blocked}</td><td>{g.not_recorded}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : null}
          {rep.by_model?.length ? (
            <div className="panel">
              <h3>By model</h3>
              <table>
                <thead><tr><th>Model</th><th>Provider</th><th>Status</th><th>Filed</th><th>In recall queue</th></tr></thead>
                <tbody>{rep.by_model.map((m) => (
                  <tr key={m.model_id}><td className="mono">{m.model_id}</td><td>{m.provider}</td><td>{m.status}</td><td>{m.filed}</td><td>{m.in_recall_queue}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="cards">
        <div className="panel">
          <h3>Latest statements supported by authoritative records</h3>
          {rep.recent_supported.length
            ? rep.recent_supported.slice(0, 5).map((x) => (
              <p key={`${x.record_id}-${x.claim_id}`} className="muted">
                {x.record_id}: {x.text} (from {x.source_record_ids.join(", ") || "no record listed"})
              </p>))
            : <p className="muted">None issued with stored checks yet</p>}
        </div>
        <div className="panel">
          <h3>AI-written vs human-written statements</h3>
          <p className="muted">{rep.authorship.ai || rep.authorship.human ? rep.authorship.plain : "None issued with stored checks yet"}</p>
        </div>
        <div className="panel">
          <h3>Sources and disposal</h3>
          <p className="muted">{rep.rot.plain}</p>
          <p className="muted">{rep.disposal_due.plain}</p>
        </div>
      </div>
      <p className="muted" style={{ marginTop: 16 }}>Example data. Every figure comes from passports and records; narrow-evidence signals are rules to look at, not findings.</p>
    </>
  );
}
