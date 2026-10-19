"use client";

import { useEffect, useState } from "react";
import { api, type S } from "@/lib/ui";

/** The console's "AI search reliability" card, from GET /sources/reliability. `refresh` re-fetches it after a mark. */
export default function Reliability({ refresh = 0 }: { refresh?: number }) {
  const [rel, setRel] = useState<S["ReliabilityReport"] | null>(null);
  useEffect(() => { api<S["ReliabilityReport"]>("sources/reliability").then(setRel).catch(() => setRel(null)); }, [refresh]);
  if (!rel) return null;
  const figure = rel.share == null ? "none yet" : `${rel.sources_ok} of ${rel.with_sources}`;
  return (
    <section className="rel" aria-label="AI search reliability" data-tour="reliability">
      <div>
        <span className="eyebrow">AI search reliability</span>
        <span className="big">{figure}</span>
        <span>retained AI outputs that cite records rest on current authoritative records</span>
        <span className="note">These outputs cite records that are still current. It says nothing about unsupported statements: see Needs a person on the Dashboard.</span>
      </div>
      <div>
        <b>Pulling it down</b>
        {rel.drag?.length
          ? rel.drag.map((d) => <div key={d.record_id}>{d.record_id} {d.title}: {d.why} ({d.outputs} output{d.outputs === 1 ? "" : "s"})</div>)
          : <div>Every source these outputs cite still counts as evidence.</div>}
      </div>
    </section>
  );
}
