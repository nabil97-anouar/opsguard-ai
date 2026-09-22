import { Database } from "lucide-react";
import { Card, CardTitle } from "@/components/ui/card";
import { JsonInspector } from "./json-inspector";
import { SafetyBadge } from "./safety-badge";
import { recordedImportedEvidence } from "@/lib/dashboard-data";
import type { AgentRunDetailResponse } from "@/lib/types";

export function ImportedEvidencePanel({ run }: { run: AgentRunDetailResponse | null }) {
  const evidence = recordedImportedEvidence(run);
  return <Card>
    <div className="panel-heading"><span><Database size={14} /> IMPORTED OBSERVATIONS / RECORDED EVIDENCE</span><span>RUN SNAPSHOTS</span></div>
    <CardTitle className="mt-4">Operational observations</CardTitle>
    <p className="mt-2 text-xs leading-6 text-slate-400">Successful observations retained by this investigation. Supplied sources and event times are not independently verified. If an event time was missing, Recorded at shows when the application read the observation; it is not an inferred event time.</p>
    {evidence.length === 0 ? <p className="empty-state">{run ? "No imported observations were recorded as evidence for this run. Historical evidence stays empty; no live import or retrieval is performed here." : "Select a recorded investigation to inspect its imported observations."}</p> : <div className="imported-evidence-list">{evidence.map((item) => <article key={item.evidence_id}>
      <div className="flex flex-wrap items-start justify-between gap-3"><p className="font-medium text-sm text-white">{item.summary}</p><SafetyBadge value={item.trust_level} /></div>
      <dl className="imported-evidence-identity"><div><dt>Source</dt><dd>{item.source}</dd></div><div><dt>{item.timestamp_basis === "recorded" ? "Recorded at · event time unknown" : "Observed"}</dt><dd>{item.observed_at}</dd></div><div><dt>Evidence ID</dt><dd>{item.evidence_id}</dd></div><div><dt>Bundle ID</dt><dd>{item.bundle_id}</dd></div><div><dt>Observation ID</dt><dd>{item.observation_id}</dd></div><div><dt>Tool call ID</dt><dd>{item.tool_call_id}</dd></div><div><dt>Citation</dt><dd>{item.citation}</dd></div></dl>
      <JsonInspector title="Exact observation snapshot" data={item.content} />
    </article>)}</div>}
  </Card>;
}
