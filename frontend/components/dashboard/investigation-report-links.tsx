import { Download } from "lucide-react";
import { API_BASE_URL } from "@/lib/config";
import { investigationReportPath } from "@/lib/dashboard-data";
import type { InvestigationReportSelection } from "@/lib/investigation-selection";

export function InvestigationReportLinks({ selection }: { selection: InvestigationReportSelection | null }) {
  if (!selection) return null;
  const { runId, alertId, incidentTitle, status, scope } = selection;
  return <div className="investigation-report-links" aria-label="Export selected investigation">
    <span>{scope === "imported" ? "IMPORTED INCIDENT REPORT" : "SELECTED HISTORICAL REPORT"}</span>
    <strong className="min-w-0 w-full break-words text-sm text-slate-100">{incidentTitle}</strong>
    {(["md", "json"] as const).map((format) => <a key={format} href={`${API_BASE_URL}${investigationReportPath(format, runId)}`} target="_blank" rel="noreferrer"><Download size={13} />{format === "md" ? "Markdown" : "JSON"}</a>)}
    <small className="break-all">Run {runId} · Alert {alertId} · {status}</small>
  </div>;
}
