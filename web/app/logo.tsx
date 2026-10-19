/**
 * Record Passport mark: a teal booklet with a yellow R and a magenta P, yellow lines, a bookmark ribbon and a magenta
 * seal with a check. `tone="on-dark"` swaps the cover to yellow so it reads on the teal header. Scales with `size` (width).
 */
export default function Logo({ size = 28, tone = "default", className }: { size?: number; tone?: "default" | "on-dark"; className?: string }) {
  const dark = tone === "on-dark";
  const cover = dark ? "#f2b705" : "#00485f";
  const r = dark ? "#00485f" : "#f2b705";
  const lines = dark ? "#00485f" : "#f2b705";
  const ribbon = dark ? "#f2b705" : "#00485f";
  return (
    <svg className={className} width={size} height={(size * 130) / 114} viewBox="0 0 114 130" fill="none" aria-hidden="true" focusable="false">
      <path d="M16 106v22l8-6 8 6v-22z" fill={ribbon} />
      <rect x="8" y="4" width="76" height="104" rx="8" fill={cover} />
      <path fillRule="evenodd" d="M20 20h20c9 0 16 6 16 15 0 7-4 12-10 14l11 17H46L37 50h-8v16H20zM29 28v14h10c4 0 7-3 7-7s-3-7-7-7z" fill={r} />
      <path fillRule="evenodd" d="M52 36h18c8 0 13 5 13 12.5S78 61 70 61H60v21h-8zM60 43v11h9c3 0 5-2 5-5.5S72 43 69 43z" fill="#d6007a" />
      <rect x="30" y="88" width="42" height="3.5" rx="1.5" fill={lines} />
      <rect x="40" y="96" width="32" height="3.5" rx="1.5" fill={lines} />
      <circle cx="84" cy="98" r="25" fill="#d6007a" />
      <circle cx="84" cy="98" r="21" stroke="#fff" strokeWidth="3" strokeDasharray="1.5 1.7" />
      <circle cx="84" cy="98" r="16.5" fill="#fff" />
      <path d="M76 98.5l6 6 12-12.5" stroke="#1d1d1b" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
