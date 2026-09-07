import { CheckCircle2, FlaskConical, Link2, ShieldBan, TriangleAlert } from "lucide-react";

import { JsonInspector } from "@/components/dashboard/json-inspector";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import type { HarnessRunResponse, HarnessScenarioResponse } from "@/lib/types";

type HarnessResultsPanelProps = {
  harnessRun: HarnessRunResponse | null;
  scenarios: HarnessScenarioResponse[];
  isLoading: boolean;
};

function scoreLabel(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function HarnessResultsPanel({
  harnessRun,
  scenarios,
  isLoading
}: HarnessResultsPanelProps) {
  return (
    <Card className="border-white/8 bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Security harness
          </p>
          <CardTitle className="mt-3">Adversarial regression scenarios</CardTitle>
          <CardDescription className="mt-3">
            The harness checks prompt injection, malicious tool feedback,
            blocked tool requests, and citation gaps in selected components and workflows.
            Results describe these cases, not general model security.
          </CardDescription>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <SafetyBadge value={`${scenarios.length} scenarios`} />
          {harnessRun ? <SafetyBadge value={harnessRun.status} /> : null}
        </div>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-white/8 bg-ink/60 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
            Total
          </p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {harnessRun?.total ?? scenarios.length}
          </p>
        </div>
        <div className="rounded-2xl border border-success/20 bg-success/10 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-green-100">
            Passed
          </p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {harnessRun?.passed ?? 0}
          </p>
        </div>
        <div className="rounded-2xl border border-warning/20 bg-warning/10 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-amber-100">
            Partial
          </p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {harnessRun?.partial ?? 0}
          </p>
        </div>
        <div className="rounded-2xl border border-critical/20 bg-critical/10 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-red-100">
            Failed
          </p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {harnessRun?.failed ?? 0}
          </p>
        </div>
      </div>

      <div className="mt-8 space-y-4">
        {isLoading && !harnessRun ? (
          <p className="text-sm text-slate-300">Loading harness evidence…</p>
        ) : null}

        {!isLoading && !harnessRun ? (
          <p className="rounded-2xl border border-white/8 bg-ink/60 p-4 text-sm text-slate-300">
            Run the security harness to record scenario results in the
            dashboard.
          </p>
        ) : null}

        {harnessRun?.results.map((result) => (
          <div
            className="rounded-2xl border border-white/8 bg-ink/60 p-5"
            key={result.harness_result_id ?? result.scenario_id}
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-3xl">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-accentSoft">
                    {result.status === "passed" ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : result.status === "partial" ? (
                      <TriangleAlert className="h-4 w-4" />
                    ) : (
                      <ShieldBan className="h-4 w-4" />
                    )}
                  </span>
                  <div>
                    <p className="font-medium text-white">{result.name}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      {result.observed_behavior}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <SafetyBadge value={result.status} />
                {result.watchdog_status ? (
                  <SafetyBadge value={result.watchdog_status} />
                ) : null}
                <SafetyBadge value={scoreLabel(result.score)} />
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                  Expected behavior
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-200">
                  {result.expected_behavior}
                </p>
              </div>

              <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                  Safety evidence
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-200">
                  {result.safety_events.length} linked safety events ·{" "}
                  {result.findings.length} findings
                </p>
                {result.agent_run_id ? (
                  <p className="mt-2 flex items-center gap-2 font-mono text-xs text-slate-400">
                    <Link2 className="h-3.5 w-3.5" />
                    {result.agent_run_id}
                  </p>
                ) : null}
              </div>

              <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                  Failure reason
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-200">
                  {result.failure_reason ?? "No failure reason. Scenario met its expected bar."}
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-3">
              <JsonInspector
                data={{
                  scenario_id: result.scenario_id,
                  safety_events: result.safety_events,
                  findings: result.findings,
                  metadata: result.metadata
                }}
                title="Scenario details"
              />
            </div>
          </div>
        ))}

        <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accentSoft">
              <FlaskConical className="h-4 w-4" />
            </span>
            <div>
              <p className="font-medium text-white">Scenario registry</p>
              <p className="mt-1 text-sm leading-6 text-slate-300">
                {scenarios.length} deterministic harness scenarios are available
                for replay against the local stack.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
