"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, GatePill, Pill, TIER_COLOURS, type S } from "@/lib/ui";
import PageHead from "../page-head";
import { PassportCard } from "../passport-card";

function PassportView() {
  const initial = useSearchParams().get("id");
  const [ids, setIds] = useState<string[] | null>(null);
  const [sel, setSel] = useState("");
  const [missing, setMissing] = useState("");
  const [p, setP] = useState<S["Passport"] | null>(null);
  const [chain, setChain] = useState<S["ChainReport"] | null>(null);
  const [policy, setPolicy] = useState<S["Policy"] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<S["Passport"][]>("passports"), api<S["ChainReport"]>("chain/verify"), api<S["Policy"]>("policy").catch(() => null)])
      .then(([ps, c, pol]) => {
        const list = ps.map((x) => x.record.id);
        setIds(list); setChain(c); setPolicy(pol);
        const ok = !!initial && list.includes(initial);
        setMissing(initial && !ok ? initial : "");
        setSel(ok ? initial! : list[0] ?? "");
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
  const docName = !p?.business.document_type ? "not stated" : policy?.document_types.find((d) => d.id === p.business.document_type)?.name ?? p.business.document_type;

  return (
    <>
      <PageHead title="Passport">The record package kept with an AI output: who, what, why, review and integrity, in one place.</PageHead>
      <section className="panel panel-pad" aria-label="Choose a record">
        <label htmlFor="rec" style={{ marginTop: 0 }}>Record</label>
        <select id="rec" value={sel} onChange={(e) => { setMissing(""); setSel(e.target.value); }}>
          {ids?.map((i) => <option key={i} value={i}>{i}</option>)}
        </select>
      </section>
      {missing && <p className="error" role="alert">Record {missing} not found.</p>}
      {chain && (chain.ok
        ? <div className="banner ok" style={{ marginTop: 16 }}><span className="ic" aria-hidden="true">✓</span><span className="txt"><b>Chain verified.</b> {chain.detail}</span></div>
        : <div role="alert" className="banner" style={{ marginTop: 16, background: "var(--blocked-bg)", borderColor: "var(--blocked-bg)", color: "#fff" }}>
            <span className="txt"><b>✕ Chain broken at {chain.first_break}.</b> {chain.detail}</span></div>)}

      {p && (
        <div className="stack" style={{ marginTop: 16 }}>
          <div className="panel hero">
            <div className="eyebrow"><span>Record passport</span><span className="mono">{p.record.id}</span></div>
            <h1 style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
              {p.record.title}
              <Pill text={p.business.tier} colours={TIER_COLOURS[p.business.tier]} />
              {p.business.gate && <GatePill status={p.business.gate} />}
            </h1>
            <PassportCard p={p} docName={docName} />
            <details className="fold panel" style={{ margin: 0 }}>
              <summary>Full hashes</summary>
              <div className="fold-body"><pre>{`hash:      ${p.integrity.hash}\nprev_hash: ${p.integrity.prev_hash || "-"}`}</pre></div>
            </details>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button className="btn-sm" onClick={download}>Download passport JSON</button>
              <a className="btn-sm" href={`/api/passport/${p.record.id}.pdf`}>Download as PDF</a>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default function Page() {
  return <Suspense><PassportView /></Suspense>;
}
