import { Bot, LoaderCircle, Siren, TriangleAlert } from "lucide-react";

import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { DEMO_ALERT_IDS } from "@/lib/types";

type AlertScenarioCardProps = {
  onRunGpuScenario: () => Promise<void> | void;
  onRunPromptScenario: () => Promise<void> | void;
  runningScenario: "gpu" | "prompt" | null;
  latestRunStatus: string | null;
  disabled?: boolean;
  providerLabel?: string | null;
};

const scenarioCards = [
  {
    key: "gpu" as const,
    title: "GPU abuse investigation",
    description:
      "Investigates a synthetic mining alert using the configured reasoning provider.",
    alertId: DEMO_ALERT_IDS.gpuAbuse,
    severity: "critical",
    source: "slurm-monitor",
    icon: Bot,
  },
  {
    key: "prompt" as const,
    title: "Prompt-injection poisoning",
    description:
      "Exercises poisoned runbook retrieval, watchdog findings, and the human review handoff.",
    alertId: DEMO_ALERT_IDS.promptInjection,
    severity: "critical",
    source: "rag-security-harness",
    icon: TriangleAlert,
  },
];

export function AlertScenarioCard({
  onRunGpuScenario,
  onRunPromptScenario,
  runningScenario,
  latestRunStatus,
  disabled = false,
  providerLabel = null
}: AlertScenarioCardProps) {
  return (
    <Card className="border-white/8 bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Agent scenarios
          </p>
          <CardTitle className="mt-3">Run a sample investigation</CardTitle>
          <CardDescription className="mt-3">
            Seed sample data explicitly before launching these synthetic scenarios.
            Each uses retrieval, local adapters, and watchdog checks, ending at human review.
          </CardDescription>
        </div>

        {latestRunStatus ? <SafetyBadge value={latestRunStatus} /> : null}
      </div>

      {providerLabel ? <p className="external-disclosure mt-4">Scenario evidence is sent to {providerLabel}.</p> : null}
      <div className="mt-5 grid gap-3">
        {scenarioCards.map((scenario) => {
          const isRunning = runningScenario === scenario.key;
          const runAction =
            scenario.key === "gpu" ? onRunGpuScenario : onRunPromptScenario;

          return (
            <div
              className="rounded-sm border border-white/8 bg-ink/60 p-4"
              key={scenario.key}
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="max-w-xl">
                  <div className="flex items-center gap-3">
                    <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accentSoft">
                      <scenario.icon className="h-4 w-4" />
                    </span>
                    <div>
                      <p className="text-sm font-medium text-white">
                        {scenario.title}
                      </p>
                      <p className="mt-1 text-sm leading-6 text-slate-300">
                        {scenario.description}
                      </p>
                    </div>
                  </div>


                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <SafetyBadge value={scenario.severity} />
                    <SafetyBadge value={scenario.source} />
                  </div>
                </div>

                <Button
                  className="min-w-44 justify-center"
                  disabled={disabled || runningScenario !== null}
                  onClick={runAction}
                  variant={scenario.key === "gpu" ? "primary" : "secondary"}
                >
                  {isRunning ? (
                    <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Siren className="mr-2 h-4 w-4" />
                  )}
                  {isRunning ? "Running scenario" : "Run scenario"}
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
