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

  const caption = doc ? (doc.case_id && !doc.title.includes(doc.case_id) ? `${doc.title} · case ${doc.case_id}` : doc.title) + (dtype ? ` · ${dtype.name}` : "") : "Run the checks on a draft before it is filed.";
  const nCite = (k: string) => result ? count(result.citations, (c) => c.status, k) : 0;
  const nWeight = (...ks: string[]) => result ? result.assessment.verdicts.filter((v) => ks.includes(v.weight)).length : 0;
  const plural = (n: number, one: string, many = one + "s") => `${n} ${n === 1 ? one : many}`;
  const reasonParts = [
    nCite("not_found") && `${nCite("not_found")} reference${nCite("not_found") === 1 ? "" : "s"} not found`,
    nCite("mismatch") && `${nCite("mismatch")} mismatched`,
    nCite("not_checked") && `${nCite("not_checked")} not checked`,
    nWeight("unsupported", "contradicted") && `${plural(nWeight("unsupported", "contradicted"), "statement")} unsupported or contradicted`,
  ].filter(Boolean) as string[];

  return (
    <div className="stack">
      <PageHead title="Check a document">{caption}</PageHead>
      <section className="panel panel-pad" aria-label="Choose a document">
        <div className="controls">
          <div><label htmlFor="doc">Document</label>
            <select id="doc" value={docId} onChange={(e) => pickDoc(e.target.value)}>
              {docs.map((d) => <option key={d.id} value={d.id}>{d.id}  {d.title}</option>)}
            </select></div>
          <div><label htmlFor="type">Document type</label>
            <select id="type" value={typeId} onChange={(e) => setTypeId(e.target.value)}>
              {policy?.document_types.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select></div>
          <button className="run" onClick={() => run()} disabled={loading || !doc}>{loading ? "Checking..." : "Run check"}</button>
        </div>
        {doc && (
          <details open={!result} style={{ marginTop: 14 }}>
            <summary className="muted">Draft as submitted (case {doc.case_id || "none"})</summary>
            <p>{doc.body}</p>
            <pre>{doc.references}</pre>
          </details>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        {!result && !loading && !error && doc && <p className="muted">Run the check to look up each reference and trace each sentence to authoritative records.</p>}
      </section>

      {result && gate && (
        <>
          <div data-tour="gate" className="stack">
            {gate.status === "ready"
              ? <div className="banner ok"><span className="ic" aria-hidden="true">✓</span><span className="txt"><b>Ready to file:</b> every check passes the bar for {dtype?.name} (policy v{policy?.version}).</span></div>
              : <div className="banner bad" role="status">
                  <span className="txt"><b>Needs a person before filing:</b>{" "}
                    {reasonParts.length ? reasonParts.join(", ") + "." : gate.reasons.map((r) => r.text).join(" ")}</span>
                  <SendForReview doc={doc} typeId={typeId} />
                </div>}
            <section className="panel panel-pad" aria-label="Filing gate">
              <span className="gate" style={{ background: GATE_COLOURS[gate.status][0], color: GATE_COLOURS[gate.status][1] }}>
                {GATE_COLOURS[gate.status][2]}
              </span>
              <span className="muted"> {dtype?.name}. Bar set by the information manager in policy v{policy?.version}.</span>
              <ul>{gate.reasons.map((r, i) => <li key={i}>{r.text}</li>)}</ul>
            </section>
          </div>

          <section className="panel panel-pad" aria-label="Citations">
            <div className="panel-head" style={{ padding: "0 0 8px", border: 0 }}>
              <h2>Citations</h2><span>Checked against Federal Register of Legislation, Crossref and OpenAlex</span>
            </div>
            {!result.citations.length && <p className="muted">This document cites no references.</p>}
            {result.citations.map((r) => (
              <div className="cite" key={r.citation.n} data-tour={`cite-${r.citation.n}`}>
                <Pill text={CITE_LABELS[r.status] ?? r.status} colours={CITE_COLOURS[r.status]} />
                <div><b>[{r.citation.n}]</b> {r.citation.raw}<br /><span className="note">{noteFor(r)}</span></div>
              </div>
            ))}
          </section>

          <section className="panel panel-pad" aria-label="The draft, sentence by sentence">
            <div className="panel-head" style={{ padding: "0 0 8px", border: 0 }}>
              <h2>The draft, sentence by sentence</h2><span>Select a sentence to see its trace</span>
            </div>
            <div className="doc">
              {claims.map((c) => {
                const v = verdicts.get(c.id);
                const [bg, fg] = v ? WEIGHT_COLOURS[v.weight] : GREY;
                return (
                  <span key={c.id}>
                    <span className="sent" data-weight={v?.weight} data-tour={c.text.includes("$4,860") ? "claim-4860" : undefined} role="button" tabIndex={0} aria-pressed={c.id === selected}
                      title={v ? `${v.weight}: ${v.reason}` : ""} style={{ background: bg, color: fg }}
                      onClick={() => setSelected(c.id)}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(c.id); } }}>
                      {c.text}<sup>{c.author.toUpperCase()}</sup>
                    </span>{" "}
                  </span>
                );
              })}
            </div>
            <p className="muted" style={{ marginTop: 12 }}>
              {Object.keys(WEIGHT_COLOURS).map((k) => <span key={k}><Pill text={k[0].toUpperCase() + k.slice(1)} colours={WEIGHT_COLOURS[k]} />{" "}</span>)}
              {" "}AI / HUMAN marks who wrote the sentence. The colour says whether authoritative records support it, whoever wrote it.
            </p>
          </section>

          {claim && verdict && (
            <section className="trace" aria-label="Trace">
              <div className="who2">
                <h2>Trace</h2><Pill text={cap(verdict.weight)} colours={WEIGHT_COLOURS[verdict.weight]} />
                <em>Author: <b>{claim.author.toUpperCase()}</b></em>
              </div>
              <blockquote>&ldquo;{claim.text}&rdquo;</blockquote>
              <p><b>Reason.</b> {verdict.reason}</p>
              {verdict.links?.length ? (
                <div className="tt">
                  <table>
                    <thead><tr><th>Record</th><th>Title</th><th>System</th><th>Status</th><th>Rule</th><th>Note</th></tr></thead>
                    <tbody>
                      {verdict.links.map((l, i) => {
                        const rec = records.find((r) => r.id === l.record_id);
                        return (
                          <tr key={i}><td><a href={`/records?id=${encodeURIComponent(l.record_id)}`}>{l.record_id}</a></td><td>{rec?.title}</td><td>{rec?.system}</td>
                            <td><b>{rec?.status}</b></td><td className="mono">{l.rule}</td><td>{l.note}</td></tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : <p className="muted">No authoritative record is linked to this claim.</p>}
            </section>
          )}

          {gate && doc && <FileAsRecord doc={doc} typeId={typeId} typeName={dtype?.name ?? typeId} result={result} gate={gate.status} />}
        </>
      )}
    </div>
  );
}

const CITE_LABELS: Record<string, string> = { found: "Found", mismatch: "Mismatch", not_found: "Not found", not_checked: "Not checked" };
const cap = (t: string) => t[0].toUpperCase() + t.slice(1);
const SOURCE_NAMES: Record<string, string> = { crossref: "Crossref", openalex: "OpenAlex", frl: "Federal Register of Legislation" };

/** The note under a citation. An offline-copy match says where the answer came from (source and time), never the word "Fixture". */
function noteFor(r: S["CitationResult"]) {
  if (!/^fixture match/i.test(r.note)) return r.note;
  if (r.source === "fixture") return "Crossref, offline copy";
  if (r.checked_at && SOURCE_NAMES[r.source]) {
    const t = new Date(/Z|[+-]\d\d:\d\d$/.test(r.checked_at) ? r.checked_at : `${r.checked_at}Z`);
    return `${SOURCE_NAMES[r.source]}, live, ${t.toLocaleString("en-AU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false })}`;
  }
  return "Offline copy of the lookup";
}

/** Sends a draft the gate does not pass to a person (POST /api/drafts/review). Shows what the server answers, never a made-up success. */
function SendForReview({ doc, typeId }: { doc?: S["Document"]; typeId: string }) {
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [sent, setSent] = useState<S["DraftReview"] | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { setState("idle"); setSent(null); setErr(""); }, [doc?.id, typeId]);
  async function send() {
    if (!doc) return;
    setState("sending"); setErr("");
    try {
      const r = await api<S["DraftReview"]>("drafts/review", { json: { document_id: doc.id, document_type: typeId, requested_by: AUTHOR } });
      setSent(r); setState("sent");
    } catch (e) {
      setErr((e as Error).message); setState("idle");
    }
  }
  if (state === "sent" && sent) {
    return (
      <div role="status" style={{ flexBasis: "100%" }}>
        <b>Sent for review ({sent.id})</b>
        <ul style={{ margin: "4px 0 0" }}>{sent.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
      </div>
    );
  }
  return (
    <>
      <button type="button" className="btn-mag" onClick={send} disabled={state === "sending" || !doc}>{state === "sending" ? "Sending..." : "Send for review →"}</button>
      {err && <span role="alert" className="flag-text" style={{ flexBasis: "100%" }}>{err}</span>}
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
    <section className="panel panel-pad" aria-label="File as record">
      <h2 style={{ marginTop: 0 }}>File as record</h2>
      <label htmlFor="reviewer">Reviewer name</label>
      <input id="reviewer" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
      <label htmlFor="decision">Decision</label>
      <select id="decision" value={decision} onChange={(e) => setDecision(e.target.value as typeof decision)}>
        {["approved", "approved_with_edits", "rejected"].map((d) => <option key={d} value={d}>{d.replace(/_/g, " ")}</option>)}
      </select>
      <label style={{ fontWeight: 400, display: "flex", gap: 8, alignItems: "center" }}>
        <input type="checkbox" style={{ width: "auto" }} checked={flag} onChange={(e) => setFlag(e.target.checked)} /> Output informs a decision about a person, case or money
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
    </section>
  );
}

export default function Page() {
  return <Suspense fallback={<p className="muted">Loading...</p>}><Check /></Suspense>;
}
