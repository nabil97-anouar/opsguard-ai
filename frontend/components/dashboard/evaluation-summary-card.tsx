import { BarChart3, FileJson, FileText, LoaderCircle } from "lucide-react";

import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { API_BASE_URL } from "@/lib/config";
import type { EvaluationSummaryResponse } from "@/lib/types";

type EvaluationSummaryCardProps = {
  summary: EvaluationSummaryResponse | null;
  isLoading: boolean;
  isRunningEvaluation: boolean;
  onRunEvaluation: () => Promise<void> | void;
};

function scoreTone(value: number): string {
  if (value >= 85) {
    return "passed";
  }
  if (value >= 65) {
    return "allow_with_warnings";
  }
  return "require_human_approval";
}

function scoreLabel(value: number): string {
  return `${value.toFixed(1)} score`;
}

export function EvaluationSummaryCard({
  summary,
  isLoading,
  isRunningEvaluation,
  onRunEvaluation,
}: EvaluationSummaryCardProps) {
  const metrics = summary?.scorecard ?? null;
  const harness = summary?.harness_performance ?? null;

  return (
    <Card className="border-white/8 bg-white/[0.03]" id="evaluation">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Evaluation and reports
          </p>
          <CardTitle className="mt-3">Safety scorecard and export-ready reports</CardTitle>
          <CardDescription className="mt-3 max-w-3xl">
            This layer rolls up harness outcomes, watchdog findings, tool-safety posture,
            grounding quality, and human-approval enforcement into a deterministic local
            scorecard for demos, screenshots, and portfolio walkthroughs.
          </CardDescription>
        </div>

        <SafetyBadge
          value={
            summary
              ? `overall ${summary.scorecard.overall_score.toFixed(1)}`
              : "evaluation ready"
          }
        />
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {metrics ? (
          [
            ["Overall", metrics.overall_score],
            ["Safety", metrics.safety_score],
            ["Grounding", metrics.grounding_score],
            ["Tool safety", metrics.tool_safety_score],
            ["Watchdog", metrics.watchdog_score],
          ].map(([label, value]) => (
            <div
              className="rounded-2xl border border-white/8 bg-ink/60 p-4"
              key={label}
            >
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">{label}</p>
              <p className="mt-3 text-3xl font-semibold text-white">
                {(value as number).toFixed(1)}
              </p>
              <div className="mt-3">
                <SafetyBadge value={scoreTone(value as number)} className="text-[10px]" />
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-white/8 bg-ink/60 p-5 md:col-span-2 xl:col-span-5">
            <p className="text-sm leading-6 text-slate-300">
              {isLoading
                ? "Loading the latest evaluation summary from the local backend…"
                : "Run the evaluation once the demo data or harness results are in place to generate the portfolio scorecard."}
            </p>
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-2xl border border-white/8 bg-ink/60 p-5">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accentSoft">
              <BarChart3 className="h-4 w-4" />
            </span>
            <div>
              <p className="font-medium text-white">Executive summary</p>
              <p className="mt-1 text-sm leading-6 text-slate-300">
                {summary?.executive_summary ??
                  "No persisted evaluation yet. The backend can still calculate a non-persisted summary on demand."}
              </p>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            {metrics ? (
              <>
                <SafetyBadge value={scoreLabel(metrics.overall_score)} />
                <SafetyBadge
                  value={`${summary?.human_approval_enforcement.runs_requiring_human_approval ?? 0} human approvals`}
                />
                <SafetyBadge
                  value={`${summary?.tool_safety.blocked_tool_calls ?? 0} blocked tool calls`}
                />
                <SafetyBadge
                  value={`${summary?.grounding_evidence.runs_with_citations ?? 0} cited runs`}
                />
              </>
            ) : (
              <SafetyBadge value="deterministic local evaluation" />
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-white/8 bg-ink/60 p-5">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
            Report exports
          </p>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Export the current backend state as Markdown or JSON. These endpoints stay
            local and deterministic, so the report is safe to demo without external services.
          </p>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <Button
              className="justify-center"
              disabled={isRunningEvaluation}
              onClick={onRunEvaluation}
              variant="secondary"
            >
              {isRunningEvaluation ? (
                <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <BarChart3 className="mr-2 h-4 w-4" />
              )}
              Run evaluation
            </Button>

            <a
              className={buttonVariants({ variant: "ghost" })}
              href={`${API_BASE_URL}/evaluation/report.md`}
              rel="noreferrer"
              target="_blank"
            >
              <FileText className="mr-2 h-4 w-4" />
              Markdown report
            </a>

            <a
              className={buttonVariants({ variant: "ghost" })}
              href={`${API_BASE_URL}/evaluation/report.json`}
              rel="noreferrer"
              target="_blank"
            >
              <FileJson className="mr-2 h-4 w-4" />
              JSON report
            </a>
          </div>

          <div className="mt-5 text-sm leading-6 text-slate-300">
            {harness ? (
              <p>
                Latest harness summary: {harness.passed} passed, {harness.partial} partial,{" "}
                {harness.failed} failed across {harness.total_scenarios} scenarios.
              </p>
            ) : (
              <p>
                The evaluation layer can bootstrap itself by running the harness if no
                scenario results exist yet.
              </p>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
