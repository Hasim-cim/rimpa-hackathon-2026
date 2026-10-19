"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ATTN, CITE_COLOURS, BAD, GATE_COLOURS, GREY, OK, Pill, STATUS_COLOURS, STATUS_MARKS, WEIGHT_COLOURS, type S } from "@/lib/ui";
import PageHead from "../page-head";
import { fmt, fp, utc, PassportCard as Card } from "../passport-card";

const SUMMARY_ONLY = "Filed before checks were stored with the passport: summary counts only.";
const cap = (t: string) => t[0].toUpperCase() + t.slice(1);
const fmtDay = (s: string) => utc(s).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" }).replace("Sept", "Sep");

type D = Record<string, unknown>;
type Link_ = { record_id: string; rule: string; note: string };
type Item = Record<string, string> & { counted?: boolean; links?: Link_[] };

/** "Ready to file." style lead: the part of the API headline before its colon, else from the status. Counts only: no new maths. */
const lead = (s: S["RecordSummary"]) => s.headline.includes(": ") ? s.headline.split(": ")[0] : s.status === "ok" ? "Ready to file" : "Needs a person";
const countsLine = (cs: S["CheckSummary"][]) => {
  const n = (st: string) => cs.filter((c) => c.status === st).length;
  const extra = [n("not_run") && `${n("not_run")} not applicable`, n("attention") && `${n("attention")} need${n("attention") === 1 ? "s" : ""} attention`, n("problem") && `${n("problem")} with a problem`].filter(Boolean);
  return `${n("ok")} of ${cs.length} checks passed${extra.length ? "; " + extra.join("; ") : ""}.`;
};

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

type Row = { record_id: string; title: string; case_id?: string | null; tier: string; function?: string | null; created: string;
  gate?: string | null; status?: string | null; status_label?: string | null; changed_since?: boolean | null; document_type?: string | null };
const rowFrom = (p: S["Passport"]): Row => ({ record_id: p.record.id, title: p.record.title, tier: p.business.tier, function: p.business.function, created: p.record.created, gate: p.business.gate });
const chipColours = (label: string) => /person|problem/i.test(label) ? BAD : /changed/i.test(label) ? ATTN : /dispos|log/i.test(label) ? GREY : OK;
const chipMark = (label: string) => /person|problem/i.test(label) ? "✕" : /changed/i.test(label) ? "!" : /dispos|log/i.test(label) ? "–" : "✓";

function Records() {
  const params = useSearchParams();
  const router = useRouter();
  const initial = params.get("id");
  const q = params.get("q") ?? "", fStatus = params.get("status") ?? "", fTier = params.get("tier") ?? "", fFn = params.get("fn") ?? "";
  const [rows, setRows] = useState<Row[] | null>(null);
  const [hasStatus, setHasStatus] = useState(false);
  const setFilter = (k: string, v: string) => {
    const n = new URLSearchParams(params.toString());
    if (v) n.set(k, v); else n.delete(k);
    router.replace(`/records${n.toString() ? `?${n}` : ""}`, { scroll: false });
  };
  const clearFilters = () => {
    const n = new URLSearchParams(params.toString());
    ["q", "status", "tier", "fn"].forEach((k) => n.delete(k));
    router.replace(`/records${n.toString() ? `?${n}` : ""}`, { scroll: false });
  };
  const rowHref = (id: string) => {
    const n = new URLSearchParams(params.toString()); n.set("id", id);
    return `/records?${n}`;
  };
  const [list, setList] = useState<S["Passport"][] | null>(null);
  const [policy, setPolicy] = useState<S["Policy"] | null>(null);
  const [summary, setSummary] = useState<S["RecordSummary"] | null>(null);
  const [view, setView] = useState<S["PassportView"] | null>(null);
  const [sel, setSel] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [missing, setMissing] = useState("");

  useEffect(() => {
    api<Row[]>("records/index").then((r) => { setRows(r); setHasStatus(r.some((x) => x.status)); })
      .catch(() => api<S["Passport"][]>("passports").then((ps) => { setRows(ps.map(rowFrom)); setHasStatus(false); }).catch(() => {}));
  }, []);

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
  const all = [...(rows ?? list.map(rowFrom))].sort((x, y) => y.created.localeCompare(x.created));
  const statuses = [...new Map(all.filter((r) => r.status).map((r) => [r.status!, r.status_label ?? r.status!])).entries()];
  const fns = [...new Set(all.map((r) => r.function).filter((f): f is string => !!f))].sort();
  const needle = q.trim().toLowerCase();
  const shown = all.filter((r) => (!needle || [r.title, r.record_id, r.case_id ?? ""].some((x) => x.toLowerCase().includes(needle)))
    && (!fStatus || r.status === fStatus) && (!fTier || r.tier === fTier) && (!fFn || r.function === fFn));
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
        <div className="filters">
          <input type="search" aria-label="Search records" placeholder="Search title, record id or case id" value={q} onChange={(e) => setFilter("q", e.target.value)} />
          <div className="frow">
            {hasStatus && (
              <select aria-label="Status" value={fStatus} onChange={(e) => setFilter("status", e.target.value)}>
                <option value="">All statuses</option>
                {statuses.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
              </select>
            )}
            <select aria-label="Tier" value={fTier} onChange={(e) => setFilter("tier", e.target.value)}>
              <option value="">All tiers</option>
              {["T0", "T1", "T2", "T3"].map((t) => <option key={t}>{t}</option>)}
            </select>
            <select aria-label="Business function" value={fFn} onChange={(e) => setFilter("fn", e.target.value)}>
              <option value="">All functions</option>
              {fns.map((f) => <option key={f}>{f}</option>)}
            </select>
          </div>
          <div className="fcount">
            <span className="muted" role="status">Showing {shown.length} of {all.length}</span>
            {(q || fStatus || fTier || fFn) && <button type="button" className="linkbtn" onClick={clearFilters}>Clear filters</button>}
          </div>
        </div>
        {!list.length && <p className="muted" style={{ padding: "0 18px" }}>No records yet. Check a document and issue a passport.</p>}
        {list.length > 0 && !shown.length && <p className="muted" style={{ padding: "0 18px 14px" }}>No records match these filters.</p>}
        <div>
          {shown.map((p) => {
            const on = p.record_id === sel;
            const [bg, fg, label] = p.status_label ? [...chipColours(p.status_label), `${chipMark(p.status_label)} ${p.status_label}`]
              : p.gate ? GATE_COLOURS[p.gate] : [...GREY, "Filed"];
            const changed = p.changed_since ?? (on && summary?.checks.some((c) => c.id === "since" && c.status === "problem"));
            return (
              <Link key={p.record_id} href={rowHref(p.record_id)}
                className={on ? "row on" : "row"} aria-current={on ? "true" : undefined}>
                <div className="t">
                  <span>{p.title}</span>
                  {changed && <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#b45309" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" role="img" aria-label="Changed since filing"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></svg>}
                </div>
                <div className="s">
                  <span className="pill" style={{ background: bg, color: fg }}>{label}</span>
                  <span>{fmtDay(p.created)}</span><span className="tier">{p.tier}</span>
                </div>
                <div className="s ids"><span className="mono">{p.record_id}</span>{p.case_id && <span>Case {p.case_id}</span>}</div>
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
            <div className={`banner ${summary.status === "ok" ? "ok" : summary.status === "problem" ? "bad" : "attn"}`} data-testid="check-counts">
              <span className="ic" aria-hidden="true" style={summary.status === "ok" ? undefined : { display: "none" }}>✓</span>
              <span className="txt"><b>{lead(summary)}.</b> {countsLine(view.checks)}</span>
            </div>
            <div className="panel" data-tour="checks">
              <div className="panel-head"><h2>Checks done on this record</h2><span>Open any check for the detail</span></div>
              {view.checks.map((c) => {
                const [bg, fg] = STATUS_COLOURS[c.status] ?? GREY;
                const isOpen = open === c.id;
                return (
                  <div className={isOpen ? "chk open" : "chk"} key={c.id}>
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
