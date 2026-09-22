import type { AgentRunDetailResponse, IncidentBundle, IncidentImportResponse, ReasoningRuntime } from "./types";
import { getAgentRunDetail, importIncidentBundle, runAgent } from "./api";
import { assertRunIdentity } from "./investigation-selection";

export const MAX_INCIDENT_BYTES = 1024 * 1024;
export const MAX_INCIDENT_OBSERVATIONS = 32;

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Only structural checks here. The backend owns field, target and trust validation. */
export function parseIncidentJson(text: string): IncidentBundle {
  if (new TextEncoder().encode(text).byteLength > MAX_INCIDENT_BYTES) {
    throw new Error("The incident file exceeds 1 MiB. Export a smaller incident bundle.");
  }
  let value: unknown;
  try { value = JSON.parse(text); } catch { throw new Error("The file is not valid JSON. Download an example to check the incident-bundle format."); }
  if (!record(value) || value.schema_version !== "incident-bundle-v1" || !record(value.incident)) {
    throw new Error("Expected schema_version incident-bundle-v1 and an incident object. Download an example for the required format.");
  }
  for (const field of ["title", "description", "source", "severity"]) {
    if (typeof value.incident[field] !== "string" || !(value.incident[field] as string).trim()) {
      throw new Error(`incident.${field} must be a non-empty string.`);
    }
  }
  if (value.incident.observed_at != null && (typeof value.incident.observed_at !== "string" || !value.incident.observed_at.trim())) {
    throw new Error("incident.observed_at must be a timestamp string or null when unknown.");
  }
  if (!Array.isArray(value.observations) || value.observations.length > MAX_INCIDENT_OBSERVATIONS) {
    throw new Error("observations must be an array of at most 32 log, metric, job, or network observations.");
  }
  for (let index = 0; index < value.observations.length; index += 1) {
    const item: unknown = value.observations[index];
    if (!record(item) || !["log", "metric", "job", "network"].some((kind) => kind === item.kind)) {
      throw new Error(`observations.${index}.kind must be log, metric, job, or network.`);
    }
  }
  return value as IncidentBundle;
}

/** Importing is deliberately separate from running a model; never seed here. */
export async function importPreparedIncident(bundle: IncidentBundle): Promise<IncidentImportResponse> {
  return importIncidentBundle(bundle);
}

export async function investigateImportedIncident(receipt: IncidentImportResponse): Promise<AgentRunDetailResponse> {
  const run = await runAgent(receipt.alert_id);
  const detail = await getAgentRunDetail(run.agent_run_id);
  assertRunIdentity(detail, { runId: run.agent_run_id, alertId: receipt.alert_id });
  return detail;
}

export function incidentDataDestination(runtime: ReasoningRuntime | null): string {
  if (!runtime) return "The reasoning provider is unavailable. Import stores the bundle in this backend; investigation remains disabled until provider configuration is available.";
  if (runtime.provider === "deterministic") return "Investigation uses deterministic local reasoning. No model-service request is made.";
  if (runtime.provider === "ollama" && runtime.mode === "local") {
    return `Running sends incident evidence to Ollama / ${runtime.model} at the backend's configured local endpoint. A local server does not establish that inference stays offline. Review the file for sensitive data before running.`;
  }
  return `Running sends incident evidence to ${providerLabel(runtime.provider)} / ${runtime.model}. Redact secrets and use only data you are permitted to send to that service. Import alone does not call the model.`;
}

export function providerLabel(provider: string | null | undefined): string {
  switch (provider) {
    case "deterministic": return "Deterministic";
    case "openai": return "OpenAI";
    case "institutional": return "Compatible API";
    case "anthropic": return "Claude / Anthropic";
    case "ollama": return "Ollama";
    default: return "Unavailable";
  }
}
