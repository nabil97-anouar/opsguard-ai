import { API_BASE_URL } from "@/lib/config";

export type HealthPayload = {
  status: string;
  version: string;
  environment: string;
  dependencies: {
    postgres: string;
    qdrant: string;
    llm_provider: string;
  };
  timestamp: string;
};

export async function getBackendHealth(): Promise<HealthPayload> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    headers: { Accept: "application/json" },
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Backend health check failed.");
  }

  return (await response.json()) as HealthPayload;
}
