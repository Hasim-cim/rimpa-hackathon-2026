"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, CITE_COLOURS, GATE_COLOURS, Pill, WEIGHT_COLOURS, type Colours, type S } from "@/lib/ui";

const STATUS: Record<string, [string, Colours]> = {
  ok: ["OK", ["#d1f0dc", "#14532d"]], attention: ["Attention", ["#fde8b8", "#7a4a00"]],
  problem: ["Problem", ["#f8d0d0", "#7f1d1d"]], not_run: ["Not run", ["#e5e7eb", "#374151"]],
};
const SUMMARY_ONLY = "Filed before checks were stored with the passport: summary counts only.";
const TIER_WORDS: Record<string, string> = {
  T0: "T0, a transitory log", T1: "T1, a retained output", T2: "T2, informs a decision", T3: "T3, an agent's action",
};
const CITE_WORDS: Record<string, string> = {
  found: "found", mismatch: "details differ", not_found: "not found (possibly fabricated)", not_checked: "for a person to confirm",
};
const HEAD_COLOURS = { green: "#15803d", orange: "#b45309", red: "#b91c1c", blue: "#1d4ed8", gray: "#6b7280" };
const fmt = (s: string) => {
  const d = new Date(s);
  const t = d.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "numeric" });
  return `${t.replace("Sept", "Sep")}, ${d.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
};
const dm = (s: string) => new Date(s).toLocaleDateString("en-AU", { day: "2-digit", month: "short" }).replace("Sept", "Sep");
const fp = (h?: string | null) => (h ? <span className="mono">{h.slice(0, 6)}…{h.slice(-6)}</span> : "none");
const lower = (t: string) => t[0].toLowerCase() + t.slice(1);

/** Same sentences as the console's _headline. */
function headline(v: S["PassportView"]): [string, keyof typeof HEAD_COLOURS] {
  const c = Object.fromEntries(v.checks.map((x) => [x.id, x]));
  if (v.disposed) return ["Disposed: the content was destroyed under an approved authority; its hash is kept in the chain.", "gray"];
  if (c.since?.status === "problem") return ["Changed since filing: " + c.since.summary.replace(/^Since filing: /, ""), "red"];
  if (!v.at_issue) return [`Older record: summary only. ${TIER_WORDS[v.tier]}.`.replace(/^(Older record: summary only\. )(.)/, (_, a, b) => a + b.toUpperCase()), "gray"];
  const ev = c.evidence;
  if (v.gate === "ready") {
    const line = ev.status === "ok" ? "every statement is supported by authoritative records" : lower(ev.summary).replace(/\.$/, "");
    return [`Ready to file: ${line}.`, "green"];
  }
  if (v.gate === "attention") return [`Filed with items to check: ${lower(ev.summary)}`, "orange"];
  return [`Filed: ${ev.summary}`, "blue"];
}

function statusWord(p: S["Passport"], v?: S["PassportView"] | null) {
  if (v?.disposed) return "Disposed";
  if (v?.checks.some((c) => c.id === "since" && c.status === "problem")) return "Changed since filing";
  return ({ ready: "Ready", attention: "To check" } as Record<string, string>)[p.business.gate ?? ""] ?? "Older";
}

type D = Record<string, unknown>;
type Link_ = { record_id: string; rule: string; note: string };
type Item = Record<string, string> & { counted?: boolean; links?: Link_[] };

const KV = ({ k, children }: { k: string; children: React.ReactNode }) => (
  <div style={{ marginBottom: 6, overflowWrap: "anywhere" }}><span className="muted">{k}: </span>{children}</div>
);

function Detail({ check }: { check: S["CheckSummary"] }) {
  const d = (check.details ?? {}) as D;
  const items = (d.items ?? []) as Item[];
  const note = d.note ? <p className="muted">{String(d.note)}</p> : null;
  switch (check.id) {
    case "evidence":
      return <>{note}{d.method ? <p className="muted">Method: {String(d.method)}</p> : null}
        {items.map((v, i) => (
          <div key={i} style={{ margin: "8px 0" }}>
            <Pill text={String(v.weight)} colours={WEIGHT_COLOURS[String(v.weight)]} /> {v.text}<br />
            <span className="muted">{v.reason}</span>
            {v.links?.map((l, j) => (
              <div key={j} className="muted">Record {l.record_id} ({l.rule}){l.note ? `: ${l.note}` : ""}</div>
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
  <div className="pk"><div className="muted">{k}</div><div>{children}</div></div>
);

function Card({ p, docName }: { p: S["Passport"]; docName: string }) {
  const { record: r, agent: a, business: b, process: pr, review: rv, integrity: ig, paradata: pd } = p;
  const ev = Object.entries(pr.evidence_summary).filter(([, n]) => n).map(([w, n]) => `${n} ${w}`).join(", ") || "no check recorded";
  const ci = Object.entries(pr.citation_summary).filter(([, n]) => n).map(([k, n]) => `${n} ${CITE_WORDS[k] ?? k}`).join(", ") || "none checked";
  const tools = pr.tool_calls.map((t) => t.name + (t.side_effect ? " (changed something)" : "")).join("; ") || "none";
  const prompt = pr.prompt.length <= 160 ? pr.prompt : pr.prompt.slice(0, 157) + "...";
  return (
    <div className="card">
      <div className="card-head"><span>RECORD PASSPORT</span><span>{r.id}</span></div>
      <div className="card-grid">
        <div><h5>Record</h5>
          <KV2 k="Title">{r.title}</KV2><KV2 k="Created">{fmt(r.created)}</KV2>
          <KV2 k="Made with AI">{r.ai_generated ? "Yes, in part" : "No"}</KV2>
          <KV2 k="Filed into">{r.final_document ?? "no document"}</KV2><KV2 k="Content fingerprint">{fp(r.content_hash)}</KV2></div>
        <div><h5>Agent</h5>
          <KV2 k="Person">{a.person}</KV2><KV2 k="AI system">{a.ai_system}</KV2><KV2 k="Model asked for">{a.model_requested}</KV2>
          <KV2 k="Model that answered">{a.model_returned}</KV2><KV2 k="Provider">{a.provider}</KV2></div>
        <div><h5>Business</h5>
          <KV2 k="Function">{b.function || "not stated"}</KV2><KV2 k="Risk tier">{TIER_WORDS[b.tier]}</KV2>
          <KV2 k="Why this tier">{b.tier_reason}</KV2><KV2 k="Document type">{docName}</KV2>
          <KV2 k="Filing gate">{b.gate ? GATE_COLOURS[b.gate][2] : "not recorded"}</KV2><KV2 k="Keep for">{b.disposal}</KV2></div>
        <div><h5>Process</h5>
          <KV2 k="Prompt">{prompt}</KV2><KV2 k="Source records">{pr.source_record_ids.join(", ") || "none"}</KV2>
          <KV2 k="Statements">{ev}</KV2><KV2 k="References">{ci}</KV2><KV2 k="Agent actions">{tools}</KV2></div>
        <div><h5>Review</h5>
          {rv ? <>
            <KV2 k="Reviewer">{rv.reviewer}</KV2>
            <KV2 k="Decision">{rv.decision.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())}</KV2>
            <KV2 k="Reviewed">{fmt(rv.reviewed_at)}</KV2><KV2 k="Note">{rv.note || "none"}</KV2></>
            : <KV2 k="Reviewer">No review recorded</KV2>}</div>
        <div><h5>Integrity and policy</h5>
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
  const [view, setView] = useState<S["PassportView"] | null>(null);
  const [sel, setSel] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<S["Passport"][]>("passports").then((ps) => {
      setList(ps);
      setSel(initial && ps.some((p) => p.record.id === initial) ? initial : ps[0]?.record.id ?? "");
    }).catch((e) => setError(e.message));
    api<S["Policy"]>("policy").then(setPolicy).catch(() => setPolicy(null));
  }, [initial]);

  useEffect(() => {
    if (!sel) return;
    setView(null);
    api<S["PassportView"]>(`passport/${sel}/view`).then(setView).catch((e) => setError(e.message));
  }, [sel]);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!list) return <p className="muted">Loading...</p>;

  const cur = list.find((p) => p.record.id === sel);
  const sorted = [...list].sort((x, y) => y.record.created.localeCompare(x.record.created));
  const dtype = cur?.business.document_type;
  const docName = !dtype ? "not stated" : policy?.document_types.find((d) => d.id === dtype)?.name ?? dtype;
  const [head, colour] = view ? headline(view) : ["", "gray" as const];
  const ran = view?.checks.filter((c) => c.status !== "not_run") ?? [];
  const skipped = view?.checks.filter((c) => c.status === "not_run").map((c) => c.name) ?? [];

  return (
    <div className="records">
      <div>
        <Link href="/check" className="btn">Check a document</Link>
        <h3>Records</h3>
        <p className="muted">Newest first. Click a row to open it.</p>
        {!list.length && <p className="muted">No records yet. Check a document and issue a passport.</p>}
        <div className="rows">
          {sorted.map((p) => (
            <Link key={p.record.id} href={`/?id=${encodeURIComponent(p.record.id)}`}
              className={p.record.id === sel ? "row on" : "row"} aria-current={p.record.id === sel ? "true" : undefined}>
              <span>{p.record.title.split(" (")[0]}, {dm(p.record.created)}</span>
              <span className="muted">{statusWord(p, p.record.id === sel ? view : null)}</span>
            </Link>
          ))}
        </div>
      </div>

      <div>
        {cur && !view && <p className="muted">Loading...</p>}
        {cur && view && (
          <>
            <h2 className="headline" style={{ color: HEAD_COLOURS[colour] }}>{head}</h2>
            <p>
              {view.title}. Filed {fmt(view.filed)} by {cur.agent.person} with {cur.agent.ai_system};{" "}
              {view.reviewer ? `reviewed by ${view.reviewer}.` : "no reviewer."}
            </p>
            <Card p={cur} docName={docName} />
            {!view.disposed && <p><a href={`/api/passport/${view.record_id}.pdf`}>Print passport (PDF)</a></p>}
            {view.disposed && <p className="muted">Content destroyed under the disposal authority; hash retained.</p>}
            <h3>Checks done on this record</h3>
            {!view.at_issue && !view.disposed && <p className="muted">{SUMMARY_ONLY}</p>}
            {ran.map((c) => {
              const [label, colours] = STATUS[c.status];
              return (
                <details className="check" key={c.id} open={c.status === "problem"}>
                  <summary><Pill text={label} colours={colours} /> <b>{c.name}</b>: {c.summary}</summary>
                  <div className="body"><Detail check={c} /></div>
                </details>
              );
            })}
            {skipped.length > 0 && <p className="muted">
              {view.at_issue ? "Not run for this document: " : "Not recorded for this older record: "}{skipped.join(", ")}.</p>}
          </>
        )}
      </div>
    </div>
  );
}

export default function Page() {
  return <Suspense fallback={<p className="muted">Loading...</p>}><Records /></Suspense>;
}
