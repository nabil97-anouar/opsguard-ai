import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { JsonInspector } from "@/components/dashboard/json-inspector";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import type { ToolAttempt } from "@/lib/types";

export function ToolAttemptsPanel({ attempts }: { attempts: ToolAttempt[] }) {
  return <Card>
    <CardTitle>Recent tool request audit</CardTitle>
    <CardDescription className="mt-3">Live requests across runs, with each run ID shown. An audited request does not prove handler execution. Invocation is recorded before handler entry, including handlers that later fail.</CardDescription>
    <div className="mt-5 space-y-4">{attempts.length === 0 ? <p className="text-sm text-slate-300">No current audit records in this view. Older tool records have unknown invocation history.</p> : attempts.map((attempt) => <article key={attempt.id} className="rounded-2xl border border-white/10 p-4">
      <p className="font-medium text-white">Requested tool: {attempt.tool_name}</p>
      <p className="mt-2 break-all font-mono text-xs text-slate-400">Call {attempt.id} · Run {attempt.agent_run_id ?? "standalone request"} · Origin {attempt.origin}</p>
      <div className="mt-3 flex flex-wrap gap-3"><SafetyBadge value={attempt.outcome} /><span className="text-sm text-slate-200">Schema validated: {attempt.validated ? "yes" : "no"}</span><span className="text-sm text-slate-200">Handler invoked: {attempt.handler_invoked ? "yes" : "no"}</span></div>
      <p className="mt-3 text-xs text-slate-400">Requested {attempt.requested_at} · Invoked {attempt.invoked_at ?? "never"} · Completed {attempt.completed_at ?? "not recorded"}</p>
      {attempt.user_error ? <p className="mt-3 text-sm text-red-100">{attempt.error_code}: {attempt.user_error}</p> : null}
      <div className="mt-3 space-y-2"><JsonInspector title="Request snapshot" data={attempt.input_snapshot} /><JsonInspector title="Authorized target" data={attempt.validated_target} /><JsonInspector title="Result snapshot" data={attempt.output_snapshot} /></div>
    </article>)}</div>
  </Card>;
}
