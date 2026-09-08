import { Lock, Wrench } from "lucide-react";

import { JsonInspector } from "@/components/dashboard/json-inspector";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import type { ToolCall } from "@/lib/types";

type ToolCallsPanelProps = {
  toolCalls: ToolCall[];
  isLoading: boolean;
};

function summarizeToolOutput(toolCall: ToolCall): string {
  if (toolCall.status === "failed" || toolCall.status === "blocked") {
    return toolCall.error_message ?? "This attempt produced no supporting observation.";
  }
  const output = toolCall.output;
  if (!output || typeof output !== "object") {
    return "Structured tool output was recorded for audit.";
  }

  const record = output as Record<string, unknown>;

  if (Array.isArray(record.matches)) {
    return `${record.matches.length} matching log entries returned.`;
  }
  if (Array.isArray(record.jobs)) {
    return `${record.jobs.length} running jobs returned.`;
  }
  if (Array.isArray(record.connections)) {
    return `${record.connections.length} network connections returned.`;
  }
  if (Array.isArray(record.results)) {
    return `${record.results.length} runbook results returned.`;
  }
  if (record.ticket_draft_id) {
    return `Ticket draft ${String(record.ticket_draft_id)} recorded; inspect its policy lifecycle.`;
  }
  if (record.node) {
    return `Node ${String(record.node)} telemetry returned.`;
  }
  if (record.status) {
    return `Tool output reported status ${String(record.status)}.`;
  }

  return "Structured tool output was recorded for audit.";
}

export function ToolCallsPanel({
  toolCalls,
  isLoading
}: ToolCallsPanelProps) {
  return (
    <Card className="border-white/8 bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Tool calls
          </p>
          <CardTitle className="mt-3">Tool observations and attempts</CardTitle>
          <CardDescription className="mt-3">
            Every tool call shows execution status, trust level, injection scan
            result, and a structured preview of the recorded output. Failed and
            blocked attempts are audit records, not supporting evidence.
          </CardDescription>
        </div>

        <SafetyBadge value={`${toolCalls.length} calls`} />
      </div>

      <div className="mt-8 space-y-4">
        {isLoading && toolCalls.length === 0 ? (
          <p className="text-sm text-slate-300">Loading tool activity…</p>
        ) : null}

        {!isLoading && toolCalls.length === 0 ? (
          <p className="rounded-2xl border border-white/8 bg-ink/60 p-4 text-sm text-slate-300">
            Tool activity will appear here after an agent scenario runs.
          </p>
        ) : null}

        {toolCalls.map((toolCall) => (
          <div
            className="rounded-2xl border border-white/8 bg-ink/60 p-5"
            key={toolCall.id}
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-2xl">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-accentSoft">
                    {toolCall.status === "blocked" ? (
                      <Lock className="h-4 w-4" />
                    ) : (
                      <Wrench className="h-4 w-4" />
                    )}
                  </span>
                  <div>
                    <p className="font-medium text-white">{toolCall.tool_name}</p>
                    <p className="mt-1 text-sm leading-6 text-slate-300">
                      {summarizeToolOutput(toolCall)}
                    </p>
                  </div>
                </div>

                <p className="mt-4 font-mono text-xs text-slate-400">
                  {new Date(toolCall.created_at).toLocaleString()} ·{" "}
                  {toolCall.duration_ms ?? 0} ms
                </p>
                <p className="mt-2 break-all font-mono text-xs text-slate-400">
                  Tool call {toolCall.id}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <SafetyBadge value={toolCall.outcome ?? toolCall.status} />
                <span className="text-xs text-slate-300">Handler invoked: {toolCall.handler_invoked === true ? "yes" : toolCall.handler_invoked === false ? "no" : "unknown (historical)"}</span>
                <SafetyBadge value={toolCall.trust_level} />
                <SafetyBadge value={toolCall.injection_scan_result} />
              </div>
            </div>

            <div className="mt-4 grid gap-3">
              <JsonInspector data={toolCall.input_args} title="Tool input" />
              <JsonInspector data={toolCall.output} title="Tool output" />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
