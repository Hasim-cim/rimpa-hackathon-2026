"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Reliability from "../reliability";
import { api, ATTN, GREY, OK, BAD, Pill, TIER_COLOURS, type Colours, type S } from "@/lib/ui";

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

export default function Dashboard() {
  const [rep, setRep] = useState<S["DashboardReport"] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<S["DashboardReport"]>("dashboard").then(setRep).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!rep) return <p className="muted">Loading...</p>;
  const flagged = rep.model_signals.filter((s) => s.suggested);

  return (
    <>
      <Reliability />
      <div className="kpis">{rep.kpis.map((k) => <Tile key={k.id} k={k} />)}</div>
      {flagged.map((s) => (
        <div key={s.model_id} className="kpi" style={{ background: BAD[0], color: BAD[1], minHeight: 0, marginTop: 10 }}>
          <b>{s.plain}</b>
        </div>
      ))}
      {flagged.length > 0 && <p className="muted">Use <Link href="/recall">Recall</Link> to act on this signal.</p>}

      <div className="cards">
        <div className="panel">
          <h3>Last 10 filed</h3>
          {rep.recent.length ? (
            <table>
              <thead><tr><th>Record</th><th>Title</th><th>Function</th><th>Tier</th><th>Status</th></tr></thead>
              <tbody>{rep.recent.map((r) => (
                <tr key={r.record_id}>
                  <td><Link href={`/?id=${encodeURIComponent(r.record_id)}`}>{r.record_id}</Link></td>
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
