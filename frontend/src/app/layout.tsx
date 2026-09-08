import type { Metadata } from "next";

import { SiteHeader } from "@/components/layout/site-header";

import "./globals.css";

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
      <body className="font-body text-slate-50 antialiased">
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
