"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { tourSet } from "@/lib/tour";
import { api, ApiError, OK, CITE_COLOURS, GATE_COLOURS, GatePill, GREY, Pill, WEIGHT_COLOURS, type S } from "@/lib/ui";
import PageHead from "../page-head";

const DEFAULT_DOC = "DOC-2026/0412-summary";
const DOC_TYPE_HINTS = [["summary", "decision-letter"], ["briefing", "briefing"], ["agent-note", "case-note"], ["eligibility", "case-note"]];

function defaultType(pol: S["Policy"], doc: S["Document"]) {
  const key = `${doc.id} ${doc.title}`.toLowerCase();
  const ids = pol.document_types.map((d) => d.id);
  for (const [needle, id] of DOC_TYPE_HINTS) if (key.includes(needle) && ids.includes(id)) return id;
  return ids[0];
}

// Guided demo steps: which document and type each one checks, and runs the (read-only) check on arrival.
const TOUR_DOCS: Record<string, [string, string]> = {
  "1": ["DOC-2026/0412-summary", "decision-letter"], "2": ["DOC-2026/0587-eligibility", "case-note"], "4b": ["DOC-2026/0412-summary", "decision-letter"],
};

function Check() {
  const tour = useSearchParams().get("tour") ?? "";
  const [docs, setDocs] = useState<S["Document"][]>([]);
  const [records, setRecords] = useState<S["SourceRecord"][]>([]);
  const [policy, setPolicy] = useState<S["Policy"] | null>(null);
  const [docId, setDocId] = useState("");
  const [typeId, setTypeId] = useState("");
  const [result, setResult] = useState<S["CheckResponse"] | null>(null);
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<S["Document"][]>("documents"), api<S["SourceRecord"][]>("records"), api<S["Policy"]>("policy")])
      .then(([d, r, p]) => {
        setDocs(d); setRecords(r); setPolicy(p);
        const first = d.find((x) => x.id === DEFAULT_DOC) ?? d[0];
        setDocId(first.id); setTypeId(defaultType(p, first));
      })
      .catch((e) => setError(e.message));
  }, []);

  const doc = docs.find((d) => d.id === docId);
  const dtype = policy?.document_types.find((t) => t.id === typeId);

  function pickDoc(id: string) {
    setDocId(id); setResult(null); setError("");
    const d = docs.find((x) => x.id === id);
    if (d && policy) setTypeId(defaultType(policy, d));
  }

  useEffect(() => {
    const t = TOUR_DOCS[tour];
    if (!t || !policy || !docs.some((d) => d.id === t[0])) return;
    setDocId(t[0]); setTypeId(t[1]); setResult(null);
    run(t[0], t[1]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tour, policy, docs]);

  async function run(id = docId, type = typeId) {
    setLoading(true); setError("");
    try {
      const r = await api<S["CheckResponse"]>("check", {
        json: { document_id: id, document_type: type } });
      setResult(r);
      setSelected([...r.assessment.claims].sort((a, b) => a.position - b.position)[0]?.id ?? "");
    } catch (e) {
      setResult(null); setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const count = <T,>(xs: T[], key: (x: T) => string, k: string) => xs.filter((x) => key(x) === k).length;
  const claims = result ? [...result.assessment.claims].sort((a, b) => a.position - b.position) : [];
  const verdicts = new Map(result?.assessment.verdicts.map((v) => [v.claim_id, v]));
  const claim = claims.find((c) => c.id === selected);
  const verdict = claim && verdicts.get(claim.id);
  const gate = result?.gate;

  return (
    <>
      <PageHead title="Check a document">Run the checks on a draft before it is filed.</PageHead>
      <label htmlFor="doc">Document</label>
      <select id="doc" value={docId} onChange={(e) => pickDoc(e.target.value)}>
        {docs.map((d) => <option key={d.id} value={d.id}>{d.id}  {d.title}</option>)}
      </select>
      {doc && (
        <>
          <h3>{doc.title}</h3>
          <p className="muted">Case {doc.case_id || "none"}. Draft as submitted:</p>
          <p>{doc.body}</p>
          <details><summary>References as submitted</summary><pre>{doc.references}</pre></details>
        </>
      )}

      <label htmlFor="type">Document type</label>
      <select id="type" value={typeId} onChange={(e) => setTypeId(e.target.value)}>
        {policy?.document_types.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select>
      <button className="run" onClick={() => run()} disabled={loading || !doc}>{loading ? "Checking..." : "Run check"}</button>
      {error && <p className="error" role="alert">{error}</p>}
      {!result && !loading && !error && doc && <p className="muted">Run the check to look up each reference and trace each sentence to authoritative records.</p>}

      {result && (
        <>
          <div className="counts">
            {["found", "mismatch", "not_found", "not_checked"].map((k) => (
              <div key={k}><b>{count(result.citations, (c) => c.status, k)}</b>Citations {k.replace("_", " ")}</div>
            ))}
            {Object.keys(WEIGHT_COLOURS).map((k) => (
              <div key={k}><b>{count(result.assessment.verdicts, (v) => v.weight, k)}</b>{k[0].toUpperCase() + k.slice(1)}</div>
            ))}
          </div>

          <h2>Filing gate: {dtype?.name}</h2>
          {gate && (
            <div data-tour="gate">
              <span className="gate" style={{ background: GATE_COLOURS[gate.status][0], color: GATE_COLOURS[gate.status][1] }}>
                {GATE_COLOURS[gate.status][2]}
              </span>
              <ul>{gate.reasons.map((r, i) => <li key={i}>{r.text}</li>)}</ul>
            </div>
          )}
          <p className="muted">Bar set by the information manager in policy v{policy?.version}.</p>

          <h2>Citations</h2>
          {!result.citations.length && <p className="muted">This document cites no references.</p>}
          {result.citations.map((r) => (
            <div className="cite" key={r.citation.n} data-tour={`cite-${r.citation.n}`}>
              <Pill text={r.status.replace("_", " ")} colours={CITE_COLOURS[r.status]} />
              <div><b>[{r.citation.n}]</b> {r.citation.raw}<br /><span className="muted">{r.note}</span></div>
            </div>
          ))}

          <h2>The draft, sentence by sentence</h2>
          <div className="doc">
            {claims.map((c) => {
              const v = verdicts.get(c.id);
              const [bg, fg] = v ? WEIGHT_COLOURS[v.weight] : GREY;
              return (
                <span key={c.id}>
                  <span className="sent" data-tour={c.text.includes("$4,860") ? "claim-4860" : undefined} role="button" tabIndex={0} aria-pressed={c.id === selected}
                    title={v ? `${v.weight}: ${v.reason}` : ""} style={{ background: bg, color: fg }}
                    onClick={() => setSelected(c.id)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(c.id); } }}>
                    {c.text}<sup>{c.author.toUpperCase()}</sup>
                  </span>{" "}
                </span>
              );
            })}
          </div>
          <p className="muted" style={{ marginTop: 8 }}>
            {Object.keys(WEIGHT_COLOURS).map((k) => <span key={k}><Pill text={k} colours={WEIGHT_COLOURS[k]} />{" "}</span>)}
            {" "}AI / HUMAN marks who wrote the sentence. A weight says whether authoritative records support it, whoever wrote it.
          </p>

          {claim && verdict && (
            <>
              <h2>Trace</h2>
              <p><Pill text={verdict.weight} colours={WEIGHT_COLOURS[verdict.weight]} /> &nbsp; Author: <b>{claim.author.toUpperCase()}</b></p>
              <p>{claim.text}</p>
              <p><b>Reason.</b> {verdict.reason}</p>
              {verdict.links?.length ? (
                <table>
                  <thead><tr><th>Record id</th><th>Title</th><th>System</th><th>Status</th><th>Rule</th><th>Note</th></tr></thead>
                  <tbody>
                    {verdict.links.map((l, i) => {
                      const rec = records.find((r) => r.id === l.record_id);
                      return (
                        <tr key={i}><td>{l.record_id}</td><td>{rec?.title}</td><td>{rec?.system}</td><td>{rec?.status}</td><td>{l.rule}</td><td>{l.note}</td></tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : <p className="muted">No authoritative record is linked to this claim.</p>}
            </>
          )}

          {gate && doc && <FileAsRecord doc={doc} typeId={typeId} typeName={dtype?.name ?? typeId} result={result} gate={gate.status} />}
        </>
      )}
    </>
  );
}

const AUTHOR = "A. Caseworker";
const MODEL = "northstar-8-2026-09-15";

/** The business function a filed document performs, from the document itself (same rule as the console's _doc_function). */
function docFunction(doc: S["Document"], typeName: string) {
  const title = doc.title.split(",")[0];
  if (title.startsWith("Briefing: ")) return "Policy briefing";
  if (title.startsWith("Case note drafted by")) return "Case note summary";
  return title.replace(/ note$/, "").replace(/ summary$/, "") || typeName;
}

function FileAsRecord({ doc, typeId, typeName, result, gate }: { doc: S["Document"]; typeId: string; typeName: string; result: S["CheckResponse"]; gate: string }) {
  const [reviewer, setReviewer] = useState("B. Team Leader");
  const [decision, setDecision] = useState<S["Review"]["decision"]>("approved");
  const [flag, setFlag] = useState(true);
  const [msg, setMsg] = useState<{ ok: boolean; text: string; id?: string } | null>(null);
  const blocked = gate === "blocked";

  async function issue() {
    const now = new Date();
    const iso = now.toISOString().replace("Z", "");   // naive UTC, like the seed data, until the engine handles aware datetimes
    const stamp = iso.replace(/[-:T]/g, "").slice(0, 14);
    const event: S["AIEvent"] = {
      id: `EVT-${stamp}-${Math.random().toString(16).slice(2, 6).padEnd(4, "0")}`, app_id: "agency-assistant", user: AUTHOR, created: iso,
      prompt: `Draft the ${doc.title.split(",")[0].toLowerCase()}${doc.case_id ? ` for case ${doc.case_id}` : ""} and cite the records relied on`, output: doc.body,
      model_requested: MODEL, model_returned: MODEL, provider: "Northstar AI (fictional vendor)",
      source_record_ids: result.relied_on ?? [],  // the server sets these again from the evidence
      exported_to_document: doc.id, decision_flag: flag, function: docFunction(doc, typeName),
    };
    const review = reviewer.trim() ? { reviewer: reviewer.trim(), decision, reviewed_at: iso } : null;
    try {
      const p = await api<S["Passport"]>("passport", {
        json: { event, review, document_type: typeId, citations: result.citations, assessment: result.assessment } });
      tourSet("record", p.record.id); tourSet("issued");
      setMsg({ ok: true, text: `Passport issued: ${p.record.id} (${p.business.tier})`, id: p.record.id });
    } catch (e) {
      const d = e instanceof ApiError ? e.detail : null;
      const why = typeof d === "object" && d && "reasons" in d ? (d as { reasons: string[] }).reasons.join(" ") : (e as Error).message;
      setMsg({ ok: false, text: `Not filed: ${why}` });
    }
  }

  return (
    <>
      <h2>File as record</h2>
      <label htmlFor="reviewer">Reviewer name</label>
      <input id="reviewer" value={reviewer} onChange={(e) => setReviewer(e.target.value)}
        style={{ width: "100%", padding: 8, font: "inherit", border: "1px solid #9ca3af", borderRadius: 6 }} />
      <label htmlFor="decision">Decision</label>
      <select id="decision" value={decision} onChange={(e) => setDecision(e.target.value as typeof decision)}>
        {["approved", "approved_with_edits", "rejected"].map((d) => <option key={d} value={d}>{d.replace(/_/g, " ")}</option>)}
      </select>
      <label style={{ fontWeight: 400 }}>
        <input type="checkbox" checked={flag} onChange={(e) => setFlag(e.target.checked)} /> Output informs a decision about a person, case or money
      </label>
      <p>Gate before review: <GatePill status={gate} /></p>
      <p className="muted">The engine runs the gate again with the review when you file.</p>
      {blocked && <p className="error" role="alert">Blocked by policy: fix the document or ask the information manager to change the bar.</p>}
      <button className="run" onClick={issue} disabled={blocked} data-tour="issue">Issue passport</button>
      {msg && (msg.ok
        ? <p role="status" data-tour="issued" style={{ background: OK[0], color: OK[1], padding: "8px 12px", borderRadius: 6, marginTop: 12 }}>
            {msg.text}. <a href={`/records?id=${encodeURIComponent(msg.id!)}`}>Open it in Records</a>
          </p>
        : <p className="error" role="alert">{msg.text}</p>)}
    </>
  );
}

export default function Page() {
  return <Suspense fallback={<p className="muted">Loading...</p>}><Check /></Suspense>;
}
