"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { tourClear, tourGet } from "@/lib/tour";

const LABELS = ["Check the draft", "Fix and re-check", "Issue the passport", "The source changes", "Recall"];

/** Which `data-tour` targets to ring, given the step and what the presenter has done so far. */
function wanted(step: string, f: { issued: boolean; marked: boolean; queued: boolean; late: boolean }): string[] {
  switch (step) {
    case "1": return ["gate", "cite-4"];
    case "2": return f.issued ? ["issued"] : f.late ? ["issue"] : ["gate"];
    case "3": return ["passport", "checks"];
    case "4": return f.marked ? ["reliability"] : ["mark"];
    case "4b": return ["claim-4860"];
    case "5": return f.queued ? ["queued"] : ["source-results", "queue"];
    default: return [];
  }
}

export default function TourBar() {
  const params = useSearchParams();
  const path = usePathname();
  const step = params.get("tour") ?? "";
  const valid = ["1", "2", "3", "4", "4b", "5"].includes(step);
  const [f, setF] = useState({ issued: false, marked: false, queued: false, record: "" });
  const [late, setLate] = useState(false);
  const seen = useRef("");

  useEffect(() => {
    const read = () => setF({ issued: !!tourGet("issued"), marked: !!tourGet("marked"), queued: !!tourGet("queued"), record: tourGet("record") });
    read();
    window.addEventListener("tour-state", read);
    return () => window.removeEventListener("tour-state", read);
  }, []);

  // A fresh run starts clean, so a second take of the demo does not show last time's progress.
  useEffect(() => { if (step === "1") tourClear(); }, [step]);

  useEffect(() => {
    document.body.classList.toggle("touring", valid);
    return () => document.body.classList.remove("touring");
  }, [valid]);

  // On step 2 the gate is shown first, then the Issue button a moment later.
  useEffect(() => {
    setLate(false);
    if (step !== "2") return;
    const t = setTimeout(() => setLate(true), 2500);
    return () => clearTimeout(t);
  }, [step]);

  // Ring the current targets and scroll the first newly ringed one into view.
  useEffect(() => {
    if (!valid) return;
    const want = wanted(step, { ...f, late });
    const apply = () => {
      const els = want.flatMap((k) => Array.from(document.querySelectorAll<HTMLElement>(`[data-tour="${k}"]`)))
        .filter((e) => !(e instanceof HTMLButtonElement && e.disabled));
      document.querySelectorAll(".tour-hl").forEach((e) => { if (!els.includes(e as HTMLElement)) e.classList.remove("tour-hl"); });
      const fresh = els.filter((e) => !e.classList.contains("tour-hl"));
      els.forEach((e) => e.classList.add("tour-hl"));
      const sig = `${step}|${want.join(",")}`;
      if (fresh.length && seen.current !== sig) {
        seen.current = sig;
        const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const tall = fresh[0].getBoundingClientRect().height > window.innerHeight * 0.6;
        fresh[0].scrollIntoView({ block: tall ? "start" : "center", behavior: calm ? "auto" : "smooth" });
      }
    };
    apply();
    let raf = 0;
    const mo = new MutationObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(apply); });
    mo.observe(document.body, { childList: true, subtree: true });
    return () => { mo.disconnect(); cancelAnimationFrame(raf); document.querySelectorAll(".tour-hl").forEach((e) => e.classList.remove("tour-hl")); };
  }, [valid, step, f, late]);

  if (!valid) return null;
  const n = step === "4b" ? 4 : Number(step);
  const recordHref = f.record ? `/records?id=${encodeURIComponent(f.record)}&tour=3` : "/records?tour=3";
  const hrefs: Record<string, string> = { "1": "/check?tour=1", "2": "/check?tour=2", "3": recordHref, "4": "/recall?tour=4", "4b": "/check?tour=4b", "5": "/recall?tour=5" };
  const back = step === "4b" ? "4" : step === "5" ? "4" : String(n - 1);
  const next = step === "4" || step === "4b" ? "5" : String(n + 1);
  const sentence: Record<string, string> = {
    "1": "A draft is checked before it is filed: the gate reads Blocked because reference [4] was not found and is possibly fabricated.",
    "2": f.issued ? "The passport is issued: the record is filed with its checks and its approval." : "The fixed note passes the same checks and the gate reads Ready to file, by the bar the information manager set.",
    "3": "The passport keeps what the output rests on, who approved it, and the checks done on it, including the bias check.",
    "4": f.marked ? "The reliability figure has dropped: AI outputs that cited the old record no longer rest on current authoritative records." : "A newer record replaces a source. It stops counting as evidence at once.",
    "4b": "The same draft, checked again: the $4,860 sentence is now contradicted by the replacement record.",
    "5": f.queued ? "Journey complete: the information manager found everything that relied on the old source and queued the decision-informing records for re-review." : "Recall lists every AI output that relied on the superseded source, and the T2 records that informed a decision.",
  };
  const rest = new URLSearchParams(params.toString()); rest.delete("tour");
  const endHref = `${path}${rest.size ? `?${rest}` : ""}`;
  const done = step === "5" && f.queued;

  return (
    <nav className="tour" aria-label="Guided demo">
      <ol className="tour-steps">
        {LABELS.map((l, i) => (
          <li key={l} aria-current={i + 1 === n ? "step" : undefined} className={i + 1 < n ? "past" : i + 1 === n ? "now" : ""}>
            <span className="tn">{i + 1}</span>{l}
          </li>
        ))}
      </ol>
      <div className="tour-row">
        <p className="tour-say" role="status">{sentence[step]}</p>
        <div className="tour-act">
          {step === "4" && f.marked && <Link href="/check?tour=4b" className="tour-link">See the draft again</Link>}
          {done && <Link href="/" className="tour-btn go" onClick={tourClear}>Back to the start</Link>}
          <Link href={endHref} className="tour-link" onClick={tourClear}>End tour</Link>
          {n > 1 && <Link href={hrefs[back]} className="tour-btn" role="button">Back</Link>}
          {n < 5 && <Link href={hrefs[next]} className="tour-btn go" role="button">Next</Link>}
        </div>
      </div>
    </nav>
  );
}
