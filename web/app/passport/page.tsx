"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, GatePill, Pill, short, TIER_COLOURS, type S } from "@/lib/ui";

const KV = ({ k, children }: { k: string; children: React.ReactNode }) => (
  <div style={{ marginBottom: 8, overflowWrap: "anywhere" }}><div className="muted">{k}</div><div>{children}</div></div>
);
const Card = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: "12px 16px" }}><b>{title}</b><div style={{ marginTop: 8 }}>{children}</div></div>
);
const when = (s: string) => s.replace("T", " ");

function PassportView() {
  const initial = useSearchParams().get("id");
  const [ids, setIds] = useState<string[] | null>(null);
  const [sel, setSel] = useState("");
  const [p, setP] = useState<S["Passport"] | null>(null);
  const [chain, setChain] = useState<S["ChainReport"] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<S["Passport"][]>("passports"), api<S["ChainReport"]>("chain/verify")])
      .then(([ps, c]) => {
        const list = ps.map((x) => x.record.id);
        setIds(list); setChain(c);
        setSel(initial && list.includes(initial) ? initial : list[0] ?? "");
      })
      .catch((e) => setError(e.message));
  }, [initial]);

  useEffect(() => {
    if (!sel) { setP(null); return; }
    api<S["Passport"]>(`passport/${sel}`).then(setP).catch((e) => setError(e.message));
  }, [sel]);

  function download() {
    if (!p) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(p, null, 2)], { type: "application/json" }));
    a.download = `${p.record.id.replace(/\//g, "-")}.json`;
    a.click(); URL.revokeObjectURL(a.href);
  }

  if (error) return <p className="error" role="alert">{error}</p>;
  if (ids && !ids.length) return <p className="muted">No passports yet.</p>;
  const [r, a, b, pr, rv, ig, pd] = p ? [p.record, p.agent, p.business, p.process, p.review, p.integrity, p.paradata] : [];

  return (
    <>
      <label htmlFor="rec">Record</label>
      <select id="rec" value={sel} onChange={(e) => setSel(e.target.value)}>
        {ids?.map((i) => <option key={i} value={i}>{i}</option>)}
      </select>
      {chain && (chain.ok
        ? <p className="muted">Chain verified: {chain.detail}</p>
        : <p className="error" role="alert">Chain broken at {chain.first_break}: {chain.detail}</p>)}

      {p && r && a && b && pr && ig && pd && (
        <>
          <h3>{r.title} &nbsp; <Pill text={b.tier} colours={TIER_COLOURS[b.tier]} /></h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12, marginTop: 12 }}>
            <Card title="Record">
              <KV k="Record id">{r.id}</KV><KV k="Title">{r.title}</KV><KV k="Created">{when(r.created)}</KV>
              <KV k="AI generated">{r.ai_generated ? "yes, in part" : "no"}</KV>
              <KV k="Final document">{r.final_document || "none"}</KV><KV k="Content hash">{short(r.content_hash)}</KV>
            </Card>
            <Card title="Agent">
              <KV k="Person">{a.person}</KV><KV k="AI system">{a.ai_system}</KV><KV k="Model requested">{a.model_requested}</KV>
              <KV k="Model returned">{a.model_returned}</KV><KV k="Provider">{a.provider}</KV>
            </Card>
            <Card title="Business">
              <KV k="Function">{b.function}</KV>
              <KV k="Tier"><Pill text={b.tier} colours={TIER_COLOURS[b.tier]} /></KV>
              <KV k="Why this tier">{b.tier_reason}</KV>
              {b.document_type && <KV k="Document type">{b.document_type}</KV>}
              {b.gate && <KV k="Filing gate"><GatePill status={b.gate} /></KV>}
              <KV k="Disposal">{b.disposal}</KV>
              <KV k="Paradata">{pd.use_register_id}; {pd.policy_version}{pd.impact_assessment_ref ? `; impact assessment ${pd.impact_assessment_ref}` : ""}</KV>
            </Card>
            <Card title="Process">
              <KV k="Prompt">{pr.prompt}</KV><KV k="Source records">{pr.source_record_ids.join(", ") || "none"}</KV>
              <KV k="Citation checks">{Object.entries(pr.citation_summary).map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`).join(" ")}</KV>
              <KV k="Evidence">{Object.entries(pr.evidence_summary).map(([k, v]) => `${k} ${v}`).join(" ")}</KV>
              <KV k="Tool calls">{pr.tool_calls.map((t) => t.name + (t.side_effect ? " (side effect)" : "")).join(", ") || "none"}</KV>
            </Card>
            <Card title="Review">
              {rv ? (
                <>
                  <KV k="Reviewer">{rv.reviewer}</KV><KV k="Decision">{rv.decision.replace(/_/g, " ")}</KV>
                  <KV k="Reviewed">{when(rv.reviewed_at)}</KV>{rv.note && <KV k="Note">{rv.note}</KV>}
                </>
              ) : <KV k="Reviewer">none recorded</KV>}
            </Card>
            <Card title="Integrity">
              <KV k="Hash"><code>{short(ig.hash)}</code></KV><KV k="Previous hash"><code>{short(ig.prev_hash)}</code></KV>
              <KV k="Algorithm">{ig.algorithm}</KV><KV k="Version">{ig.version}</KV>
              {ig.corrects && <KV k="Corrects">{ig.corrects}</KV>}
              <details><summary>Full hashes</summary><pre>{`hash:      ${ig.hash}\nprev_hash: ${ig.prev_hash || "-"}`}</pre></details>
            </Card>
          </div>
          <button className="run" onClick={download}>Download passport JSON</button>
        </>
      )}
    </>
  );
}

export default function Page() {
  return <Suspense><PassportView /></Suspense>;
}
