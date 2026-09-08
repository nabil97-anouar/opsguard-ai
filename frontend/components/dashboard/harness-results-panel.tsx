import { CheckCircle2, FlaskConical, Link2, ShieldBan, TriangleAlert } from "lucide-react";

import { JsonInspector } from "@/components/dashboard/json-inspector";
import { ProvenanceLabel } from "@/components/dashboard/provenance-label";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import type { HarnessRunResponse, HarnessScenarioResponse } from "@/lib/types";

type HarnessResultsPanelProps = {
  harnessRun: HarnessRunResponse | null;
  scenarios: HarnessScenarioResponse[];
  isLoading: boolean;
};

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
            Executed cases observe input-pattern detection, trust boundaries, tool
            policies, and workflow invariants. Fixture records are examples, not
            executed tests. These deterministic cases do not measure model-level
            prompt-injection resistance.
          </CardDescription>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <SafetyBadge value={`${scenarios.length} scenarios`} />
          {harnessRun ? <SafetyBadge value={harnessRun.status} /> : null}
        </div>
      </div>

      {harnessRun ? (
        <div className="mt-5 space-y-3 text-sm text-slate-300">
          <ProvenanceLabel provenance={harnessRun.provenance} />
          <p className="break-all font-mono text-xs">Harness record group ID: {harnessRun.harness_run_id}</p>
          <p>Completed / expected scenarios: {harnessRun.completed_case_count} / {harnessRun.expected_case_count ?? "unknown"}</p>
          <p>Execution started: {harnessRun.started_at ?? "Not recorded"} · completed: {harnessRun.completed_at ?? "Not recorded"}</p>
          <p>Provider / reasoner: {harnessRun.provider_version ?? "Not recorded"} · policy / watchdog: {harnessRun.policy_version ?? "Not recorded"}</p>
        </div>
      ) : null}

      <div className="mt-8 grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-white/8 bg-ink/60 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
            Stored records
          </p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {harnessRun?.total ?? 0}
          </p>
        </div>
        <div className="rounded-2xl border border-success/20 bg-success/10 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-green-100">
            Recorded passed
          </p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {harnessRun?.passed ?? 0}
          </p>
        </div>
        <div className="rounded-2xl border border-warning/20 bg-warning/10 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-amber-100">
            Legacy partial
          </p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {harnessRun?.partial ?? 0}
          </p>
        </div>
        <div className="rounded-2xl border border-critical/20 bg-critical/10 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-red-100">
            Recorded failed
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
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <ProvenanceLabel provenance={result.provenance} />
              <SafetyBadge value={`test level: ${result.test_level ?? "unknown"}`} />
              <span className="font-mono text-xs text-slate-400">
                {result.scenario_id} · version {result.scenario_version ?? "unknown"}
              </span>
            </div>
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
                  Recorded observations
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
                  {result.failure_reason ?? "No failure reason recorded."}
                </p>
              </div>
            </div>

            <section className="mt-4 rounded-2xl border border-white/10 p-4" aria-label="Mandatory invariants">
              <p className="text-sm font-medium text-white">Mandatory invariants</p>
              {result.invariant_failures?.length ? (
                <ul className="mt-2 list-inside list-disc text-sm text-red-100">
                  {result.invariant_failures.map((failure) => <li key={failure}>Failed: {failure}</li>)}
                </ul>
              ) : null}
              {Object.keys(result.mandatory_invariants ?? {}).length ? (
                <ul className="mt-2 list-inside list-disc text-sm text-slate-300">
                  {Object.entries(result.mandatory_invariants).map(([name, passed]) => (
                    <li key={name}>{name}: {passed ? "passed" : "failed"}</li>
                  ))}
                </ul>
              ) : <p className="mt-2 text-sm text-slate-300">No observed mandatory-invariant checks recorded.</p>}
              {result.status === "partial" ? (
                <p className="mt-2 text-sm text-amber-100">Legacy partial result. Current executions use pass/fail; this is not proof that mandatory invariants passed.</p>
              ) : null}
            </section>

            {result.human_review_required !== null && result.human_review_required !== undefined ? (
              <p className="mt-4 text-sm text-slate-300">
                Human review required: {String(result.human_review_required)} · reached: {result.human_review_reached === null ? "Not observed" : String(result.human_review_reached)} · terminal status: {result.terminal_status ?? "Not recorded"}
              </p>
            ) : null}

            <div className="mt-4 grid gap-3">
              <JsonInspector
                data={{
                  scenario_id: result.scenario_id,
                  scenario_version: result.scenario_version,
                  test_level: result.test_level,
                  provenance: result.provenance,
                  harness_run_id: result.harness_run_id,
                  harness_result_id: result.harness_result_id,
                  created_at: result.created_at,
                  mandatory_invariants: result.mandatory_invariants,
                  invariant_failures: result.invariant_failures,
                  expectations: result.expectations,
                  observations: result.observations,
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
              <ul className="mt-2 space-y-1 text-xs text-slate-400">
                {scenarios.map((scenario) => <li key={scenario.scenario_id}>
                  {scenario.scenario_id} · {scenario.test_level} · version {scenario.scenario_version}
                </li>)}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
