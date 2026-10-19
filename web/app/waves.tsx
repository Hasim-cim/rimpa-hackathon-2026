/** Decorative thin, overlapping sine waves in magenta and yellow. Deterministic (no randomness), so it renders the same on server and client. */
const W = 1440;

function wave(i: number, h: number) {
  const amp = h * (0.12 + 0.34 * ((i * 37) % 11) / 10);
  const len = 260 + ((i * 131) % 7) * 120;
  const phase = (i * 97) % 360;
  const mid = h / 2 + (((i * 53) % 9) - 4) * (h * 0.015);
  let d = "";
  for (let x = 0; x <= W; x += 12) {
    const y = mid + amp * Math.sin(((x / len) * 360 + phase) * (Math.PI / 180));
    d += `${x === 0 ? "M" : "L"}${x} ${y.toFixed(1)} `;
  }
  return d;
}

export default function Waves({ count = 14, height = 150, className, magenta = "#e0609f", yellow = "#e6c55a" }: { count?: number; height?: number; className?: string; magenta?: string; yellow?: string }) {
  return (
    <svg className={className} viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none" aria-hidden="true" focusable="false">
      {Array.from({ length: count }, (_, i) => (
        <path key={i} d={wave(i + 1, height)} fill="none" stroke={i % 2 ? yellow : magenta} strokeWidth="1" vectorEffect="non-scaling-stroke" opacity="0.7" />
      ))}
    </svg>
  );
}
