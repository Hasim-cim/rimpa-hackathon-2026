"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Reliability from "../reliability";
import { api, ATTN, GREY, OK, BAD, Pill, TIER_COLOURS, type Colours, type S } from "@/lib/ui";
import PageHead from "../page-head";

// Every figure and sentence comes from GET /api/dashboard; nothing is computed here.
const KPI_COLOURS: Record<string, Colours> = { filed_approved: OK, needs_review: ATTN, narrow_evidence: ATTN };

function Tile({ k }: { k: S["KpiTile"] }) {
  const [bg, fg] = k.id === "recall_suggested" ? (k.count ? BAD : GREY) : KPI_COLOURS[k.id] ?? GREY;
  return (
    <div className="kpi" style={{ background: bg, color: fg }}>
      <div className="l" style={k.id === "recall_suggested" && k.count ? { fontWeight: 700 } : undefined}>{k.label}</div>
      <div className="v">{k.display}</div>
      <div className="p">{k.plain}</div>
    </div>
  );
}

// B2 additions (optional until the engine ships them; each panel renders only when its field is present).
type Week = { week_start: string; filed: number; approved: number };
type GateRow = { document_type: string; name: string; ready: number; attention: number; blocked: number; not_recorded: number };
type ModelRow = { model_id: string; provider: string; status: string; filed: number; in_recall_queue: number };
type B2 = { filed_by_week?: Week[]; gate_by_type?: GateRow[]; by_model?: ModelRow[];
  bias?: { ok: number; attention: number; not_run: number; label?: string }; queue?: { open: number; closed: number } };

export default function Dashboard() {
  const [rep, setRep] = useState<S["DashboardReport"] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<S["DashboardReport"]>("dashboard").then(setRep).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!rep) return <p className="muted">Loading...</p>;
  const flagged = rep.model_signals.filter((s) => s.suggested);
  const b2 = rep as S["DashboardReport"] & B2;
  const maxWeek = Math.max(1, ...(b2.filed_by_week ?? []).map((w) => w.filed));  // bar scale only, not a figure

  return (
    <>
      <PageHead title="Dashboard">How much of what was filed rests on current authoritative records, and what needs a person.</PageHead>
      <Reliability />
      <div className="kpis">{rep.kpis.map((k) => <Tile key={k.id} k={k} />)}</div>
      {flagged.map((s) => (
        <div key={s.model_id} className="kpi" style={{ background: BAD[0], color: BAD[1], minHeight: 0, marginTop: 10 }}>
          <b>{s.plain}</b>
        </div>
      ))}
      {flagged.length > 0 && <p className="muted">Use <Link href="/recall">Recall</Link> to act on this signal.</p>}


      {(b2.bias || b2.queue || b2.filed_by_week?.length) ? (
        <div className="cards">
          {b2.bias && (
            <div className="panel">
              <h3>Bias check</h3>
              <p className="muted">{b2.bias.label ?? "How broad and how current the evidence is behind each filed output."}</p>
              <div className="counts">
                <div><b>{b2.bias.ok}</b><Pill text="✓ Broad evidence" colours={OK} /></div>
                <div><b>{b2.bias.attention}</b><Pill text="! Narrow evidence" colours={ATTN} /></div>
                <div><b>{b2.bias.not_run}</b><Pill text="– Not run" colours={GREY} /></div>
              </div>
            </div>
          )}
          {b2.queue && (
            <div className="panel">
              <h3>Review queue</h3>
              <div className="counts"><div><b>{b2.queue.open}</b>Open</div><div><b>{b2.queue.closed}</b>Closed</div></div>
              <p className="muted"><Link href="/recall">Open Recall</Link> to queue or review.</p>
            </div>
          )}
          {b2.filed_by_week?.length ? (
            <div className="panel">
              <h3>Filed per week</h3>
              {b2.filed_by_week.map((w) => (
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

      {(b2.gate_by_type?.length || b2.by_model?.length) ? (
        <div className="cards">
          {b2.gate_by_type?.length ? (
            <div className="panel">
              <h3>Filing gate by document type</h3>
              <table>
                <thead><tr><th>Document type</th><th>Ready</th><th>Needs review</th><th>Blocked</th><th>Not recorded</th></tr></thead>
                <tbody>{b2.gate_by_type.map((g) => (
                  <tr key={g.document_type}><td>{g.name}</td><td>{g.ready}</td><td>{g.attention}</td><td>{g.blocked}</td><td>{g.not_recorded}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : null}
          {b2.by_model?.length ? (
            <div className="panel">
              <h3>By model</h3>
              <table>
                <thead><tr><th>Model</th><th>Provider</th><th>Status</th><th>Filed</th><th>In recall queue</th></tr></thead>
                <tbody>{b2.by_model.map((m) => (
                  <tr key={m.model_id}><td>{m.model_id}</td><td>{m.provider}</td><td>{m.status}</td><td>{m.filed}</td><td>{m.in_recall_queue}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}
      <div className="cards">
        <div className="panel">
          <h3>Last 10 filed</h3>
          {rep.recent.length ? (
            <table>
              <thead><tr><th>Record</th><th>Title</th><th>Function</th><th>Tier</th><th>Status</th></tr></thead>
              <tbody>{rep.recent.map((r) => (
                <tr key={r.record_id}>
                  <td><Link href={`/records?id=${encodeURIComponent(r.record_id)}`}>{r.record_id}</Link></td>
                  <td>{r.title}</td><td>{r.function}</td><td><Pill text={r.tier} colours={TIER_COLOURS[r.tier]} /></td><td>{r.status}</td>
                </tr>
              ))}</tbody>
            </table>
          ) : <p className="muted">None filed yet</p>}
        </div>
        <div className="panel">
          <h3>Risk by business function</h3>
          {rep.by_function.length ? (
            <table>
              <thead><tr><th>Function</th><th>Total</th><th>Needs a person</th><th>Narrow-evidence signals</th></tr></thead>
              <tbody>{rep.by_function.map((f) => (
                <tr key={f.function}><td>{f.function}</td><td>{f.total}</td><td>{f.needs_review}</td><td>{f.narrow_evidence}</td></tr>
              ))}</tbody>
            </table>
          ) : <p className="muted">None yet</p>}
        </div>
      </div>

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
      <p className="muted">Example data. Every figure comes from passports and records; narrow-evidence signals are rules to look at, not findings.</p>
    </>
  );
}
