import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import { Suspense } from "react";
import Logo from "./logo";
import Nav from "./nav";
import TourBar from "./tour-bar";
import "./globals.css";

export const metadata: Metadata = { title: "Record Passport", description: "Every AI-assisted output that becomes a record gets a passport." };

const sans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--sans" });
const serif = Source_Serif_4({ subsets: ["latin"], weight: ["400", "600"], variable: "--serif" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--mono" });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} ${serif.variable}`}>
      <body>
        <header>
          <div className="bar">
            <div className="brand">
              <Link href="/" className="home" aria-label="Record Passport home">
                <Logo size={26} tone="on-dark" />
                <span className="name">Record Passport</span>
              </Link>
              <span className="marker" title="All cases, people and records are invented">Example data: all invented</span>
            </div>
            <Nav />
          </div>
        </header>
        <main>{children}</main>
        <Suspense fallback={null}><TourBar /></Suspense>
      </body>
    </html>
  );
}
