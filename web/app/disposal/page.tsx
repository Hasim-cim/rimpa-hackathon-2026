"use client";

import { useCallback, useEffect, useState } from "react";
import { api, OK, DISPOSAL_COLOURS, Pill, short, BAD, type S } from "@/lib/ui";
import PageHead from "../page-head";

const today = () => new Date().toLocaleDateString("en-CA");
const day = (s: string) => s.slice(0, 10);
const stamp = (s: string) => s.replace("T", " ").slice(0, 19);

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
  const [confirming, setConfirming] = useState(false);

  const refresh = useCallback(async (date: string) => {
    const [pol, due, reg, aud] = await Promise.all([
      api<S["Policy"]>("policy"),
      api<S["DisposalItem"][]>(`disposal/due?as_of=${date}`),
      api<S["DisposalEntry"][]>("disposal/register"),
      api<Record<string, unknown>[]>("audit?action_prefix=disposal.&limit=10"),
    ]);
    setAuthority(pol.tier_rules.disposal_authority); setItems(due); setRegister(reg); setAudit(aud);
    setChosen(new Set());   // nothing is pre-ticked: the information manager chooses what to destroy
  }, []);

  useEffect(() => { refresh(asOf).catch((e) => setError(e.message)); }, [asOf, refresh]);

  const approvable = items.filter((i) => !i.on_hold).map((i) => i.record_id);
  const picked = approvable.filter((id) => chosen.has(id));
  const holds = items.length - approvable.length;

  async function approve() {
    setBusy(true); setError(""); setConfirming(false);
    try {
      const done = await api<S["DisposalEntry"][]>("disposal/approve", {
        json: { record_ids: picked, approved_by: approver, reason, as_of: asOf } });
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

  const toggle = (id: string) => { setConfirming(false); setChosen((c) => { const n = new Set(c); if (n.has(id)) n.delete(id); else n.add(id); return n; }); };

  return (
    <div className="stack">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16, justifyContent: "space-between", alignItems: "flex-end" }}>
        <PageHead title="Disposal">Records and log entries due for destruction under the retention rules, with approval kept on the record.</PageHead>
        <div style={{ marginBottom: 18 }}>
          <label htmlFor="asof" style={{ margin: "0 0 4px", fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase" }}>As of</label>
          <input id="asof" type="date" style={{ width: "auto" }} value={asOf} onChange={(e) => e.target.value && setAsOf(e.target.value)} />
        </div>
      </div>
      <div className="info-strip">
        <span><span className="chip-t0">T0</span>Log entries kept <b>90 days</b>, then destroyed with approval.</span>
        <span><span className="chip-t13">T1–T3</span>Follow their business record.</span>
        <span className="auth">Disposal authority: {authority}</span>
      </div>
      <div className="dtiles">
        <div className="dtile bad"><span className="l">Due for destruction</span><span className="v">{approvable.length}</span><span className="p">Past retention, awaiting approval</span></div>
        <div className="dtile attn"><span className="l">On hold</span><span className="v">{holds}</span><span className="p">Model under recall: cannot be destroyed yet</span></div>
        <div className="dtile ok"><span className="l">Selected to destroy</span><span className="v">{picked.length}</span><span className="p">Of {approvable.length} due, ticked below</span></div>
      </div>

      <section className="panel panel-pad" aria-label="Due for disposal">
        <div className="panel-head" style={{ padding: "0 0 8px", border: 0 }}>
          <h2>Due for disposal</h2>
          <span>
            <button type="button" className="linkbtn" onClick={() => { setConfirming(false); setChosen(new Set(approvable)); }} disabled={!approvable.length}>Select all due</button>
            {" · "}
            <button type="button" className="linkbtn" onClick={() => { setConfirming(false); setChosen(new Set()); }}>Clear selection</button>
          </span>
        </div>
        {items.length ? (
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr><th><span className="sr" style={{ position: "absolute", left: -9999 }}>Select</span></th><th>Record</th><th>App</th><th>Model</th><th>Created</th><th>Due</th><th>Status</th><th>Reason</th></tr></thead>
              <tbody>
                {items.map((i) => (
                  <tr key={i.record_id}>
                    <td>
                      <input type="checkbox" style={{ width: 16, height: 16, accentColor: "var(--teal)" }} aria-label={`Select ${i.record_id}`}
                        checked={chosen.has(i.record_id)} disabled={i.on_hold} onChange={() => toggle(i.record_id)} />
                    </td>
                    <td className="mono"><a href={`/records?id=${encodeURIComponent(i.record_id)}`}>{i.record_id}</a></td><td>{i.app_id}</td><td className="mono">{i.model_returned}</td>
                    <td className="mono">{day(i.created)}</td><td className="due-date mono">{i.due}</td>
                    <td title={i.hold_reason}><Pill text={i.on_hold ? "on hold" : "due"} colours={DISPOSAL_COLOURS[i.on_hold ? "on hold" : "due"]} /></td>
                    <td>{i.hold_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="muted">Nothing is past its retention period on this date.</p>}
      </section>

      <section className="approve" aria-label="Approve destruction">
        <h2>Approve destruction</h2>
        <p>The approval, approver and reason are written to each record&apos;s passport before it is destroyed.</p>
        <div className="two">
          <div><label htmlFor="appr">Approver name</label><input id="appr" value={approver} onChange={(e) => setApprover(e.target.value)} /></div>
          <div><label htmlFor="why">Reason</label><input id="why" value={reason} onChange={(e) => setReason(e.target.value)} /></div>
        </div>
        <div className="foot">
          <span>{picked.length} of {approvable.length} records selected for destruction.</span>
          {confirming ? (
            <div className="confirm" role="alertdialog" aria-label="Confirm destruction">
              <span>Destroy {picked.length} record{picked.length === 1 ? "" : "s"}? Only the hash stubs are kept. This cannot be undone.</span>
              <button type="button" className="btn-mag" onClick={approve} disabled={busy}>{busy ? "Destroying..." : "Yes, destroy"}</button>
              <button type="button" className="btn-ghost" onClick={() => setConfirming(false)}>Cancel</button>
            </div>
          ) : (
            <button type="button" className="btn-mag" onClick={() => setConfirming(true)} disabled={busy || !picked.length}>
              Approve destruction{picked.length ? ` of ${picked.length}` : ""}
            </button>
          )}
        </div>
      </section>
      {error && <p className="error" role="alert">{error}</p>}
      {result && (
        <div role="status">
          <p style={result.ok ? { background: OK[0], color: OK[1], padding: "8px 12px", borderRadius: 6 } : { background: BAD[0], color: BAD[1], padding: "8px 12px", borderRadius: 6 }}>{result.text}</p>
          <p className="muted">{result.detail}</p>
        </div>
      )}

      <section className="panel panel-pad" aria-label="Disposal register">
        <h2 style={{ marginTop: 0 }}>Disposal register</h2>
        {register.length ? (
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr><th>Record id</th><th>Tier</th><th>Created</th><th>Destroyed</th><th>Approved by</th><th>Authority</th><th>Reason</th><th>Hash retained</th></tr></thead>
              <tbody>
                {register.map((e) => (
                  <tr key={e.record_id}>
                    <td className="mono">{e.record_id}</td><td><span className="tier">{e.tier}</span></td><td>{stamp(e.created)}</td><td>{stamp(e.disposed_at)}</td>
                    <td>{e.approved_by}</td><td>{e.authority}</td><td>{e.reason}</td><td className="mono">{short(e.hash_retained)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
      </section>
    </div>
  );
}
