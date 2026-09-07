import { ShieldAlert } from "lucide-react";

import { JsonInspector } from "@/components/dashboard/json-inspector";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import type { FinalRecommendation } from "@/lib/types";

type WatchdogFindingsPanelProps = {
  recommendation: FinalRecommendation | null;
};

export function WatchdogFindingsPanel({
  recommendation
}: WatchdogFindingsPanelProps) {
  const findings = recommendation?.watchdog_findings ?? [];

  return (
    <Card className="border-white/8 bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Watchdog safety
          </p>
          <CardTitle className="mt-3">Policy verdict before human review</CardTitle>
          <CardDescription className="mt-3">
            Inspect policy findings and their supporting references. An allow verdict
            does not execute an action; investigations end at a manual review handoff.
          </CardDescription>
        </div>

        {recommendation?.watchdog_status ? (
          <SafetyBadge value={recommendation.watchdog_status} />
        ) : null}
      </div>

      <div className="mt-8 space-y-4">
        {recommendation?.watchdog_summary ? (
          <div className="rounded-2xl border border-accent/20 bg-accent/10 p-4">
            <p className="text-sm leading-6 text-slate-50">
              {recommendation.watchdog_summary}
            </p>
          </div>
        ) : null}

        {findings.length === 0 ? (
          <p className="rounded-2xl border border-white/8 bg-ink/60 p-4 text-sm text-slate-300">
            Run an investigation to inspect watchdog findings and
            remediation guidance.
          </p>
        ) : null}

        {findings.map((finding) => (
          <div
            className="rounded-2xl border border-white/8 bg-ink/60 p-5"
            key={finding.policy_id}
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-2xl">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-critical/20 bg-critical/10 text-red-100">
                    <ShieldAlert className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="font-medium text-white">{finding.title}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      {finding.reason}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <SafetyBadge value={finding.severity} />
                <SafetyBadge value={finding.status} />
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                  Remediation
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-200">
                  {finding.remediation}
                </p>
              </div>

              <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                  Evidence references
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {finding.evidence_refs.length > 0 ? (
                    finding.evidence_refs.map((reference) => (
                      <span
                        className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 font-mono text-xs text-slate-200"
                        key={reference}
                      >
                        {reference}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-slate-300">
                      No explicit evidence refs were attached.
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-4">
              <JsonInspector data={finding.metadata} title="Finding metadata" />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
