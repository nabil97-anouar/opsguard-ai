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

export type DocumentListItem = {
  id: string;
  title: string;
  source: string;
  doc_type: string;
  trust_level: string;
  created_at: string;
};

export type DocumentIngestRequest = {
  title: string;
  source: string;
  doc_type: string;
  trust_level: string;
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
  document_id: string;
  chunk_id: string;
  title: string;
  source: string;
  chunk_index: number;
  trust_level: string;
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
  trust_filter?: string | null;
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
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
};

export type ToolListResponse = {
  status: "ok";
  items: ToolListItem[];
};

export type ToolCall = {
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
  policy_id: string;
  title: string;
  severity: string;
  status: string;
  reason: string;
  evidence_refs: string[];
  remediation: string;
  metadata: Record<string, unknown>;
};

export type FinalRecommendation = {
  summary: string;
  evidence: Array<Record<string, unknown>>;
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
  self_assessment: AgentAssessment | null;
  final_recommendation: FinalRecommendation | null;
};

export type AgentRunListItem = {
  agent_run_id: string;
  alert_id: string;
  status: string;
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
  status: "completed";
  harness_run_id: string;
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

export type EvaluationScorecard = {
  safety_score: number;
  grounding_score: number;
  tool_safety_score: number;
  watchdog_score: number;
  overall_score: number;
};

export type EvaluationHarnessPerformance = {
  total_scenarios: number;
  passed: number;
  partial: number;
  failed: number;
  pass_rate: number;
  average_score: number;
  latest_harness_run_id: string | null;
};

export type EvaluationSummaryResponse = {
  generated_at: string;
  report_type: string;
  latest_agent_run_id: string | null;
  latest_harness_run_id: string | null;
  harness_performance: EvaluationHarnessPerformance;
  prompt_injection_resistance: {
    prompt_injection_events: number;
    unsafe_tool_output_events: number;
    suspicious_retrieval_events: number;
    prompt_injection_scenarios_passed: number;
    prompt_injection_scenarios_total: number;
  };
  tool_safety: {
    total_tool_calls: number;
    blocked_tool_calls: number;
    failed_tool_calls: number;
    flagged_tool_outputs: number;
    dangerous_tool_attempts: number;
    arbitrary_shell_execution_present: boolean;
  };
  agent_quality: {
    total_agent_runs: number;
    waiting_for_human_runs: number;
    failed_runs: number;
    average_confidence: number;
    low_confidence_high_severity_count: number;
    runs_with_self_assessment: number;
    runs_with_ticket_draft: number;
  };
  grounding_evidence: {
    runs_with_citations: number;
    runs_missing_citations: number;
    weak_grounding_events: number;
    untrusted_context_events: number;
  };
  human_approval_enforcement: {
    runs_requiring_human_approval: number;
    dangerous_recommendations_requiring_human_approval: number;
    auto_executed_dangerous_actions: number;
  };
  scorecard: EvaluationScorecard;
  executive_summary: string;
  limitations: string[];
};

export type EvaluationRunResponse = {
  status: "ok";
  persisted: boolean;
  evaluation_score_id: string | null;
  summary: EvaluationSummaryResponse;
  scorecard: EvaluationScorecard;
};

export const DEMO_ALERT_IDS = {
  gpuAbuse: "909d28d2-5c9f-5fa2-a35e-f6b39c95f83f",
  promptInjection: "e3e0e0d5-9e19-5243-a1f0-76c507be3641"
} as const;

export const DEMO_RAG_QUERIES = {
  gpuAbuse: {
    query: "gpu xmrig suspicious process mining pool",
    limit: 5,
    include_untrusted: false
  },
  promptInjection: {
    query: "system override ignore policies poisoned runbook",
    limit: 5,
    include_untrusted: true
  }
} as const;
