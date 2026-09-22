import { Cpu, Radio, ShieldCheck } from "lucide-react";
import { providerLabel } from "@/lib/incident-import";
import { Card } from "@/components/ui/card";
import type { HealthPayload, ReasoningRuntime } from "@/lib/types";

type SystemStatusCardProps = {
  health: HealthPayload | null;
  documentsCount: number | null;
  trustedDocumentsCount: number | null;
  executableToolsCount: number | null;
  blockedToolsCount: number | null;
  policiesCount: number | null;
  isLoading: boolean;
  reasoning: ReasoningRuntime | null;
};

export function SystemStatusCard({ health, documentsCount, trustedDocumentsCount, executableToolsCount,
  blockedToolsCount, policiesCount, isLoading, reasoning }: SystemStatusCardProps) {
  const deterministic = reasoning?.provider === "deterministic";
  const providerState = isLoading ? "SYNCING" : !reasoning?.available ? "Provider unavailable"
    : deterministic ? "LOCAL REASONING READY" : "CONFIGURED / INFERENCE NOT CHECKED";
  return (
    <Card className="runtime-card">
      <div className="panel-heading"><span><Cpu size={14} /> RUNTIME / PROVIDER</span><span className={health ? "text-accent" : "text-amber-300"}>{isLoading ? "SYNCING" : health ? "API ONLINE" : "API UNAVAILABLE"}</span></div>
      <div className="runtime-provider">
        <div className="runtime-provider-icon"><Radio size={26} /></div>
        <div className="min-w-0"><p className="telemetry-label">SELECTED REASONING ENGINE</p><div className="mt-2"><span className="provider-name">{providerLabel(reasoning?.provider)}</span></div><p className="mt-2 break-all font-mono text-sm text-white">{reasoning?.model ?? "No runtime response"}</p></div>
      </div>
      <p className={`runtime-state ${reasoning?.available ? "" : "runtime-state-warning"}`}>{providerState}</p>
      <p className="mt-3 text-xs leading-5 text-slate-400">{!reasoning ? "Provider configuration is unavailable until the backend responds." : !reasoning.available ? "The selected provider is not ready. Check the backend configuration and the reason below." : deterministic ? "Deterministic local reasoning. No model-service request is made in this mode." : "Configuration is loaded. A successful investigation verifies inference; credentials alone do not."}</p>
      {reasoning?.reason ? <p className="mt-3 text-xs leading-5 text-amber-200">{reasoning.reason}</p> : null}
      <dl className="runtime-facts">
        <div><dt>Documents / trusted</dt><dd>{documentsCount === null ? "Unavailable" : `${documentsCount} / ${trustedDocumentsCount ?? "?"}`}</dd></div>
        <div><dt>Executable adapters</dt><dd>{executableToolsCount ?? "Unavailable"}</dd></div>
        <div><dt>Blocked definitions</dt><dd>{blockedToolsCount ?? "Unavailable"}</dd></div>
        <div><dt>Watchdog policies</dt><dd>{policiesCount ?? "Unavailable"}</dd></div>
      </dl>
      <details className="provider-details"><summary>Provider configuration details</summary><div>
        <p>Provider and model are selected in the backend environment. Credentials never belong in this interface.</p>
        {reasoning?.response_format ? <p className="mt-2">Response format: <code>{reasoning.response_format}</code></p> : null}
        {reasoning?.model_options?.length ? <><p className="mt-3">Configured chat-model options (service availability unverified):</p><ul className="mt-2 space-y-1">{reasoning.model_options.map((model) => <li className="break-all" key={model.id}>{model.id}</li>)}</ul></> : null}
      </div></details>
      <p className="runtime-boundary"><ShieldCheck size={13} /> APPLICATION-OWNED TOOL &amp; POLICY BOUNDARIES</p>
    </Card>
  );
}
