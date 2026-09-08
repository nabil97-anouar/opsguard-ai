import type { AgentRunDetailResponse, EvidenceItem, HarnessRunResponse, RetrievalChunk, ToolListItem } from "./types";

export function executionProvenanceLabel(provenance: string | null | undefined): string {
  if (provenance === "executed") return "Executed";
  if (provenance === "fixture") return "Fixture / example — not executed";
  return "Legacy / unknown provenance — execution unverified";
}

export function executedHarnessRunId(run: HarnessRunResponse | null): string | null {
  return run && run.status === "completed" && run.provenance === "executed" && run.results.length > 0 && run.results.every((result) => result.provenance === "executed")
    ? run.harness_run_id : null;
}

export function harnessExecutionCounts(run: HarnessRunResponse | null): string {
  if (!executedHarnessRunId(run) || !run || run.total === 0) return "Not executed";
  return `${run.passed} / ${run.total}`;
}

export function evaluationReportPath(format: "md" | "json", evaluationRunId: string): string {
  return `/evaluation/report.${format}?evaluation_run_id=${encodeURIComponent(evaluationRunId)}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isStoredChunk(value: unknown): value is RetrievalChunk {
  if (!isRecord(value)) return false;
  return ["document_id", "chunk_id", "title", "source", "doc_type", "content_excerpt", "citation", "risk_level"]
    .every((key) => typeof value[key] === "string") &&
    ["trusted", "untrusted", "quarantined"].some((trust) => value.trust_level === trust) &&
    typeof value.score === "number" && Number.isFinite(value.score) &&
    typeof value.chunk_index === "number" &&
    typeof value.is_suspicious === "boolean" &&
    Array.isArray(value.matched_patterns) && value.matched_patterns.every((pattern) => typeof pattern === "string");
}

function isDocumentEvidence(value: EvidenceItem | Record<string, unknown>): value is EvidenceItem & { document_id: string; chunk_id: string; retrieval_score: number; content: string } {
  return value.kind === "retrieval" && value.source_type === "document" &&
    typeof value.evidence_id === "string" && typeof value.document_id === "string" &&
    typeof value.chunk_id === "string" && typeof value.source === "string" &&
    typeof value.retrieval_score === "number" && Number.isFinite(value.retrieval_score) &&
    typeof value.content === "string" && typeof value.observed_at === "string" &&
    typeof value.citation === "string" &&
    ["trusted", "untrusted", "quarantined"].some((trust) => value.trust_level === trust);
}

/** Read snapshots only. Document catalog changes never populate historical evidence. */
export function recordedRetrievalChunks(run: AgentRunDetailResponse | null): RetrievalChunk[] {
  if (!run) return [];
  const evidence = run.final_recommendation?.evidence;
  if (evidence && (evidence.length === 0 || evidence.some((item) => "source_type" in item))) {
    return evidence.filter(isDocumentEvidence).map((item) => ({
      evidence_id: item.evidence_id,
      observed_at: item.observed_at,
      document_id: item.document_id,
      chunk_id: item.chunk_id,
      title: item.title ?? item.source,
      source: item.source,
      chunk_index: item.chunk_index ?? 0,
      trust_level: item.trust_level,
      doc_type: item.doc_type ?? "unknown",
      score: item.retrieval_score,
      content_excerpt: item.content,
      citation: item.citation,
      is_suspicious: item.suspicious,
      matched_patterns: item.matched_patterns ?? [],
      risk_level: item.risk_level ?? "unknown"
    }));
  }

  // Legacy runs can still display their own persisted retrieval step, never live data.
  const results = run.steps.find((step) => step.node_name === "retrieve_context")?.output_snapshot.results;
  return Array.isArray(results) ? results.filter(isStoredChunk).map((item) => ({ ...item })) : [];
}

export async function loadRecordedAgentRun(
  runId: string,
  getRunDetail: (id: string) => Promise<AgentRunDetailResponse>
): Promise<{ detail: AgentRunDetailResponse; chunks: RetrievalChunk[] }> {
  const detail = await getRunDetail(runId);
  return { detail, chunks: recordedRetrievalChunks(detail) };
}

export function toolRegistryGroups(tools: ToolListItem[]) {
  // An explicit backend capability is required; unknown capability fails closed.
  const isExecutable = (tool: ToolListItem) =>
    tool.executable === true && tool.is_destructive === false && tool.requires_human_approval === false;
  return [
    { key: "executable", label: "Executable local adapters", tools: tools.filter(isExecutable) },
    { key: "blocked", label: "Blocked action definitions", tools: tools.filter((tool) => !isExecutable(tool)) }
  ] as const;
}
