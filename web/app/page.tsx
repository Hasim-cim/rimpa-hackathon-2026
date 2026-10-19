"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Logo from "./logo";
import Waves from "./waves";
import { api, type S } from "@/lib/ui";

const ENTRIES = [
  ["/check", "Check a document", "Run the checks on a draft before it is filed."],
  ["/records", "Records", "Every passport, its checks, and what changed since filing."],
  ["/dashboard", "Information Integrity Dashboard", "Dashboard, recall and the rules you set."],
];
const STEPS = [
  ["Check", "References looked up, each sentence traced to authoritative records."],
  ["Gate", "The information manager's bar decides if it can be filed."],
  ["Passport", "The record package kept with the output."],
  ["Recall", "When a source or model changes, find everything that relied on it."],
];

// Counts come straight from the API; if either call fails the row is hidden. Captions come from the API's own labels.
const tail = (label: string) => {
  const t = label.includes(": ") ? label.slice(label.indexOf(": ") + 2).replace(/^\d+ of \d+ /, "") : label;
  return t[0].toUpperCase() + t.slice(1);
};
const TILES: Record<string, [string, string]> = { filed_approved: ["Approved", "ok"], needs_review: ["Needs a person", "bad"], narrow_evidence: ["Narrow evidence", "attn"] };

function LiveTile({ cls, eyebrow, n, of, pct, caption }: { cls: string; eyebrow: string; n: number; of: number; pct: number | null; caption: string }) {
  return (
    <div className={`tile ${cls}`}>
      <span className="eb">{eyebrow}</span>
      <div className="nm"><b>{n}</b><i>of {of}</i>{pct != null && <span className="pct">{pct}%</span>}</div>
      <div className="pbar" aria-hidden="true"><span style={{ width: `${pct ?? 0}%` }} /></div>
      <span className="cap">{caption}</span>
    </div>
  );
}

function Live() {
  const [d, setD] = useState<S["DashboardReport"] | null>(null);
  const [r, setR] = useState<S["ReliabilityReport"] | null>(null);
  useEffect(() => {
    api<S["DashboardReport"]>("dashboard").then(setD).catch(() => setD(null));
    api<S["ReliabilityReport"]>("sources/reliability").then(setR).catch(() => setR(null));
  }, []);
  if (!d || !r) return null;
  return (
    <section aria-label="Right now" className="right-now">
      <h2>Right now</h2>
      <div className="live">
        {d.kpis.filter((k) => TILES[k.id]).map((k) => (
          <LiveTile key={k.id} cls={TILES[k.id][1]} eyebrow={TILES[k.id][0]} n={k.count} of={k.total} pct={k.percent == null ? null : Math.round(k.percent)}
            caption={k.id === "filed_approved" ? k.label : tail(k.label)} />
        ))}
        <LiveTile cls="blue" eyebrow="Current sources" n={r.sources_ok} of={r.with_sources} pct={r.share == null ? null : Math.round(r.share * 100)}
          caption="AI outputs citing records rest on current authoritative records" />
      </div>
    </section>
  );
}

// Old links like /?id=REC-... still work.
function Redirect() {
  const router = useRouter();
  const id = useSearchParams().get("id");
  useEffect(() => { if (id) router.replace(`/records?id=${encodeURIComponent(id)}`); }, [id, router]);
  return null;
}

export default function Landing() {
  return (
    <div className="land">
      <Suspense fallback={null}><Redirect /></Suspense>
      <div className="land-hero">
        <Waves className="waves" />
        <Logo size={124} className="logo" />
        <h1>Record Passport</h1>
        <p className="lead">Every AI-assisted output that becomes a record gets a passport: what it rests on, who approved it, and what changed since.</p>
        <p className="sub">For the information manager: check a document before it is filed, keep the evidence with the record, and recall what relied on a source when it changes.</p>
        {process.env.NEXT_PUBLIC_MODE === "demo" && <Link href="/check?tour=1" className="start">Start the demo</Link>}
      </div>
      <nav aria-label="Start here" className="entries">
        {ENTRIES.map(([href, title, text]) => <Link key={href} href={href} className={href === "/dashboard" ? "entry dark" : "entry"}><b>{title}</b><span>{text}</span><span className="arrow" aria-hidden="true">→</span></Link>)}
      </nav>
      <ol className="steps">
        {STEPS.map(([t, text]) => <li key={t}><span className="num" aria-hidden="true">{STEPS.findIndex((x) => x[0] === t) + 1}</span><b>{t}</b>{text}</li>)}
      </ol>
      <Live />
    </div>
  );
}
