"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// One top bar (Hasim, 19 Oct): every important page in one click, the IM pages after a divider, the rest under More.
const MAIN = [["/records", "Records"], ["/check", "Check a document"]];
const MANAGER = [["/dashboard", "Dashboard"], ["/recall", "Recall"], ["/setup", "Setup"]];
const MORE = [["/disposal", "Disposal"], ["/register", "Register"]];

export default function Nav() {
  const path = usePathname();
  const link = ([href, label]: string[]) => (
    <Link key={href} href={href} aria-current={path === href ? "page" : undefined}>{label}</Link>
  );
  const inMore = MORE.some(([href]) => href === path);
  return (
    <nav aria-label="Main" className="tabs">
      {MAIN.map(link)}
      {MANAGER.map(link)}
      <details className="more" onClick={(e) => { if ((e.target as HTMLElement).closest("a")) e.currentTarget.open = false; }}>
        <summary aria-current={inMore ? "page" : undefined}>More</summary>
        <div className="menu">{MORE.map(link)}</div>
      </details>
    </nav>
  );
}
