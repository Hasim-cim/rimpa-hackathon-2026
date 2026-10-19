import type { components } from "@/lib/api";

export type S = components["schemas"];
export type Colours = [string, string];

// Colour rule (docs/decisions.md, 19 Oct): green = accepted / supported / ready, yellow = narrow or weak, pink = needs a
// person / unsupported / not found, solid magenta = contradicted or Blocked, grey = not run. Every status also carries an
// icon (STATUS_MARKS), so it never relies on colour alone. The values are CSS variables defined in app/globals.css.
export const OK: Colours = ["var(--ok-bg)", "var(--ok-ink)"];
export const ATTN: Colours = ["var(--attn-bg)", "var(--attn-ink)"];
export const BAD: Colours = ["var(--bad-bg)", "var(--bad-ink)"];
export const BLOCKED: Colours = ["var(--blocked-bg)", "var(--blocked-ink)"];
export const GREY: Colours = ["var(--grey-bg)", "var(--grey-ink)"];
export const BLUE: Colours = ["var(--blue-bg)", "var(--blue-ink)"];
export const CITE_COLOURS: Record<string, Colours> = { found: OK, mismatch: ATTN, not_found: BAD, not_checked: ATTN };
export const WEIGHT_COLOURS: Record<string, Colours> = { supported: OK, weak: ATTN, unsupported: BAD, contradicted: BLOCKED };
export const GATE_COLOURS: Record<string, [string, string, string]> = {
  ready: [...OK, "Ready to file"], attention: [...ATTN, "Needs review"], blocked: [...BLOCKED, "Blocked"],
};
export const TIER_COLOURS: Record<string, Colours> = { T0: BAD, T1: BAD, T2: BAD, T3: BAD };  // small magenta-text chips (.tier); a scale, not a status
export const STATUS_COLOURS: Record<string, Colours> = { ok: OK, attention: ATTN, problem: BAD, not_run: GREY };
export const STATUS_MARKS: Record<string, string> = { ok: "✓", attention: "!", problem: "✕", not_run: "–" };
export const DISPOSAL_COLOURS: Record<string, Colours> = { due: BAD, "on hold": ATTN };
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

export function Tier({ tier }: { tier: string }) {
  return <span className="tier">{tier}</span>;
}

export function GatePill({ status }: { status: string }) {
  const [bg, fg, label] = GATE_COLOURS[status];
  return <span className="gate" style={{ background: bg, color: fg }}>{label}</span>;
}

export const short = (h?: string | null) => (h ? `${h.slice(0, 12)}…` : "-");
