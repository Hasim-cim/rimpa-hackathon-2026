"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Logo from "./logo";
import { api, type S } from "@/lib/ui";

const ENTRIES = [
  ["/check", "Check a document", "Run the checks on a draft before it is filed."],
  ["/records", "Records", "Every passport, its checks, and what changed since filing."],
  ["/dashboard", "Information manager", "Dashboard, recall and the rules you set."],
];
const STEPS = [
  ["Check", "References looked up, each sentence traced to authoritative records."],
  ["Gate", "The information manager's bar decides if it can be filed."],
  ["Passport", "The record package kept with the output."],
  ["Recall", "When a source or model changes, find everything that relied on it."],
];

// Counts come straight from the API; if either call fails the row is hidden.
function Live() {
  const [d, setD] = useState<S["DashboardReport"] | null>(null);
  const [r, setR] = useState<S["ReliabilityReport"] | null>(null);
  useEffect(() => {
    api<S["DashboardReport"]>("dashboard").then(setD).catch(() => setD(null));
    api<S["ReliabilityReport"]>("sources/reliability").then(setR).catch(() => setR(null));
  }, []);
  if (!d || !r) return null;
  return (
    <section aria-label="Right now">
      <h2>Right now</h2>
      <div className="live">
        {d.kpis.slice(0, 3).map((k) => <div key={k.id}><b>{k.display}</b>{k.label}</div>)}
        <div><b>{r.share == null ? "none yet" : `${r.sources_ok} of ${r.with_sources}`}</b>AI outputs citing records rest on current authoritative records</div>
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
    <>
      <Suspense fallback={null}><Redirect /></Suspense>
      <div className="land-hero">
        <Logo size={72} />
        <h1 className="name">Record Passport</h1>
        <p className="lead">Every AI-assisted output that becomes a record gets a passport: what it rests on, who approved it, and what changed since.</p>
        <p className="sub">For the information manager: check a document before it is filed, keep the evidence with the record, and recall what relied on a source when it changes.</p>
        {process.env.NEXT_PUBLIC_MODE === "demo" && <Link href="/check?tour=1" className="start">Start the demo</Link>}
      </div>
      <nav aria-label="Start here" className="entries">
        {ENTRIES.map(([href, title, text]) => <Link key={href} href={href} className="entry"><b>{title}</b><span>{text}</span></Link>)}
      </nav>
      <ol className="steps">
        {STEPS.map(([t, text]) => <li key={t}><b>{t}</b>{text}</li>)}
      </ol>
      <Live />
    </>
  );
}
