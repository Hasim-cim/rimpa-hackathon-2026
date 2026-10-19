/** Record Passport mark: a passport booklet with a check. One colour, so it prints. */
export default function Logo({ size = 28, colour = "#1e3a8a" }: { size?: number; colour?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="6" y="3" width="20" height="26" rx="3" stroke={colour} strokeWidth="2.2" />
      <path d="M10 3v26" stroke={colour} strokeWidth="2.2" />
      <circle cx="18" cy="13" r="5" stroke={colour} strokeWidth="2" />
      <path d="M15.6 13.2l1.7 1.7 3.2-3.4" stroke={colour} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 22h8M14 25h5" stroke={colour} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
