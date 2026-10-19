"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const MANAGER = [["/setup", "Setup"], ["/recall", "Recall"], ["/disposal", "Disposal"], ["/register", "Register"], ["/passport", "Passport detail"]];
const TABS = [["/", "Records"], ["/check", "Check a document"], ["/setup", "Information manager"]];

export default function Nav() {
  const path = usePathname();
  const inManager = MANAGER.some(([href]) => href === path);
  const current = (href: string) => (href === "/setup" ? inManager : path === href) ? "page" : undefined;
  return (
    <>
      <nav>
        {TABS.map(([href, label]) => <Link key={href} href={href} aria-current={current(href)}>{label}</Link>)}
      </nav>
      {inManager && (
        <nav className="sub" aria-label="Information manager">
          {MANAGER.map(([href, label]) => <Link key={href} href={href} aria-current={path === href ? "page" : undefined}>{label}</Link>)}
        </nav>
      )}
    </>
  );
}
