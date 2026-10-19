"use client";

import { useCallback, useEffect, useState } from "react";
import { api, DISPOSAL_COLOURS, Pill, short, type S } from "@/lib/ui";

const today = () => new Date().toLocaleDateString("en-CA");
const day = (s: string) => s.slice(0, 10);
const stamp = (s: string) => s.replace("T", " ").slice(0, 19);
const input = { width: "100%", padding: 8, font: "inherit", border: "1px solid #9ca3af", borderRadius: 6 } as const;

export default function Disposal() {
  const [asOf, setAsOf] = useState(today());
  const [authority, setAuthority] = useState("");
  const [items, setItems] = useState<S["DisposalItem"][]>([]);
  const [register, setRegister] = useState<S["DisposalEntry"][]>([]);
  const [audit, setAudit] = useState<Record<string, unknown>[]>([]);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [approver, setApprover] = useState("Information manager");
  const [reason, setReason] = useState("Transitory AI interaction past retention; no business value");
  const [result, setResult] = useState<{ ok: boolean; text: string; detail: string } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async (date: string) => {
    const [pol, due, reg, aud] = await Promise.all([
      api<S["Policy"]>("policy"),
      api<S["DisposalItem"][]>(`disposal/due?as_of=${date}`),
      api<S["DisposalEntry"][]>("disposal/register"),
      api<Record<string, unknown>[]>("audit?action_prefix=disposal.&limit=10"),
    ]);
    setAuthority(pol.tier_rules.disposal_authority); setItems(due); setRegister(reg); setAudit(aud);
    setChosen(new Set(due.filter((i) => !i.on_hold).map((i) => i.record_id)));
  }, []);

  useEffect(() => { refresh(asOf).catch((e) => setError(e.message)); }, [asOf, refresh]);

  const approvable = items.filter((i) => !i.on_hold).map((i) => i.record_id);

  async function approve() {
    setBusy(true); setError("");
    try {
      const done = await api<S["DisposalEntry"][]>("disposal/approve", {
        json: { record_ids: approvable.filter((id) => chosen.has(id)), approved_by: approver, reason, as_of: asOf } });
      const rep = await api<S["ChainReport"]>("chain/verify", { method: "GET" });
      setResult({
        ok: rep.ok, detail: rep.detail,
        text: rep.ok ? `Destroyed ${done.length} records. Hash stubs retained; chain verified.`
          : `Destroyed ${done.length} records, but the chain check failed at ${rep.first_break}.`,
      });
      await refresh(asOf);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const toggle = (id: string) => setChosen((c) => { const n = new Set(c); if (n.has(id)) n.delete(id); else n.add(id); return n; });

  return (
    <>
      <p>T0 log entries are kept 90 days, then destroyed with approval. T1 to T3 follow their business record.</p>
      <p className="muted">Disposal authority: {authority}</p>
      <label htmlFor="asof">As of</label>
      <input id="asof" type="date" style={{ ...input, width: "auto" }} value={asOf} onChange={(e) => e.target.value && setAsOf(e.target.value)} />
      <div className="counts" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
        <div><b>{approvable.length}</b>Due for destruction</div>
        <div><b>{items.length - approvable.length}</b>On hold</div>
      </div>

      <h2>Due for disposal</h2>
      {items.length ? (
        <table>
          <thead><tr><th>Record id</th><th>App</th><th>Model</th><th>Created</th><th>Due</th><th>Status</th><th>Reason</th></tr></thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.record_id}>
                <td>{i.record_id}</td><td>{i.app_id}</td><td>{i.model_returned}</td><td>{day(i.created)}</td><td>{i.due}</td>
                <td title={i.hold_reason}><Pill text={i.on_hold ? "on hold" : "due"} colours={DISPOSAL_COLOURS[i.on_hold ? "on hold" : "due"]} /></td>
                <td>{i.hold_reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p className="muted">Nothing is past its retention period on this date.</p>}

      <h2>Approve destruction</h2>
      <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
        <legend style={{ fontWeight: 600 }}>Records to destroy</legend>
        {approvable.length ? approvable.map((id) => (
          <label key={id} style={{ fontWeight: 400, margin: "4px 0", display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" checked={chosen.has(id)} onChange={() => toggle(id)} /> {id}
          </label>
        )) : <p className="muted">No records can be approved on this date.</p>}
      </fieldset>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "0 16px" }}>
        <div><label htmlFor="appr">Approver name</label><input id="appr" style={input} value={approver} onChange={(e) => setApprover(e.target.value)} /></div>
        <div><label htmlFor="why">Reason</label><input id="why" style={input} value={reason} onChange={(e) => setReason(e.target.value)} /></div>
      </div>
      <button className="run" onClick={approve} disabled={busy || !approvable.some((id) => chosen.has(id))}>Approve destruction</button>
      {error && <p className="error" role="alert">{error}</p>}
      {result && (
        <div role="status">
          <p style={result.ok ? { background: "#d1f0dc", color: "#14532d", padding: "8px 12px", borderRadius: 6 } : { background: "#f8d0d0", color: "#7f1d1d", padding: "8px 12px", borderRadius: 6 }}>{result.text}</p>
          <p className="muted">{result.detail}</p>
        </div>
      )}

      <h2>Disposal register</h2>
      {register.length ? (
        <table>
          <thead><tr><th>Record id</th><th>Tier</th><th>Created</th><th>Destroyed</th><th>Approved by</th><th>Authority</th><th>Reason</th><th>Hash retained</th></tr></thead>
          <tbody>
            {register.map((e) => (
              <tr key={e.record_id}>
                <td>{e.record_id}</td><td>{e.tier}</td><td>{stamp(e.created)}</td><td>{stamp(e.disposed_at)}</td>
                <td>{e.approved_by}</td><td>{e.authority}</td><td>{e.reason}</td><td>{short(e.hash_retained)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p className="muted">No records destroyed yet.</p>}

      <details style={{ marginTop: 16 }}>
        <summary>Audit trail (last 10 disposal rows)</summary>
        <table>
          <thead><tr><th>At</th><th>Actor</th><th>Action</th><th>Subject</th><th>Detail</th></tr></thead>
          <tbody>
            {audit.map((r, i) => (
              <tr key={i}><td>{String(r.at)}</td><td>{String(r.actor)}</td><td>{String(r.action)}</td><td>{String(r.subject)}</td><td>{String(r.detail)}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  );
}
