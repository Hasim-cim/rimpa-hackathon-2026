"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { tourSet } from "@/lib/tour";
import { api, OK, Pill, TIER_COLOURS, type S } from "@/lib/ui";
import Reliability from "../reliability";
import PageHead from "../page-head";

const BY = "Information manager";
const input = { width: "100%", padding: 8, font: "inherit", border: "1px solid #9ca3af", borderRadius: 6 } as const;
const ok = { background: OK[0], color: OK[1], padding: "8px 12px", borderRadius: 6, marginTop: 12 } as const;
type Counts = Record<string, number>;

function Tiles({ counts }: { counts: Counts }) {
  const n = (t: string) => counts[t] ?? 0;
  const tiles: [string, number][] = [["Records affected", n("T1") + n("T2") + n("T3")], ["T2 decision-informing", n("T2")], ["T1", n("T1")], ["T3", n("T3")]];
  return <div className="counts">{tiles.map(([k, v]) => <div key={k}><b>{v}</b>{k}</div>)}</div>;
}

function Items({ items, what }: { items: S["RecallItem"][]; what: string }) {
  if (!items.length) return <p className="muted">No T1 to T3 records {what}.</p>;
  return (
    <table>
      <thead><tr><th>Record id</th><th>Tier</th><th>Function</th><th>Created</th><th>Reviewer</th><th>Queued</th></tr></thead>
      <tbody>
        {items.map((i) => (
          <tr key={i.record_id}>
            <td><Link href={`/records?id=${encodeURIComponent(i.record_id)}`}>{i.record_id}</Link></td><td><Pill text={i.tier} colours={TIER_COLOURS[i.tier]} /></td><td>{i.function}</td>
            <td>{i.created.slice(0, 10)}</td><td>{i.reviewer || "none"}</td><td>{i.queued ? "yes" : "no"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Recall() {
  const [reg, setReg] = useState<S["ModelRegistryEntry"][]>([]);
  const [records, setRecords] = useState<S["SourceRecord"][]>([]);
  const [audit, setAudit] = useState<Record<string, string>[]>([]);
  const [model, setModel] = useState("");
  const [status, setStatus] = useState<"faulty" | "withdrawn">("faulty");
  const [eff, setEff] = useState("2026-03-01");
  const [reason, setReason] = useState("Vendor bulletin: fabricated citations");
  const [res, setRes] = useState<S["RecallResult"] | null>(null);
  const [queuedMsg, setQueuedMsg] = useState("");
  const [error, setError] = useState("");
  // by source record
  const [recId, setRecId] = useState("");
  const [supBy, setSupBy] = useState("");
  const [supReason, setSupReason] = useState("Policy replaced by v5");
  const [srcRes, setSrcRes] = useState<S["SourceRecallResult"] | null>(null);
  const [srcError, setSrcError] = useState("");
  const [srcQueued, setSrcQueued] = useState("");
  const [relKey, setRelKey] = useState(0);

  const refreshAudit = useCallback(() => api<Record<string, string>[]>("audit?limit=20").then(setAudit).catch(() => {}), []);
  const loadModels = () => api<S["ModelRegistryEntry"][]>("models").then(setReg);

  useEffect(() => {
    Promise.all([api<S["ModelRegistryEntry"][]>("models"), api<S["SourceRecord"][]>("records")]).then(([m, r]) => {
      const ids = m.map((e) => e.model_id), rids = r.map((x) => x.id);
      setReg(m); setRecords(r);
      setModel(ids.includes("northstar-7-2026-03-01") ? "northstar-7-2026-03-01" : ids[0] ?? "");
      setRecId(rids.includes("REC-2026/004790") ? "REC-2026/004790" : rids[0] ?? "");
      setSupBy(rids.includes("REC-2026/004912") ? "REC-2026/004912" : "");
    }).catch((e) => setError(e.message));
    refreshAudit();
  }, [refreshAudit]);

  const callModel = useCallback(async (mark?: S["Mark"]) => {
    if (!model) return;
    setError("");
    try {
      setRes(await api<S["RecallResult"]>("recall", { json: { model_id: model, mark } }));
      if (mark) await loadModels();
    } catch (e) { setError((e as Error).message); }
    refreshAudit();
  }, [model, refreshAudit]);

  useEffect(() => { setQueuedMsg(""); callModel(); }, [callModel]);

  const callSource = useCallback(async (mark?: S["SupersedeMark"]) => {
    if (!recId) return;
    setSrcError("");
    try { setSrcRes(await api<S["SourceRecallResult"]>("recall/record", { json: { record_id: recId, mark } })); if (mark) { setRelKey((k) => k + 1); tourSet("marked"); } }
    catch (e) { setSrcRes(null); setSrcError((e as Error).message); }
    refreshAudit();
  }, [recId, refreshAudit]);

  useEffect(() => { setSrcQueued(""); callSource(); }, [callSource]);

  const srcT2 = srcRes?.items.filter((i) => i.tier === "T2").map((i) => i.record_id) ?? [];
  async function queueSource() {
    if (!srcRes) return;
    try {
      const { queued } = await api<{ queued: number }>("recall/queue", {
        json: { record_ids: srcT2, by: BY, reason: `Source ${srcRes.record_id} ${srcRes.record.status}: ${supReason || "no reason given"}` } });
      await callSource();
      tourSet("queued");
      setSrcQueued(`Queued ${queued} T2 records for re-review (${srcT2.length - queued} were already queued).`);
    } catch (err) { setSrcError((err as Error).message); }
  }

  const t2 = res?.items.filter((i) => i.tier === "T2").map((i) => i.record_id) ?? [];
  async function queue() {
    if (!res) return;
    const e = res.entry;
    try {
      const { queued } = await api<{ queued: number }>("recall/queue", {
        json: { record_ids: t2, by: BY, reason: `Model ${model} marked ${e.status}: ${e.reason || "no reason given"}` } });
      await callModel();
      setQueuedMsg(`Queued ${queued} T2 records for re-review (${t2.length - queued} were already queued).`);
    } catch (err) { setError((err as Error).message); }
  }

  return (
    <>
      <PageHead title="Recall">When a source or a model changes, find and queue everything that relied on it.</PageHead>
      <Reliability refresh={relKey} />
      <h2 style={{ marginTop: 0 }}>Mark a source superseded</h2>
      <p className="muted">A new version replaces a record (a reissued notice, a new policy). It stops counting as evidence at once, and recall lists every AI output that relied on it.</p>
      <form onSubmit={(e) => { e.preventDefault(); callSource({ superseded_by: supBy || null, reason: supReason, by: BY }); }}>
        <label htmlFor="rec">Source record</label>
        <select id="rec" value={recId} onChange={(e) => setRecId(e.target.value)}>
          {records.map((r) => <option key={r.id} value={r.id}>{r.id}  {r.title}</option>)}
        </select>
        <label htmlFor="sup">Superseded by (blank = withdrawn without a replacement)</label>
        <select id="sup" value={supBy} onChange={(e) => setSupBy(e.target.value)}>
          <option value="">(none)</option>
          {records.filter((r) => r.id !== recId).map((r) => <option key={r.id} value={r.id}>{r.id}  {r.title}</option>)}
        </select>
        <label htmlFor="sreason">Reason</label>
        <input id="sreason" value={supReason} onChange={(e) => setSupReason(e.target.value)} style={input} />
        <button className="run" type="submit" data-tour="mark">Mark superseded</button>
      </form>
      {srcError && <p className="error" role="alert">{srcError}</p>}
      {srcRes && (
        <>
          <h3>Recall by source record: {srcRes.record_id}</h3>
          <p className="muted">{srcRes.record.title}. Status {srcRes.record.status}.</p>
          <div data-tour="source-results">
            <Tiles counts={srcRes.counts} />
            <Items items={srcRes.items} what="relied on this record" />
          </div>
          <button className="run" onClick={queueSource} disabled={!srcT2.length} data-tour="queue">Queue T2 records for re-review ({srcT2.length})</button>
          {srcQueued && <p role="status" style={ok} data-tour="queued">{srcQueued}</p>}
        </>
      )}

      <h2>Mark a model</h2>
      <form onSubmit={(e) => { e.preventDefault(); callModel({ status, effective_from: eff, reason, by: BY }); }}>
        <label htmlFor="model">Model</label>
        <select id="model" value={model} onChange={(e) => setModel(e.target.value)}>{reg.map((m) => <option key={m.model_id}>{m.model_id}</option>)}</select>
        <label htmlFor="status">Status</label>
        <select id="status" value={status} onChange={(e) => setStatus(e.target.value as typeof status)}><option>faulty</option><option>withdrawn</option></select>
        <label htmlFor="eff">Effective from</label>
        <input id="eff" type="date" value={eff} onChange={(e) => setEff(e.target.value)} style={input} />
        <label htmlFor="reason">Reason</label>
        <input id="reason" value={reason} onChange={(e) => setReason(e.target.value)} style={input} />
        <button className="run" type="submit">Mark model</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}

      {res && (
        <>
          <h2>Recall: {model}</h2>
          <p className="muted">
            Status {res.entry.status}{res.entry.effective_from ? `, effective from ${res.entry.effective_from}` : ""}{res.entry.reason ? `. ${res.entry.reason}` : ""}
          </p>
          <Tiles counts={res.counts} />
          <Items items={res.items} what="were made with this model" />
          <button className="run" onClick={queue} disabled={!t2.length}>Queue T2 records for re-review ({t2.length})</button>
          {queuedMsg && <p role="status" style={ok}>{queuedMsg}</p>}
        </>
      )}

      <details className="card-d">
        <summary>Model registry</summary>
      <table>
        <thead><tr><th>Model</th><th>Provider</th><th>Status</th><th>Effective from</th><th>Reason</th></tr></thead>
        <tbody>{reg.map((e) => <tr key={e.model_id}><td>{e.model_id}</td><td>{e.provider}</td><td>{e.status}</td><td>{e.effective_from ?? ""}</td><td>{e.reason}</td></tr>)}</tbody>
      </table>
      </details>

      <details className="card-d" style={{ marginTop: 24 }}>
        <summary>Audit trail (last 20)</summary>
        <table>
          <thead><tr><th>At</th><th>Actor</th><th>Action</th><th>Subject</th><th>Detail</th></tr></thead>
          <tbody>{audit.map((a, i) => <tr key={i}><td>{a.at}</td><td>{a.actor}</td><td>{a.action}</td><td>{a.subject}</td><td>{a.detail}</td></tr>)}</tbody>
        </table>
      </details>

    </>
  );
}
