"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ATTN, CITE_COLOURS, GATE_COLOURS, GREY, OK, Pill, STATUS_COLOURS, STATUS_MARKS, WEIGHT_COLOURS, type S } from "@/lib/ui";
import PageHead from "../page-head";

const SUMMARY_ONLY = "Filed before checks were stored with the passport: summary counts only.";
const TIER_WORDS: Record<string, string> = {
  T0: "T0, a transitory log", T1: "T1, a retained output", T2: "T2, informs a decision", T3: "T3, an agent's action",
};
const CITE_WORDS: Record<string, string> = {
  found: "found", mismatch: "details differ", not_found: "not found (possibly fabricated)", not_checked: "for a person to confirm",
};
// Stored times are naive UTC; read them as UTC so they show in the viewer's local time.
const utc = (s: string) => new Date(/T[^Z+]*$/.test(s) && !/-\d\d:\d\d$/.test(s) ? `${s}Z` : s);
const fmt = (s: string) => {
  const d = utc(s);
  const t = d.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "numeric" });
  return `${t.replace("Sept", "Sep")}, ${d.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
};
const cap = (t: string) => t[0].toUpperCase() + t.slice(1);
const fmtDay = (s: string) => utc(s).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" }).replace("Sept", "Sep");
const fp = (h?: string | null) => (h ? <span className="mono">{h.slice(0, 6)}…{h.slice(-6)}</span> : "none");

type D = Record<string, unknown>;
type Link_ = { record_id: string; rule: string; note: string };
type Item = Record<string, string> & { counted?: boolean; links?: Link_[] };

const KV = ({ k, children }: { k: string; children: React.ReactNode }) => (
  <div className="kv"><span className="k">{k}</span><span className="v">{children}</span></div>
);

function Detail({ check }: { check: S["CheckSummary"] }) {
  const d = (check.details ?? {}) as D;
  const items = (d.items ?? []) as Item[];
  const note = d.note ? <p className="muted">{String(d.note)}</p> : null;
  switch (check.id) {
    case "evidence":
      return <>{note}{d.method ? <p className="muted">Method: {String(d.method)}</p> : null}
        {items.map((v, i) => (
          <div className="sentence" key={i}>
            <div className="top"><Pill text={cap(String(v.weight))} colours={WEIGHT_COLOURS[String(v.weight)]} /><span>{v.text}</span></div>
            <span className="why">{v.reason}</span>
            {v.links?.map((l, j) => (
              <span key={j} className="why">Record {l.record_id} ({l.rule}){l.note ? `: ${l.note}` : ""}</span>
            ))}
          </div>
        ))}</>;
    case "citations":
      return <>{note}{items.map((c, i) => (
        <div className="cite" key={i}>
          <Pill text={String(c.status).replace("_", " ")} colours={CITE_COLOURS[String(c.status)]} />
          <div><b>[{c.n}]</b> {c.reference}<br /><span className="muted">{c.note}</span></div>
        </div>
      ))}</>;
    case "sources": {
      const ids = (d.records ?? []) as string[];
      return <>{note}{ids.length > 0 && <p>{ids.join(", ")}</p>}
        {items.length > 0 && (
          <table>
            <thead><tr><th>Record</th><th>Title</th><th>System</th><th>Status</th><th>Counted at issue</th></tr></thead>
            <tbody>{items.map((s, i) => (
              <tr key={i}><td>{s.record_id}</td><td>{s.title}</td><td>{s.system}</td><td>{s.status}</td>
                <td>{s.counted ? "Yes" : `No: ${s.why_not}`}</td></tr>
            ))}</tbody>
          </table>
        )}</>;
    }
    case "bias": {
      // How broad and how current the evidence is. Never claims the output is unbiased (docs/decisions.md, 19 Oct).
      const src = (d.sources ?? []) as Item[];
      const systems = (d.systems ?? []) as string[];
      const stmts = (d.statements ?? []) as { claim_id: string; text: string; sources: string[]; narrow: boolean }[];
      return <>{d.method ? <p className="muted">What this checks: {String(d.method).replace(/\.+$/, "")}.</p> : null}{note}
        {d.suggestion ? <p><b>Suggestion.</b> {String(d.suggestion)}</p> : null}
        {systems.length > 0 && <KV k="Systems relied on">{systems.join(", ")}</KV>}
        {stmts.map((st) => (
          <div className="sentence" key={st.claim_id}>
            <div className="top"><Pill text={st.narrow ? "! Narrow" : "✓ Broad"} colours={st.narrow ? ATTN : OK} /><span>{st.text}</span></div>
            <span className="why">Rests on {st.sources.length ? st.sources.join(", ") : "no record"}</span>
          </div>
        ))}
        {src.length > 0 && (
          <table>
            <thead><tr><th>Record</th><th>Title</th><th>System</th><th>Status</th><th>Counts</th></tr></thead>
            <tbody>{src.map((s, i) => (
              <tr key={i}><td>{s.record_id}</td><td>{s.title}</td><td>{s.system}</td><td>{s.status}</td>
                <td>{s.counts ? "Yes" : `No${s.why ? `: ${s.why}` : ""}`}</td></tr>
            ))}</tbody>
          </table>
        )}</>;
    }
    case "gate":
      return <>{((d.reasons ?? []) as string[]).map((r, i) => <p key={i}>{r}</p>)}{note}
        <KV k="Policy version">{String(d.policy_version ?? "-")}</KV>
        <KV k="Policy hash">{d.policy_hash ? `${String(d.policy_hash).slice(0, 12)}…` : "-"}</KV>
        <KV k="Document type">{String(d.document_type ?? "-")}</KV></>;
    case "integrity":
      return <><KV k="Algorithm">{String(d.algorithm)}</KV><KV k="Hash">{String(d.hash)}</KV>
        <KV k="Previous hash">{String(d.prev_hash ?? "-")}</KV><KV k="Checks hash">{String(d.checks_hash ?? "-")}</KV>
        <KV k="Chain">{String(d.chain ?? "-")}</KV></>;
    case "retention":
      return <><KV k="Tier">{String(d.tier)}</KV>
        <KV k="Retention">{d.retention_days ? `${d.retention_days} days, then destroyed with approval` : "kept with the business record it supports"}</KV>
        <KV k="Disposal">{String(d.disposal ?? "-")}</KV><KV k="Disposal authority">{String(d.authority)}</KV>
        {d.disposed_at ? <KV k="Disposed at">{String(d.disposed_at)}</KV> : null}</>;
    case "review":
      return d.reviewer ? <p>{String(d.reviewer)} {String(d.decision).replace(/_/g, " ")} it on {String(d.reviewed_at).slice(0, 10)}.{d.note ? ` Note: ${String(d.note)}` : ""}</p>
        : <p className="muted">No review recorded.</p>;
    case "since": {
      const ch = (d.sources_changed ?? []) as { record_id: string; why: string; superseded_by?: string | null }[];
      return <>{ch.map((c) => <p key={c.record_id}>Source {c.record_id} {c.why}{c.superseded_by ? ` (superseded by ${c.superseded_by})` : ""}.</p>)}
        <KV k="Model">{String(d.model)} ({String(d.model_status)})</KV>
        <KV k="Queued for re-review">{d.queued ? "Yes" : "No"}</KV>
        <p><Link href={typeof d.recall === "string" ? d.recall : "/recall"}>Open Recall</Link></p></>;
    }
    default: {
      const rows = Object.entries(d).filter(([, v]) => v !== null && v !== "");
      return rows.length ? <>{rows.map(([k, v]) => <KV key={k} k={k.replace(/_/g, " ")}>{typeof v === "object" ? JSON.stringify(v) : String(v)}</KV>)}</>
        : <p className="muted">No further detail.</p>;
    }
  }
}

const KV2 = ({ k, children }: { k: string; children: React.ReactNode }) => (
  <div className="pk"><span className="k">{k}</span><span>{children}</span></div>
);

function Card({ p, docName }: { p: S["Passport"]; docName: string }) {
  const { record: r, agent: a, business: b, process: pr, review: rv, integrity: ig, paradata: pd } = p;
  const ev = Object.entries(pr.evidence_summary).filter(([, n]) => n).map(([w, n]) => `${n} ${w}`).join(", ") || "no check recorded";
  const ci = Object.entries(pr.citation_summary).filter(([, n]) => n).map(([k, n]) => `${n} ${CITE_WORDS[k] ?? k}`).join(", ") || "none checked";
  const tools = pr.tool_calls.map((t) => t.name + (t.side_effect ? " (changed something)" : "")).join("; ") || "none";
  const prompt = pr.prompt.length <= 160 ? pr.prompt : pr.prompt.slice(0, 157) + "...";
  return (
    <div className="pass" data-tour="passport">
      <div className="pass-head"><b>Passport</b><span>The record package kept with this output</span></div>
      <div className="groups">
        <div className="group"><h5>Record</h5>
          <KV2 k="Title">{r.title}</KV2><KV2 k="Created">{fmt(r.created)}</KV2>
          <KV2 k="Made with AI">{r.ai_generated ? "Yes, in part" : "No"}</KV2>
          <KV2 k="Filed into">{r.final_document ?? "no document"}</KV2><KV2 k="Content fingerprint">{fp(r.content_hash)}</KV2></div>
        <div className="group"><h5>Agent</h5>
          <KV2 k="Person">{a.person}</KV2><KV2 k="AI system">{a.ai_system}</KV2><KV2 k="Model asked for">{a.model_requested}</KV2>
          <KV2 k="Model that answered">{a.model_returned}</KV2><KV2 k="Provider">{a.provider}</KV2></div>
        <div className="group"><h5>Business</h5>
          <KV2 k="Function">{b.function || "not stated"}</KV2><KV2 k="Risk tier">{TIER_WORDS[b.tier]}</KV2>
          <KV2 k="Why this tier">{b.tier_reason}</KV2><KV2 k="Document type">{docName}</KV2>
          <KV2 k="Filing gate">{b.gate ? GATE_COLOURS[b.gate][2] : "not recorded"}</KV2><KV2 k="Keep for">{b.disposal}</KV2></div>
        <div className="group"><h5>Process</h5>
          <KV2 k="Prompt">{prompt}</KV2><KV2 k="Source records">{pr.source_record_ids.join(", ") || "none"}</KV2>
          <KV2 k="Statements">{ev}</KV2><KV2 k="References">{ci}</KV2><KV2 k="Agent actions">{tools}</KV2></div>
        <div className="group"><h5>Review</h5>
          {rv ? <>
            <KV2 k="Reviewer">{rv.reviewer}</KV2>
            <KV2 k="Decision">{rv.decision.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())}</KV2>
            <KV2 k="Reviewed">{fmt(rv.reviewed_at)}</KV2><KV2 k="Note">{rv.note || "none"}</KV2></>
            : <KV2 k="Reviewer">No review recorded</KV2>}</div>
        <div className="group"><h5>Integrity and policy</h5>
          <KV2 k="Fingerprint">{fp(ig.hash)}</KV2><KV2 k="Previous in chain">{fp(ig.prev_hash)}</KV2>
          <KV2 k="Checks at filing">{pr.checks_hash ? fp(pr.checks_hash) : "not stored (older record)"}</KV2>
          <KV2 k="Judged against">{pd.policy_version}</KV2><KV2 k="Policy fingerprint">{fp(pd.policy_hash)}</KV2>
          <KV2 k="AI use register">{pd.use_register_id}</KV2></div>
      </div>
    </div>
  );
}

function Records() {
  const initial = useSearchParams().get("id");
  const [list, setList] = useState<S["Passport"][] | null>(null);
  const [policy, setPolicy] = useState<S["Policy"] | null>(null);
  const [summary, setSummary] = useState<S["RecordSummary"] | null>(null);
  const [view, setView] = useState<S["PassportView"] | null>(null);
  const [sel, setSel] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [missing, setMissing] = useState("");

  useEffect(() => {
    api<S["Passport"][]>("passports").then((ps) => {
      setList(ps);
      const newest = [...ps].sort((x, y) => y.record.created.localeCompare(x.record.created))[0]?.record.id ?? "";
      setSel(initial ?? newest);   // an unknown ?id= is reported below, never swapped for another record
    }).catch((e) => setError(e.message));
    api<S["Policy"]>("policy").then(setPolicy).catch(() => setPolicy(null));
  }, [initial]);

  useEffect(() => {
    if (!sel || !list) return;
    setSummary(null); setView(null); setMissing("");
    if (!list.some((p) => p.record.id === sel)) { setMissing(sel); return; }
    Promise.all([api<S["RecordSummary"]>(`passport/${sel}/summary`), api<S["PassportView"]>(`passport/${sel}/view`)])
      .then(([s, v]) => { setSummary(s); setView(v); setOpen(v.checks.find((c) => c.status === "problem")?.id ?? null); }).catch((e) => setError(e.message));
  }, [sel, list]);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!list) return <p className="muted">Loading...</p>;

  const cur = list.find((p) => p.record.id === sel);
  const sorted = [...list].sort((x, y) => y.record.created.localeCompare(x.record.created));
  const dtype = cur?.business.document_type;
  const docName = !dtype ? "not stated" : policy?.document_types.find((d) => d.id === dtype)?.name ?? dtype;

  return (
    <>
    <PageHead title="Records">Every AI-assisted output filed as a record, with its passport and the checks done on it.</PageHead>
    <div className="records">
      <section className="panel list" aria-label="Records">
        <div className="panel-head">
          <h2>Records</h2>
          <Link href="/check" className="btn">Check a document</Link>
        </div>
        {!list.length && <p className="muted" style={{ padding: "0 18px" }}>No records yet. Check a document and issue a passport.</p>}
        <div>
          {sorted.map((p) => {
            const on = p.record.id === sel;
            const [bg, fg, label] = p.business.gate ? GATE_COLOURS[p.business.gate] : [...GREY, "Filed"];
            const changed = on && summary?.checks.some((c) => c.id === "since" && c.status === "problem");
            return (
              <Link key={p.record.id} href={`/records?id=${encodeURIComponent(p.record.id)}`}
                className={on ? "row on" : "row"} aria-current={on ? "true" : undefined}>
                <div className="t">
                  <span>{p.record.title}</span>
                  {changed && <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#b45309" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" role="img" aria-label="Changed since filing"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></svg>}
                </div>
                <div className="s">
                  <span className="pill" style={{ background: bg, color: fg }}>{label}</span>
                  <span>{fmtDay(p.record.created)}</span><span>{p.business.tier}</span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      <div className="main">
        {missing && <p className="error" role="alert">Record {missing} not found.</p>}
        {cur && !(summary && view) && <p className="muted">Loading...</p>}
        {cur && summary && view && (
          <>
            <div className="panel hero">
              <div className="eyebrow">
                <span>Record passport</span><span className="mono">{view.record_id}</span>
                {!view.disposed && <a className="btn-sm" href={`/api/passport/${view.record_id}.pdf`}>Download as PDF</a>}
              </div>
              <h1>{view.title}</h1>
              <div className="headline" data-testid="headline"
                style={{ background: STATUS_COLOURS[summary.status][0], color: STATUS_COLOURS[summary.status][1] }}>
                {summary.headline.includes(": ")
                  ? <><b>{summary.headline.split(": ")[0]}:</b><span>{summary.headline.slice(summary.headline.indexOf(": ") + 2)}</span></>
                  : <span>{summary.headline}</span>}
              </div>
              <p className="who">
                Filed by {cur.agent.person} on {fmt(view.filed)} · drafted with {cur.agent.model_returned} ·{" "}
                {view.reviewer ? `reviewed by ${view.reviewer}` : "no reviewer"} · document type: {docName}
              </p>
              <Card p={cur} docName={docName} />
            </div>
            {!view.at_issue && !view.disposed && <div className="older">{SUMMARY_ONLY}</div>}
            {view.disposed && <div className="older">Content destroyed under the disposal authority; hash retained.</div>}
            <div className="panel" data-tour="checks">
              <div className="panel-head"><h2>Checks done on this record</h2><span>Open any check for the detail</span></div>
              {view.checks.map((c) => {
                const [bg, fg] = STATUS_COLOURS[c.status] ?? GREY;
                const isOpen = open === c.id;
                return (
                  <div className="chk" key={c.id}>
                    <button type="button" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : c.id)}>
                      <span className="dot" style={{ background: bg, color: fg }} aria-hidden="true">{STATUS_MARKS[c.status]}</span>
                      <span className="n">{c.name}</span><span className="sm">{c.summary}</span>
                      <span className="tg">{isOpen ? "Hide" : "Details"}</span>
                    </button>
                    {isOpen && <div className="body"><Detail check={c} /></div>}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
    </>
  );
}

export default function Page() {
  return <Suspense fallback={<p className="muted">Loading...</p>}><Records /></Suspense>;
}
