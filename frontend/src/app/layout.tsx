import type { Metadata } from "next";
import { IBM_Plex_Mono, Manrope, Space_Grotesk } from "next/font/google";

import { SiteHeader } from "@/components/layout/site-header";
import { cn } from "@/lib/utils";

import "./globals.css";

const displayFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display"
});

const bodyFont = Manrope({
  subsets: ["latin"],
  variable: "--font-body"
});

const monoFont = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono"
});

export const metadata: Metadata = {
  title: "OpsGuard AI",
  description:
    "Incident triage with runbook retrieval, typed local tools, policy checks, and adversarial testing."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={cn(
          displayFont.variable,
          bodyFont.variable,
          monoFont.variable,
          "font-body text-slate-50 antialiased"
        )}
      >
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
