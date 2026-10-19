"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [["/setup", "Setup"], ["/", "Check"], ["/passport", "Passport"], ["/recall", "Recall"],
  ["/disposal", "Disposal"], ["/register", "Register"]];

export default function Nav() {
  const path = usePathname();
  return (
    <nav>
      {TABS.map(([href, label]) => (
        <Link key={href} href={href} aria-current={path === href ? "page" : undefined}>{label}</Link>
      ))}
    </nav>
  );
}
