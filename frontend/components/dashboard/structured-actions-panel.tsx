import { Crosshair, ShieldCheck } from "lucide-react";

import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { recommendationLifecycle } from "@/lib/safety-status";
import type { FinalRecommendation } from "@/lib/types";

export function StructuredActionsPanel({ recommendation }: { recommendation: FinalRecommendation | null }) {
  const actions = recommendation?.proposed_actions ?? [];
  return (
    <Card className="matrix-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="console-kicker"><Crosshair className="h-3.5 w-3.5" /> STRUCTURED ACTIONS</p>
          <CardTitle className="mt-3">Proposal boundary</CardTitle>
          <CardDescription className="mt-3">
            Provider output is a candidate. Every action remains subject to application-owned evidence validation,
            tool authorization, watchdog policy, and human review.
          </CardDescription>
        </div>
        <SafetyBadge value={recommendation?.lifecycle_state ?? "no candidate"} />
      </div>
      <p className="mt-5 text-sm text-slate-300">
        {recommendation ? recommendationLifecycle(recommendation.lifecycle_state) : "No recommendation has been generated."}
      </p>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {actions.map((action) => (
          <article className="telemetry-row" key={action.action_id}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-4 w-4 text-accent" />
                <div>
                  <p className="font-mono text-sm font-semibold text-white">{action.action_type}</p>
                  <p className="mt-1 break-all font-mono text-xs text-slate-500">{action.action_id}</p>
                </div>
              </div>
              <SafetyBadge value={action.risk_level} />
            </div>
            <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
              <div><dt className="telemetry-label">TARGET</dt><dd className="mt-1 break-all text-slate-200">{action.target ?? "none"}</dd></div>
              <div><dt className="telemetry-label">APPROVAL</dt><dd className="mt-1 text-slate-200">{action.requires_approval ? "required" : "not requested"}</dd></div>
              <div className="sm:col-span-2"><dt className="telemetry-label">EVIDENCE</dt><dd className="mt-1 break-all font-mono text-xs text-slate-300">{action.supporting_evidence_ids.join(" · ") || "no references"}</dd></div>
            </dl>
            <p className="mt-4 text-sm leading-6 text-slate-300">{action.rationale}</p>
          </article>
        ))}
        {actions.length === 0 ? <p className="telemetry-row text-sm text-slate-300">No structured actions are recorded for this trace.</p> : null}
      </div>
    </Card>
  );
}
