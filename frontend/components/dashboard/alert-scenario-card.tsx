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
};

const scenarioCards = [
  {
    key: "gpu" as const,
    title: "GPU abuse investigation",
    description:
      "Runs the deterministic agent workflow against the seeded xmrig / mining-pool alert.",
    alertId: DEMO_ALERT_IDS.gpuAbuse,
    severity: "critical",
    source: "slurm-monitor",
    icon: Bot,
  },
  {
    key: "prompt" as const,
    title: "Prompt-injection poisoning",
    description:
      "Exercises the poisoned runbook path, watchdog blocking, and human approval handoff.",
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
  latestRunStatus
}: AlertScenarioCardProps) {
  return (
    <Card className="border-white/8 bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Agent scenarios
          </p>
          <CardTitle className="mt-3">Launch premium demo paths</CardTitle>
          <CardDescription className="mt-3">
            Each scenario uses stable seeded IDs, grounded retrieval, safe tools,
            and watchdog policy checks before the run enters human review.
          </CardDescription>
        </div>

        {latestRunStatus ? <SafetyBadge value={latestRunStatus} /> : null}
      </div>

      <div className="mt-8 grid gap-4">
        {scenarioCards.map((scenario) => {
          const isRunning = runningScenario === scenario.key;
          const runAction =
            scenario.key === "gpu" ? onRunGpuScenario : onRunPromptScenario;

          return (
            <div
              className="rounded-2xl border border-white/8 bg-ink/60 p-5"
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

                  <p className="mt-4 font-mono text-xs text-slate-400">
                    Alert ID: {scenario.alertId}
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <SafetyBadge value={scenario.severity} />
                    <SafetyBadge value={scenario.source} />
                  </div>
                </div>

                <Button
                  className="min-w-44 justify-center"
                  disabled={runningScenario !== null}
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
