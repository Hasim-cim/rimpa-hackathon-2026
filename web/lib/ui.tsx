import type { components } from "@/lib/api";

export type S = components["schemas"];
export type Colours = [string, string];

// Same palette as the Streamlit console (prototype/record-check/app/streamlit_app.py).
export const GREY: Colours = ["#e5e7eb", "#374151"];
export const CITE_COLOURS: Record<string, Colours> = {
  found: ["#d1f0dc", "#14532d"], mismatch: ["#fde8b8", "#7a4a00"], not_found: ["#f8d0d0", "#7f1d1d"], not_checked: GREY,
};
export const WEIGHT_COLOURS: Record<string, Colours> = {
  supported: ["#d1f0dc", "#14532d"], weak: ["#fde8b8", "#7a4a00"], unsupported: ["#f8d0d0", "#7f1d1d"], contradicted: ["#4b5563", "#ffffff"],
};
export const GATE_COLOURS: Record<string, [string, string, string]> = {
  ready: ["#d1f0dc", "#14532d", "Ready to file"], attention: ["#fde8b8", "#7a4a00", "Needs attention"], blocked: ["#f8d0d0", "#7f1d1d", "Blocked"],
};
export const TIER_COLOURS: Record<string, Colours> = {
  T0: GREY, T1: ["#d6e6fb", "#1e3a8a"], T2: ["#fde8b8", "#7a4a00"], T3: ["#f8d0d0", "#7f1d1d"],
};
export const DISPOSAL_COLOURS: Record<string, Colours> = { due: ["#fde8b8", "#7a4a00"], "on hold": GREY };
export const TIERS = ["T0", "T1", "T2", "T3"] as const;
export const ESCALATION_LABELS: Record<string, string> = {
  exported_to_document: "Output filed into a document", decision_flag: "Output informs a decision",
  side_effect_tool_call: "Agent took an action with side effects",
};

/** Calls the Python service at /api. Throws with the API's `detail` (a string, or {reasons} when the gate blocks). */
export class ApiError extends Error {
  constructor(message: string, public status: number, public detail: unknown) { super(message); }
}

export async function api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {};
  const res = await fetch(`/api/${path}`, json === undefined ? rest : {
    ...rest, method: rest.method ?? "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(json),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const d = body?.detail;
    const msg = typeof d === "string" ? d
      : Array.isArray(d?.reasons) ? d.reasons.join(" ")
      : Array.isArray(d) ? d.map((e: { loc?: unknown[]; msg?: string }) => `${(e.loc ?? []).slice(1).join(".")}: ${e.msg}`).join("; ")
      : `Request failed (${res.status})`;
    throw new ApiError(msg, res.status, d);
  }
  return body as T;
}

export function Pill({ text, colours }: { text: string; colours?: Colours }) {
  const [bg, fg] = colours ?? GREY;
  return <span className="pill" style={{ background: bg, color: fg }}>{text}</span>;
}

export function GatePill({ status }: { status: string }) {
  const [bg, fg, label] = GATE_COLOURS[status];
  return <span className="gate" style={{ background: bg, color: fg }}>{label}</span>;
}

export const short = (h?: string | null) => (h ? `${h.slice(0, 12)}…` : "-");
