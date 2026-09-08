import { BarChart3, FileJson, FileText, LoaderCircle } from "lucide-react";

import { JsonInspector } from "@/components/dashboard/json-inspector";
import { ProvenanceLabel } from "@/components/dashboard/provenance-label";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { API_BASE_URL } from "@/lib/config";
import { evaluationReportPath } from "@/lib/dashboard-data";
import type { EvaluationMetric, EvaluationSummaryResponse } from "@/lib/types";

type EvaluationSummaryCardProps = {
  summary: EvaluationSummaryResponse | null;
  isLoading: boolean;
  isRunningEvaluation: boolean;
  onRunEvaluation: () => Promise<void> | void;
};

function metricValue(metric: EvaluationMetric): string {
  return metric.denominator === 0 || metric.value === null
    ? "N/A — no applicable observations"
    : `${metric.value} (${(metric.value * 100).toFixed(1)}%)`;
}

export function EvaluationSummaryCard({
  summary,
  isLoading,
  isRunningEvaluation,
  onRunEvaluation,
}: EvaluationSummaryCardProps) {
  const cohort = summary?.cohort;
  const storedId = summary?.report_kind === "stored" ? summary.evaluation_run_id : null;
  const levelCounts = cohort?.scenario_manifest.reduce<Record<string, number>>((counts, scenario) => {
    counts[scenario.test_level] = (counts[scenario.test_level] ?? 0) + 1;
    return counts;
  }, {}) ?? {};

  return (
    <Card className="border-white/8 bg-white/[0.03]" id="evaluation">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Evaluation and reports</p>
      <CardTitle className="mt-3">Evaluation of an explicit execution cohort</CardTitle>
      <CardDescription className="mt-3 max-w-3xl">
        Each stored report records one harness execution and its linked observations.
        Fixture records cannot establish execution. Counts describe the recorded
        cases; no overall AI safety score is calculated.
      </CardDescription>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Button disabled={isRunningEvaluation} onClick={onRunEvaluation} variant="secondary">
          {isRunningEvaluation ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <BarChart3 className="mr-2 h-4 w-4" />}
          Run evaluation
        </Button>
        {storedId ? (
          <>
            <a className={buttonVariants({ variant: "ghost" })} href={`${API_BASE_URL}${evaluationReportPath("md", storedId)}`} rel="noreferrer" target="_blank">
              <FileText className="mr-2 h-4 w-4" />Markdown report
            </a>
            <a className={buttonVariants({ variant: "ghost" })} href={`${API_BASE_URL}${evaluationReportPath("json", storedId)}`} rel="noreferrer" target="_blank">
              <FileJson className="mr-2 h-4 w-4" />JSON report
            </a>
          </>
        ) : null}
      </div>

      {summary && cohort ? (
        <>
          <section className="mt-6 rounded-2xl border border-white/10 bg-ink/60 p-5" aria-label="Evaluation context">
            <div className="flex flex-wrap items-center gap-3">
              <p className="font-medium text-white">{storedId ? "Stored evaluation report" : "Live preview — no stored evaluation"}</p>
              {cohort.provenance === "executed" ? <ProvenanceLabel provenance="executed" /> : <span className="text-sm text-slate-300">No executed cohort</span>}
            </div>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              {[
                ["Evaluation ID", summary.evaluation_run_id ?? "Not persisted"],
                ["Harness execution ID", cohort.harness_run_id ?? "None"],
                ["Execution started", cohort.execution_started_at ?? "Not executed"],
                ["Execution completed", cohort.execution_completed_at ?? "Not executed"],
                ["Completed / expected scenarios", `${cohort.completed_case_count} / ${cohort.expected_case_count}`],
                ["Report generated", summary.generated_at],
                ["Provider / reasoner version", cohort.provider_version ?? "Not recorded"],
                ["Policy / watchdog version", cohort.policy_version ?? "Not recorded"],
                ["Metric definitions version", summary.schema_version],
                ["Scenario / test-level breakdown", Object.entries(levelCounts).map(([level, count]) => `${level}: ${count}`).join(" · ") || "No scenarios"],
              ].map(([label, value]) => <div key={label}><dt className="text-slate-400">{label}</dt><dd className="mt-1 break-all text-slate-100">{value}</dd></div>)}
            </dl>
            <p className="mt-4 text-sm text-slate-300">
              {storedId ? "Exports are pinned to this evaluation ID. Unrelated later activity does not update this stored report." : "Run evaluation to store a report. If only fixture results exist, an actual harness execution is required."}
            </p>
            <div className="mt-4"><JsonInspector title="Exact cohort and scenario versions" data={cohort} /></div>
          </section>

          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-left text-sm" aria-label="Evaluation metric counts">
              <thead className="border-b border-white/20 text-slate-400"><tr>
                <th className="p-3">Metric / definition</th><th className="p-3">Numerator</th><th className="p-3">Denominator</th><th className="p-3">Value</th>
              </tr></thead>
              <tbody>
                {Object.entries(summary.metrics).map(([name, metric]) => <tr className="border-b border-white/10 align-top" key={name}>
                  <th scope="row" className="p-3 font-normal"><p className="font-mono text-slate-100">{name}</p><p className="mt-2 max-w-xl text-slate-300">{metric.definition}</p></th>
                  <td className="p-3 text-slate-100">{metric.numerator}</td><td className="p-3 text-slate-100">{metric.denominator}</td><td className="p-3 text-slate-100">{metricValue(metric)}</td>
                </tr>)}
              </tbody>
            </table>
          </div>
          <section className="mt-6 grid gap-4 sm:grid-cols-2" aria-label="Evaluation failures">
            <div className="rounded-2xl border border-white/10 p-4"><p className="font-medium text-white">Failed scenarios</p>
              {summary.failed_scenarios.length ? <ul className="mt-3 list-inside list-disc text-sm text-red-100">{summary.failed_scenarios.map((id) => <li key={id}>{id}</li>)}</ul> : <p className="mt-3 text-sm text-slate-300">No failures recorded in this cohort.</p>}
            </div>
            <div className="rounded-2xl border border-white/10 p-4"><p className="font-medium text-white">Mandatory invariant failures</p>
              {summary.mandatory_invariant_failures.length ? <ul className="mt-3 list-inside list-disc text-sm text-red-100">{summary.mandatory_invariant_failures.map((failure) => <li key={`${failure.scenario_id}:${failure.invariant}`}>{failure.scenario_id}: {failure.invariant}</li>)}</ul> : <p className="mt-3 text-sm text-slate-300">No mandatory invariant failures recorded in this cohort.</p>}
            </div>
          </section>
          <section className="mt-6 rounded-2xl border border-white/10 p-5" aria-label="Evaluation limitations">
            <p className="font-medium text-white">Limitations</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">Human-review rates describe the terminal waiting_for_human workflow, not escalation accuracy or approval usefulness. Adversarial cases measure application-level invariants under fixture inputs, not model-level prompt-injection resistance.</p>
            <ul className="mt-3 list-inside list-disc space-y-2 text-sm text-slate-300">{summary.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
          </section>
        </>
      ) : <p className="mt-6 rounded-2xl border border-white/10 p-5 text-sm text-slate-300">{isLoading ? "Loading the stored evaluation report…" : "No evaluation report is available. Run evaluation to execute or select a harness cohort and record its metrics."}</p>}
    </Card>
  );
}
