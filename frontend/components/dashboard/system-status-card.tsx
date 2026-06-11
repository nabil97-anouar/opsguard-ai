import { AlertTriangle, Cpu, Database, ShieldCheck } from "lucide-react";

import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import type { HealthPayload } from "@/lib/types";

type SystemStatusCardProps = {
  health: HealthPayload | null;
  documentsCount: number;
  trustedDocumentsCount: number;
  toolsCount: number;
  policiesCount: number;
  isLoading: boolean;
};

const systemRows = [
  {
    label: "Backend API",
    icon: Cpu,
    value: (health: HealthPayload | null) => health?.status ?? "loading"
  },
  {
    label: "Environment",
    icon: ShieldCheck,
    value: (health: HealthPayload | null) => health?.environment ?? "local"
  },
  {
    label: "LLM provider",
    icon: Database,
    value: (health: HealthPayload | null) => health?.dependencies.llm_provider ?? "mock"
  }
];

export function SystemStatusCard({
  health,
  documentsCount,
  trustedDocumentsCount,
  toolsCount,
  policiesCount,
  isLoading
}: SystemStatusCardProps) {
  return (
    <Card className="relative overflow-hidden border-accent/20 bg-gradient-to-br from-white/[0.08] via-white/[0.04] to-accent/10">
      <div className="absolute right-8 top-8 h-24 w-24 rounded-full bg-accent/20 blur-3xl" />
      <div className="relative">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-accentSoft">
              System posture
            </p>
            <CardTitle className="mt-3">Local-first, guardrailed, human-approved</CardTitle>
            <CardDescription className="mt-3 max-w-xl">
              The dashboard runs on the deterministic local backend. No real
              infrastructure actions, no external LLM calls, and no destructive
              controls are exposed here.
            </CardDescription>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.18em] text-success">
            <ShieldCheck className="h-3.5 w-3.5" />
            {isLoading ? "Syncing" : "Mock-safe mode"}
          </div>
        </div>

        <div className="mt-8 grid gap-4">
          {systemRows.map((row) => (
            <div
              className="flex items-center justify-between rounded-2xl border border-white/8 bg-ink/60 px-4 py-3"
              key={row.label}
            >
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-accentSoft">
                  <row.icon className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm text-slate-200">{row.label}</p>
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                    Live contract
                  </p>
                </div>
              </div>

              <SafetyBadge value={row.value(health)} />
            </div>
          ))}
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-white/8 bg-ink/60 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
              Knowledge base
            </p>
            <p className="mt-3 text-2xl font-semibold text-white">{documentsCount}</p>
            <p className="mt-2 text-sm text-slate-300">
              {trustedDocumentsCount} trusted documents,{" "}
              {Math.max(documentsCount - trustedDocumentsCount, 0)} untrusted
              sources
            </p>
          </div>

          <div className="rounded-2xl border border-white/8 bg-ink/60 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
              Control surface
            </p>
            <p className="mt-3 text-2xl font-semibold text-white">
              {toolsCount} / {policiesCount}
            </p>
            <p className="mt-2 text-sm text-slate-300">
              allowlisted tools and watchdog policies currently exposed
            </p>
          </div>
        </div>

        <div className="mt-6 flex items-start gap-3 rounded-2xl border border-warning/20 bg-warning/10 p-4 text-sm text-amber-50">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>
            Human approval is always required before any dangerous or disruptive
            action recommendation can move beyond this UI.
          </p>
        </div>
      </div>
    </Card>
  );
}
