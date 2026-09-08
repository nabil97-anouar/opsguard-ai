import { API_BASE_URL } from "@/lib/config";
import type {
  AgentRunDetailResponse,
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
  RagRetrieveRequest,
  RagRetrieveResponse,
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
    const detail =
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof (payload as BackendErrorPayload).detail === "string"
        ? ((payload as BackendErrorPayload).detail ?? `Request failed with status ${response.status}.`)
        : `Request failed with status ${response.status}.`;
    throw new ApiClientError(response.status, detail);
  }

  return payload as T;
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

export async function seedDemoData(reset = false): Promise<DemoSeedResponse> {
  return request<DemoSeedResponse>("/demo/seed", {
    method: "POST",
    body: { reset }
  });
}

export async function listDocuments(): Promise<DocumentListItem[]> {
  return request<DocumentListItem[]>("/documents");
}

export async function retrieveRagChunks(
  payload: RagRetrieveRequest
): Promise<RagRetrieveResponse> {
  return request<RagRetrieveResponse>("/rag/retrieve", {
    method: "POST",
    body: payload
  });
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
