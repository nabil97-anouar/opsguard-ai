import { AlertTriangle, Cpu, Database, ShieldCheck } from "lucide-react";

import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import type { HealthPayload, ReasoningRuntime } from "@/lib/types";

type SystemStatusCardProps = {
  health: HealthPayload | null;
  documentsCount: number;
  trustedDocumentsCount: number;
  executableToolsCount: number;
  blockedToolsCount: number;
  policiesCount: number;
  isLoading: boolean;
  reasoning: ReasoningRuntime | null;
};

export function SystemStatusCard({
  health,
  documentsCount,
  trustedDocumentsCount,
  executableToolsCount,
  blockedToolsCount,
  policiesCount,
  isLoading,
  reasoning
}: SystemStatusCardProps) {
  const systemRows = [
    { label: "System", icon: Cpu, value: health?.status ?? "unavailable", detail: health?.environment ?? "no response" },
    { label: "Reasoning", icon: Database, value: reasoning?.provider ?? "unavailable", detail: reasoning?.model ?? "not configured" },
    { label: "Provider mode", icon: ShieldCheck, value: reasoning?.available ? reasoning.mode : "unavailable", detail: reasoning?.schema_version ?? "schema unavailable" }
  ];
  return (
    <Card className="matrix-panel relative overflow-hidden">
      <div className="absolute right-8 top-8 h-24 w-24 rounded-full bg-accent/20 blur-3xl" />
      <div className="relative">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-accentSoft">
              System posture
            </p>
            <CardTitle className="mt-3">Runtime authority map</CardTitle>
            <CardDescription className="mt-3 max-w-xl">
              Runtime data identifies the active provider. Evidence validation, tool policy,
              watchdog decisions, and review requirements remain application-owned.
            </CardDescription>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.18em] text-success">
            <ShieldCheck className="h-3.5 w-3.5" />
            {isLoading ? "Syncing" : reasoning?.available ? "Provider available" : "Provider unavailable"}
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
                    Backend response
                  </p>
                </div>
              </div>

              <div className="text-right">
                <SafetyBadge value={row.value} />
                <p className="mt-2 max-w-52 break-all font-mono text-[10px] text-slate-500">{row.detail}</p>
              </div>
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
              {Math.max(documentsCount - trustedDocumentsCount, 0)} with other
              trust labels
            </p>
          </div>

          <div className="rounded-2xl border border-white/8 bg-ink/60 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
              Registered components
            </p>
            <p className="mt-3 text-2xl font-semibold text-white">
              {executableToolsCount} executable adapters
            </p>
            <p className="mt-2 text-sm text-slate-300">
              {blockedToolsCount} blocked action definitions · {policiesCount} watchdog policies
            </p>
          </div>
        </div>

        <div className="mt-6 flex items-start gap-3 rounded-2xl border border-warning/20 bg-warning/10 p-4 text-sm text-amber-50">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>
            Destructive tool requests are blocked. Recommendations require review
            outside the application; there is no approval or execution control here.
          </p>
        </div>
      </div>
    </Card>
  );
}
