import type { Metadata } from "next";
import Nav from "./nav";
import "./globals.css";

export const metadata: Metadata = { title: "Record Check" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main>
          <header>
            <h1>Record Check</h1>
            <span className="marker" title="Every case, person and record is invented">Example data</span>
            <Nav />
          </header>
          {children}
        </main>
      </body>
    </html>
  );
}
