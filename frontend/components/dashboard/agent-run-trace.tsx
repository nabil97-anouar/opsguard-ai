import { recommendationLifecycle } from "@/lib/safety-status";
import {
  Bot,
  Fingerprint,
  GitBranch,
  Search,
  ShieldAlert,
  Wrench
} from "lucide-react";

import { JsonInspector } from "@/components/dashboard/json-inspector";
import { ProvenanceLabel } from "@/components/dashboard/provenance-label";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import type { AgentRunDetailResponse, AgentStep, FinalRecommendation } from "@/lib/types";

type AgentRunTraceProps = {
  agentRun: AgentRunDetailResponse | null;
  activeScenarioLabel: string | null;
  isLoading: boolean;
};

const highlightedNodes = new Set([
  "retrieve_context",
  "execute_safe_tools",
  "metacognitive_self_assessment",
  "watchdog_policy_check",
  "wait_for_human_approval"
]);

function iconForNode(nodeName: string) {
  if (nodeName === "retrieve_context") {
    return Search;
  }
  if (nodeName === "execute_safe_tools") {
    return Wrench;
  }
  if (nodeName === "metacognitive_self_assessment") {
    return Fingerprint;
  }
  if (nodeName === "watchdog_policy_check") {
    return ShieldAlert;
  }
  if (nodeName === "wait_for_human_approval") {
    return Bot;
  }
  return GitBranch;
}

function summarizeStepOutput(step: AgentStep): string {
  const output = step.output_snapshot;

  if (step.node_name === "retrieve_context") {
    const results = Array.isArray(output.results) ? output.results.length : 0;
    return `${results} chunks were returned by retrieval.`;
  }

  if (step.node_name === "execute_safe_tools") {
    const executedTools = Array.isArray(output.executed_tools)
      ? output.executed_tools.length
      : 0;
    return `${executedTools} tool results were recorded for this step.`;
  }

  if (step.node_name === "metacognitive_self_assessment") {
    if (typeof output.confidence_score === "number") {
      return `Heuristic confidence ${output.confidence_score.toFixed(2)} with ${String(
        output.uncertainty_level ?? "unknown"
      )} uncertainty.`;
    }
  }

  if (step.node_name === "watchdog_policy_check") {
    return `Watchdog returned ${String(output.watchdog_status ?? "unknown")} for the final recommendation.`;
  }

  if (step.node_name === "wait_for_human_approval") {
    return "The investigation ended at a manual review handoff. Workflow resumption is not implemented.";
  }

  if (step.node_name === "generate_recommendation") {
    return String(
      output.summary ??
        output.recommended_next_steps ??
        "A final recommendation was generated."
    );
  }

  const interestingKey = Object.keys(output).find((key) => key !== "completed_at");
  if (!interestingKey) {
    return "Structured step output recorded.";
  }

  const value = output[interestingKey];
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    return `${interestingKey}: ${value}`;
  }
  if (Array.isArray(value)) {
    return `${interestingKey}: ${value.length} item(s)`;
  }

  return `Recorded ${interestingKey.replace(/_/g, " ")}.`;
}

function humanApprovalBanner(
  recommendation: FinalRecommendation | null
) {
  if (!recommendation?.requires_human_approval) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-warning/20 bg-warning/10 p-4 text-sm leading-6 text-amber-50">
      This recommendation requires manual review outside the application.
      Approval controls and infrastructure execution are not implemented.
    </div>
  );
}

export function AgentRunTrace({
  agentRun,
  activeScenarioLabel,
  isLoading
}: AgentRunTraceProps) {
  if (isLoading && !agentRun) {
    return (
      <Card className="border-white/8 bg-white/[0.03]">
        <p className="text-sm text-slate-300">Loading the latest agent run…</p>
      </Card>
    );
  }

  if (!agentRun) {
    return (
      <Card className="border-white/8 bg-white/[0.03]">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
          Agent trace
        </p>
        <CardTitle className="mt-3">No active agent run yet</CardTitle>
        <CardDescription className="mt-3">
          Seed the sample data and launch one of the GPU or prompt-injection
          scenarios to inspect the full step-by-step workflow.
        </CardDescription>
      </Card>
    );
  }

  return (
    <Card className="border-white/8 bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Agent run trace
          </p>
          <CardTitle className="mt-3">
            {activeScenarioLabel ?? "Deterministic workflow trace"}
          </CardTitle>
          <CardDescription className="mt-3">
            Alert {agentRun.alert_id} · Run {agentRun.agent_run_id}
          </CardDescription>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <ProvenanceLabel provenance={agentRun.provenance} />
          <SafetyBadge value={agentRun.status} />
          <SafetyBadge value={agentRun.risk_level} />
          <SafetyBadge value={agentRun.approval_status} />
        </div>
      </div>

      <div className="mt-6 space-y-4">
        {agentRun.final_recommendation ? <p className="mt-4 text-sm text-slate-200">{recommendationLifecycle(agentRun.final_recommendation.lifecycle_state)}</p> : null}
        {humanApprovalBanner(agentRun.final_recommendation)}

        {agentRun.final_recommendation ? (
          <div className="rounded-2xl border border-accent/20 bg-accent/10 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-accentSoft">
              Recommendation summary
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-50">
              {agentRun.final_recommendation.summary}
            </p>
            <div className="mt-4">
              <JsonInspector data={agentRun.final_recommendation.evidence} title="Recorded supporting evidence" />
            </div>
          </div>
        ) : null}

        {agentRun.steps.map((step) => {
          const Icon = iconForNode(step.node_name);

          return (
            <div
              className={`rounded-2xl border p-5 ${
                highlightedNodes.has(step.node_name)
                  ? "border-accent/20 bg-accent/10"
                  : "border-white/8 bg-ink/60"
              }`}
              key={step.id}
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-accentSoft">
                    <Icon className="h-4 w-4" />
                  </span>

                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="font-medium text-white">
                        {step.step_index}. {step.node_name}
                      </p>
                      {highlightedNodes.has(step.node_name) ? (
                        <SafetyBadge value="highlighted node" />
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      {summarizeStepOutput(step)}
                    </p>
                    <p className="mt-2 font-mono text-xs text-slate-400">
                      {new Date(step.created_at).toLocaleString()} ·{" "}
                      {step.duration_ms ?? 0} ms
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <SafetyBadge value={step.status} />
                  {step.error ? <SafetyBadge value="error" /> : null}
                </div>
              </div>

              <div className="mt-4 grid gap-3">
                <JsonInspector data={step.input_snapshot} title="Step input" />
                <JsonInspector data={step.output_snapshot} title="Step output" />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
