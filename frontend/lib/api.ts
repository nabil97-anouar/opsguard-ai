import { API_BASE_URL } from "@/lib/config";
import type {
  AgentRunDetailResponse,
  IncidentBundle,
  IncidentImportResponse,
  AgentRunListResponse,
  AgentRunResponse,
  BackendErrorPayload,
  DemoSeedResponse,
  DocumentListItem,
  EvaluationRunResponse,
  EvaluationSummaryResponse,
  HarnessResultListResponse,
  HarnessRunResponse,
  HarnessScenarioListResponse,
  HealthPayload,
  ReasoningRuntime,
  ToolListResponse,
  WatchdogPoliciesResponse
} from "@/lib/types";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export class ApiClientError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...init } = options;
  const requestHeaders = new Headers(headers);
  requestHeaders.set("Accept", "application/json");

  const requestInit: RequestInit = {
    ...init,
    headers: requestHeaders,
    cache: "no-store"
  };

  if (body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
    requestInit.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, requestInit);
  const hasJsonBody = response.headers.get("content-type")?.includes("application/json");
  const payload = hasJsonBody ? ((await response.json()) as unknown) : null;

  if (!response.ok) {
    const detail = apiErrorDetail(payload, response.status);
    throw new ApiClientError(response.status, detail);
  }

  return payload as T;
}

// Pydantic error input/context/msg can echo uploaded data. Show only bounded,
// recognized field paths and fixed descriptions; never serialize error objects.
export function apiErrorDetail(payload: unknown, status: number): string {
  const detail = typeof payload === "object" && payload !== null && "detail" in payload
    ? (payload as BackendErrorPayload).detail : undefined;
  if (typeof detail === "string") return detail.slice(0, 500);
  if (Array.isArray(detail)) {
    const fields = new Set(["body", "incident", "observations", "schema_version", "title", "description", "severity", "source", "observed_at", "infrastructure_type", "node", "job_id", "user", "kind", "message", "name", "value", "unit", "command", "status", "remote_ip", "remote_port", "process"]);
    const errors = detail.slice(0, 6).map((error) => {
      if (typeof error !== "object" || error === null) return "bundle: invalid value";
      const path = Array.isArray(error.loc) ? error.loc.slice(0, 8).filter((part) => part !== "body").map((part) =>
        typeof part === "number" && Number.isSafeInteger(part) ? String(part) : typeof part === "string" && fields.has(part) ? part : "field").join(".") : "bundle";
      const explanations: Record<string, string> = {
        missing: "required field missing", extra_forbidden: "field not accepted",
        string_type: "must be text", string_too_long: "text exceeds the allowed length",
        string_too_short: "text is too short", literal_error: "unsupported value",
        datetime_parsing: "use an ISO 8601 timestamp with a timezone", datetime_from_date_parsing: "use an ISO 8601 timestamp with a timezone",
        timezone_aware: "timestamp must include a timezone", int_parsing: "must be an integer",
        float_parsing: "must be a number", finite_number: "must be a finite number",
        too_long: "too many items or too much content", value_error: "value does not meet the incident schema",
      };
      const message = error.type && Object.prototype.hasOwnProperty.call(explanations, error.type) ? explanations[error.type] : "invalid value";
      return `${path || "bundle"}: ${message}`;
    });
    return `Request validation failed. ${errors.join("; ")}${detail.length > 6 ? "; additional fields need correction" : ""}.`;
  }
  return `Request failed with status ${status}.`;
}

export async function importIncidentBundle(bundle: IncidentBundle): Promise<IncidentImportResponse> {
  return request<IncidentImportResponse>("/incidents/import", { method: "POST", body: bundle });
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.detail;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong while contacting the backend.";
}

export async function getBackendHealth(): Promise<HealthPayload> {
  return request<HealthPayload>("/health");
}

export async function getReasoningRuntime(): Promise<ReasoningRuntime> {
  return request<ReasoningRuntime>("/runtime/reasoning");
}

export async function seedDemoData(reset = false): Promise<DemoSeedResponse> {
  return request<DemoSeedResponse>("/demo/seed", {
    method: "POST",
    body: { reset }
  });
}

export async function listDocuments(): Promise<DocumentListItem[]> {
  return request<DocumentListItem[]>("/documents");
}

export async function listTools(): Promise<ToolListResponse> {
  return request<ToolListResponse>("/tools");
}

export async function runAgent(alertId: string): Promise<AgentRunResponse> {
  return request<AgentRunResponse>("/agent/runs", {
    method: "POST",
    body: { alert_id: alertId }
  });
}

export async function getAgentRunDetail(
  agentRunId: string
): Promise<AgentRunDetailResponse> {
  return request<AgentRunDetailResponse>(`/agent/runs/${agentRunId}`);
}

export async function listAgentRuns(): Promise<AgentRunListResponse> {
  return request<AgentRunListResponse>("/agent/runs");
}

export async function listWatchdogPolicies(): Promise<WatchdogPoliciesResponse> {
  return request<WatchdogPoliciesResponse>("/watchdog/policies");
}

export async function listHarnessScenarios(): Promise<HarnessScenarioListResponse> {
  return request<HarnessScenarioListResponse>("/harness/scenarios");
}

export async function runSecurityHarness(
  scenarioIds: string[] | null = null,
  resetDemoData = false
): Promise<HarnessRunResponse> {
  return request<HarnessRunResponse>("/harness/run", {
    method: "POST",
    body: {
      scenario_ids: scenarioIds,
      reset_demo_data: resetDemoData
    }
  });
}

export async function listHarnessResults(): Promise<HarnessResultListResponse> {
  return request<HarnessResultListResponse>("/harness/results");
}

export async function getHarnessRunResults(
  harnessRunId: string
): Promise<HarnessRunResponse> {
  return request<HarnessRunResponse>(`/harness/results/${harnessRunId}`);
}

export async function getEvaluationSummary(): Promise<EvaluationSummaryResponse> {
  return request<EvaluationSummaryResponse>("/evaluation/summary");
}

export async function runEvaluation(
  runHarnessIfEmpty = true,
  reportType = "full",
  harnessRunId: string | null = null
): Promise<EvaluationRunResponse> {
  return request<EvaluationRunResponse>("/evaluation/run", {
    method: "POST",
    body: {
      run_harness_if_empty: runHarnessIfEmpty,
      report_type: reportType,
      harness_run_id: harnessRunId
    }
  });
}


export function listToolAttempts(): Promise<{ items: import("./types").ToolAttempt[] }> {
  return request("/tools/attempts");
}
