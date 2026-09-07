import Link from "next/link";
import { ShieldCheck } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/config";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/#overview", label: "Overview" },
  { href: "/#controls", label: "Scenarios" },
  { href: "/#traces", label: "Trace" },
  { href: "/#harness", label: "Harness" },
  { href: "/#evaluation", label: "Evaluation" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-ink/80 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
        <Link className="flex items-center gap-3" href="/">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/40 bg-accent/10 text-accent">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div>
            <p className="font-display text-sm uppercase tracking-[0.28em] text-accentSoft">
              OpsGuard AI
            </p>
            <p className="text-sm text-slate-400">
              Incident investigation and policy review
            </p>
          </div>
        </Link>

        <nav className="hidden items-center gap-2 md:flex">
          {navItems.map((item) => (
            <Link
              className={cn(
                "rounded-full px-4 py-2 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white"
              )}
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <a
            className={buttonVariants({ variant: "ghost" })}
            href={`${API_BASE_URL}/health`}
            rel="noreferrer"
            target="_blank"
          >
            API Health
          </a>
          <Link className={buttonVariants()} href="/#controls">
            Run a scenario
          </Link>
        </div>
      </div>
    </header>
  );
}
