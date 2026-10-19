import { GATE_COLOURS, type S } from "@/lib/ui";
import Waves from "./waves";

const TIER_WORDS: Record<string, string> = {
  T0: "T0, a transitory log", T1: "T1, a retained output", T2: "T2, informs a decision", T3: "T3, an agent's action",
};
const CITE_WORDS: Record<string, string> = {
  found: "found", mismatch: "details differ", not_found: "not found (possibly fabricated)", not_checked: "for a person to confirm",
};
// Stored times are naive UTC; read them as UTC so they show in the viewer's local time.
export const utc = (s: string) => new Date(/T[^Z+]*$/.test(s) && !/-\d\d:\d\d$/.test(s) ? `${s}Z` : s);
export const fmt = (s: string) => {
  const d = utc(s);
  const t = d.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "numeric" });
  return `${t.replace("Sept", "Sep")}, ${d.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
};
export const fp = (h?: string | null) => (h ? <span className="mono">{h.slice(0, 6)}…{h.slice(-6)}</span> : "none");

const KV2 = ({ k, children }: { k: string; children: React.ReactNode }) => (
  <div className="pk"><span className="k">{k}</span><span>{children}</span></div>
);

export function PassportCard({ p, docName }: { p: S["Passport"]; docName: string }) {
  const { record: r, agent: a, business: b, process: pr, review: rv, integrity: ig, paradata: pd } = p;
  const ev = Object.entries(pr.evidence_summary).filter(([, n]) => n).map(([w, n]) => `${n} ${w}`).join(", ") || "no check recorded";
  const ci = Object.entries(pr.citation_summary).filter(([, n]) => n).map(([k, n]) => `${n} ${CITE_WORDS[k] ?? k}`).join(", ") || "none checked";
  const tools = pr.tool_calls.map((t) => t.name + (t.side_effect ? " (changed something)" : "")).join("; ") || "none";
  const prompt = pr.prompt.length <= 160 ? pr.prompt : pr.prompt.slice(0, 157) + "...";
  return (
    <div className="pass" data-tour="passport">
      <div className="pass-head"><Waves className="waves" count={10} height={40} yellow="#f2b705" magenta="#f2b705" /><b>Passport</b><span>The record package kept with this output</span></div>
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

