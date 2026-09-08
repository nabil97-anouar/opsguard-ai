export type BackendErrorPayload = {
  detail?: string;
};

export type HealthPayload = {
  status: "healthy";
  version: string;
  environment: string;
  dependencies: {
    postgres: string;
    qdrant: string;
    llm_provider: string;
  };
  timestamp: string;
};

export type DemoSeedSummary = {
  status: "ok";
  created: Record<string, number>;
  updated: Record<string, number>;
  skipped: Record<string, number>;
};

export type DemoSeedResponse = {
  status: "ok";
  message: string;
  summary: DemoSeedSummary;
};

export type TrustLevel = "trusted" | "untrusted" | "quarantined";
export type ExecutionProvenance = "executed" | "fixture" | "legacy_unknown";
export type HarnessTestLevel = "end_to_end" | "component" | "policy" | "tool_boundary" | "legacy_unknown";

export type DocumentListItem = {
  id: string;
  title: string;
  source: string;
  doc_type: string;
  trust_level: TrustLevel;
  created_at: string;
};

export type DocumentIngestRequest = {
  title: string;
  source: string;
  doc_type: string;
  trust_level?: Exclude<TrustLevel, "trusted">;
  content: string;
  metadata?: Record<string, unknown> | null;
};

export type DocumentIngestResponse = {
  status: "ok";
  document_id: string;
  created: boolean;
  updated: boolean;
  skipped: boolean;
  chunk_count: number;
};

export type RetrievalChunk = {
  evidence_id?: string;
  observed_at?: string;
  document_id: string;
  chunk_id: string;
  title: string;
  source: string;
  chunk_index: number;
  trust_level: TrustLevel;
  doc_type: string;
  score: number;
  content_excerpt: string;
  is_suspicious: boolean;
  matched_patterns: string[];
  risk_level: string;
  citation: string;
};

export type RagRetrieveRequest = {
  query: string;
  limit?: number;
  trust_filter?: TrustLevel | null;
  include_untrusted?: boolean;
};

export type RagRetrieveResponse = {
  status: "ok";
  query: string;
  results: RetrievalChunk[];
};

export type ToolListItem = {
  name: string;
  description: string;
  trust_level: string;
  allowed_use: string[];
  blocked_use: string[];
  requires_human_approval: boolean;
  is_destructive: boolean;
  executable: boolean;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
};

export type ToolListResponse = {
  status: "ok";
  items: ToolListItem[];
};

export type ToolCall = {
  handler_invoked?: boolean | null;
  outcome?: string;
  origin?: string;
  id: string;
  agent_run_id: string;
  step_id: string;
  tool_name: string;
  input_args: Record<string, unknown>;
  output: unknown;
  trust_level: string;
  duration_ms: number | null;
  status: string;
  error_message: string | null;
  injection_scan_result: string;
  created_at: string;
};

export type AgentAssessment = {
  capability_area: string;
  confidence_score: number;
  uncertainty_level: string;
  what_agent_knows: string[];
  missing_evidence: string[];
  within_capability: boolean;
  decision: string;
  rationale: string;
  risk_flags: string[];
  overridden_by_policy: boolean;
};

export type WatchdogFinding = {
  finding_id?: string;
  finding_type?: string;
  affected_action_ids?: string[];
  blocking?: boolean;
  mandatory_review?: boolean;
  policy_id: string;
  title: string;
  severity: string;
  status: string;
  reason: string;
  evidence_refs: string[];
  remediation: string;
  metadata: Record<string, unknown>;
};

export type EvidenceItem = {
  evidence_id: string;
  kind: "alert" | "retrieval" | "tool_output";
  source_type: "alert" | "document" | "tool";
  source: string;
  alert_id?: string | null;
  document_id: string | null;
  chunk_id: string | null;
  tool_call_id: string | null;
  retrieval_score: number | null;
  trust_level: TrustLevel;
  content: string | Record<string, unknown>;
  observed_at: string;
  summary: string;
  citation: string;
  suspicious: boolean;
  title?: string | null;
  chunk_index?: number | null;
  doc_type?: string | null;
  matched_patterns?: string[];
  risk_level?: string;
};

export type FinalRecommendation = {
  proposed_actions?: ProposedAction[];
  lifecycle_state?: "candidate" | "pending_human_review" | "blocked";
  review_valid?: boolean;
  policy_version?: string | null;
  watchdog_decision?: WatchdogDecision | null;
  summary: string;
  // Older stored runs may contain the previous, less complete evidence shape.
  evidence: Array<EvidenceItem | Record<string, unknown>>;
  citations: string[];
  recommended_next_steps: string[];
  blocked_actions_requiring_human_approval: Array<Record<string, unknown>>;
  uncertainty: string;
  missing_evidence: string[];
  notes: string[];
  requires_human_approval: boolean;
  ticket_draft_id: string | null;
  watchdog_status: string | null;
  watchdog_summary: string | null;
  watchdog_findings: WatchdogFinding[];
};

export type AgentStep = {
  id: string;
  step_index: number;
  node_name: string;
  status: string;
  input_snapshot: Record<string, unknown>;
  output_snapshot: Record<string, unknown>;
  duration_ms: number | null;
  error: string | null;
  created_at: string;
};

export type AgentRunResponse = {
  status: "waiting_for_human" | "failed";
  agent_run_id: string;
  alert_id: string;
  steps: AgentStep[];
  self_assessment: AgentAssessment | null;
  final_recommendation: FinalRecommendation | null;
};

export type AgentRunDetailResponse = {
  agent_run_id: string;
  alert_id: string;
  status: string;
  provenance: ExecutionProvenance;
  execution_kind: string;
  provider_version: string | null;
  policy_version: string | null;
  llm_provider: string;
  model_version: string | null;
  risk_level: string;
  approval_status: string;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  error_message: string | null;
  steps: AgentStep[];
  tool_calls: ToolCall[];
  tool_attempts?: ToolAttempt[];
  self_assessment: AgentAssessment | null;
  final_recommendation: FinalRecommendation | null;
};

export type AgentRunListItem = {
  agent_run_id: string;
  alert_id: string;
  status: string;
  provenance: ExecutionProvenance;
  risk_level: string;
  approval_status: string;
  started_at: string;
  completed_at: string | null;
};

export type AgentRunListResponse = {
  status: "ok";
  items: AgentRunListItem[];
};

export type WatchdogPoliciesResponse = {
  status: string;
  items: WatchdogPolicyItem[];
};

export type WatchdogPolicyItem = {
  policy_id: string;
  title: string;
  description: string;
};

export type HarnessScenarioResponse = {
  scenario_id: string;
  scenario_version: string;
  test_level: HarnessTestLevel;
  expectations: Record<string, unknown>;
  name: string;
  category: string;
  description: string;
  attack_type: string;
  expected_behavior: string;
  severity: string;
  injection_point: string;
  input_config: Record<string, unknown>;
  success_criteria: string[];
};

export type HarnessScenarioListResponse = {
  status: "ok";
  items: HarnessScenarioResponse[];
};

export type HarnessResultResponse = {
  scenario_id: string;
  scenario_version: string;
  test_level: HarnessTestLevel;
  provenance: ExecutionProvenance;
  mandatory_invariants: Record<string, boolean>;
  invariant_failures: string[];
  expectations: Record<string, unknown>;
  observations: Record<string, unknown>;
  human_review_required: boolean | null;
  human_review_reached: boolean | null;
  terminal_status: string | null;
  name: string;
  category: string;
  status: "passed" | "failed" | "partial";
  score: number;
  observed_behavior: string;
  expected_behavior: string;
  findings: WatchdogFinding[];
  safety_events: Array<Record<string, unknown>>;
  agent_run_id: string | null;
  tool_call_ids: string[];
  watchdog_status: string | null;
  failure_reason: string | null;
  injection_detected: boolean;
  action_blocked: boolean;
  harness_run_id: string | null;
  harness_result_id: string | null;
  created_at: string | null;
  metadata: Record<string, unknown>;
};

export type HarnessRunResponse = {
  status: "running" | "completed" | "failed" | "not_executed" | "legacy_unknown";
  harness_run_id: string;
  provenance: ExecutionProvenance;
  started_at: string | null;
  completed_at: string | null;
  expected_case_count: number | null;
  completed_case_count: number;
  provider_version: string | null;
  policy_version: string | null;
  scenario_manifest: Array<Record<string, unknown>>;
  total: number;
  passed: number;
  failed: number;
  partial: number;
  results: HarnessResultResponse[];
};

export type HarnessResultListResponse = {
  status: "ok";
  items: HarnessResultResponse[];
};

export type EvaluationMetric = {
  numerator: number;
  denominator: number;
  value: number | null;
  unit: "rate";
  definition: string;
};

export type EvaluationCohort = {
  harness_run_id: string | null;
  provenance: "executed" | "none";
  execution_started_at: string | null;
  execution_completed_at: string | null;
  agent_run_ids: string[];
  component_run_ids: string[];
  scenario_manifest: Array<{
    scenario_id: string;
    scenario_version: string;
    test_level: HarnessTestLevel;
    [key: string]: unknown;
  }>;
  expected_case_count: number;
  completed_case_count: number;
  provider_version: string | null;
  policy_version: string | null;
};

export type EvaluationSummaryResponse = {
  schema_version: "evaluation-v2";
  report_kind: "stored" | "live_preview";
  evaluation_run_id: string | null;
  generated_at: string;
  report_type: string;
  cohort: EvaluationCohort;
  metrics: Record<string, EvaluationMetric>;
  scenario_results: HarnessResultResponse[];
  agent_run_snapshots: Array<Record<string, unknown>>;
  failed_scenarios: string[];
  mandatory_invariant_failures: Array<{ scenario_id: string; invariant: string }>;
  limitations: string[];
};

export type EvaluationRunResponse = {
  status: "ok";
  persisted: boolean;
  evaluation_run_id: string;
  summary: EvaluationSummaryResponse;
};

export const DEMO_ALERT_IDS = {
  gpuAbuse: "909d28d2-5c9f-5fa2-a35e-f6b39c95f83f",
  promptInjection: "e3e0e0d5-9e19-5243-a1f0-76c507be3641"
} as const;


export type ProposedAction = {
  action_id: string;
  action_type: string;
  target: string | null;
  parameters: Record<string, unknown>;
  risk_level: "low" | "medium" | "high" | "critical";
  requires_approval: boolean;
  supporting_evidence_ids: string[];
  rationale: string;
};

export type WatchdogDecision = {
  verdict: "allow" | "allow_with_warnings" | "require_human_approval" | "block";
  blocking: boolean;
  mandatory_review: boolean;
  policy_version: string;
  severity: string;
  reason: string;
  affected_action_ids: string[];
  finding_ids: string[];
};

export type ToolAttempt = {
  id: string;
  agent_run_id: string | null;
  step_id: string | null;
  tool_name: string;
  origin: string;
  input_snapshot: unknown;
  validated_target: Record<string, unknown>;
  outcome: "requested" | "validated" | "denied" | "invoked" | "succeeded" | "failed";
  validated: boolean;
  handler_invoked: boolean;
  requested_at: string;
  invoked_at: string | null;
  completed_at: string | null;
  output_snapshot: unknown;
  error_code: string | null;
  user_error: string | null;
  diagnostic: Record<string, unknown>;
};
