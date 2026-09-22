import { recordedIncidentTitle } from "./dashboard-data";
import type { AgentRunDetailResponse } from "./types";

/** An explicit file/run/history choice takes precedence over background loads. */
export function createRunSelectionGuard() {
  let revision = 0;
  let automaticSelectionAllowed = true;
  return {
    begin() {
      automaticSelectionAllowed = false;
      return ++revision;
    },
    beginAutomatic() {
      return automaticSelectionAllowed ? ++revision : null;
    },
    isCurrent(request: number) {
      return request === revision;
    },
    commit(request: number) {
      if (request !== revision) return false;
      automaticSelectionAllowed = false;
      return true;
    },
  };
}

export function assertRunIdentity(
  detail: AgentRunDetailResponse,
  expected: { runId?: string; alertId?: string },
): void {
  if ((expected.runId && detail.agent_run_id !== expected.runId)
      || (expected.alertId && detail.alert_id !== expected.alertId)) {
    throw new Error("The returned investigation does not match the requested incident or run. No report was selected.");
  }
}

export type InvestigationReportSelection = {
  runId: string;
  alertId: string;
  incidentTitle: string;
  status: string;
  scope: "imported" | "historical";
};

export function selectedInvestigationReport(
  detail: AgentRunDetailResponse | null,
  pending: boolean,
  importedAlertId?: string,
): InvestigationReportSelection | null {
  if (pending || !detail || !detail.completed_at || detail.status === "running") return null;
  return {
    runId: detail.agent_run_id,
    alertId: detail.alert_id,
    incidentTitle: recordedIncidentTitle(detail) ?? "Incident title was not recorded",
    status: detail.status,
    scope: importedAlertId === detail.alert_id ? "imported" : "historical",
  };
}
