# DATA_MODEL.md — OpsGuard AI Database Schema

## Overview

All relational data is stored in PostgreSQL using SQLModel (SQLAlchemy core with Pydantic validation). All primary keys are UUIDs. Timestamps are always UTC ISO 8601. Enums are stored as VARCHAR with Python Enum validation.

---

## Table: `alerts`

Stores incoming operational alerts from all infrastructure sources.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | Auto-generated |
| `title` | VARCHAR(500) | Alert title |
| `severity` | VARCHAR(20) | `info` / `warning` / `error` / `critical` |
| `source` | VARCHAR(100) | e.g., `prometheus`, `slurm`, `grafana`, `manual` |
| `infrastructure_type` | VARCHAR(50) | `gpu_cluster` / `cloud` / `hpc` / `devops` / `security` / `saas` |
| `raw_data` | JSONB | Full alert payload — treated as untrusted |
| `status` | VARCHAR(30) | `new` / `investigating` / `resolved` / `escalated` / `closed` |
| `agent_run_id` | UUID FK → `agent_runs.id` | Nullable |
| `created_at` | TIMESTAMPTZ | UTC |
| `updated_at` | TIMESTAMPTZ | UTC |
| `resolved_at` | TIMESTAMPTZ | Nullable |
| `tags` | TEXT[] | e.g., `["gpu", "memory", "node-04"]` |
| `is_demo` | BOOLEAN | True for seeded demo data |

**Indexes:** `status`, `severity`, `infrastructure_type`, `created_at`, `is_demo`

**Example row:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "GPU memory overflow on node-04 — NVIDIA NVML error",
  "severity": "critical",
  "source": "prometheus",
  "infrastructure_type": "gpu_cluster",
  "raw_data": {
    "node": "gpu-node-04",
    "gpu_id": 3,
    "memory_used_gb": 79.8,
    "memory_total_gb": 80,
    "log_lines": ["ERROR kernel: NVML error on GPU 3 — ECC memory error"]
  },
  "status": "investigating",
  "tags": ["gpu", "memory", "critical", "node-04"],
  "is_demo": true
}
```

---

## Table: `incidents`

Finalized incident records after investigation.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `alert_id` | UUID FK → `alerts.id` | |
| `agent_run_id` | UUID FK → `agent_runs.id` | |
| `title` | VARCHAR(500) | |
| `severity` | VARCHAR(20) | |
| `root_cause` | TEXT | Best supported hypothesis |
| `resolution` | TEXT | What was done or recommended |
| `kill_chain_stage` | VARCHAR(100) | Nullable |
| `status` | VARCHAR(30) | `open` / `resolved` / `postmortem` |
| `created_at` | TIMESTAMPTZ | |
| `resolved_at` | TIMESTAMPTZ | Nullable |
| `is_demo` | BOOLEAN | |

---

## Table: `documents`

Ingested knowledge base documents (runbooks, incident reports, policies, etc.).

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `title` | VARCHAR(500) | |
| `source_type` | VARCHAR(50) | `runbook` / `incident_report` / `security_policy` / `ops_doc` / `checklist` |
| `file_path` | VARCHAR(500) | Relative path under `demo_data/` |
| `content_hash` | VARCHAR(64) | SHA-256 of content for dedup |
| `trust_level` | VARCHAR(20) | `trusted` / `untrusted` / `quarantined` |
| `tags` | TEXT[] | |
| `infrastructure_type` | VARCHAR(50) | |
| `version` | VARCHAR(20) | e.g., `1.0`, `2024-11` |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |
| `is_demo` | BOOLEAN | |
| `chunk_count` | INT | Total chunks created |
| `injection_scan_result` | VARCHAR(20) | `clean` / `flagged` / `quarantined` / `pending` |

**Indexes:** `source_type`, `trust_level`, `tags` (GIN)

**Example row:**
```json
{
  "id": "doc-uuid-001",
  "title": "GPU Memory Overflow Recovery Runbook",
  "source_type": "runbook",
  "trust_level": "trusted",
  "tags": ["gpu", "memory", "recovery", "nvidia"],
  "infrastructure_type": "gpu_cluster",
  "version": "2.1",
  "chunk_count": 8,
  "injection_scan_result": "clean"
}
```

---

## Table: `document_chunks`

Individual chunks from ingested documents, stored in PostgreSQL for relational queries and in Qdrant for vector search.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | Also used as Qdrant point ID |
| `document_id` | UUID FK → `documents.id` | |
| `chunk_index` | INT | Position within document |
| `content` | TEXT | Raw chunk text |
| `content_hash` | VARCHAR(64) | For dedup |
| `token_count` | INT | |
| `metadata` | JSONB | Headings, section, page ref, etc. |
| `trust_level` | VARCHAR(20) | Inherited from document |
| `injection_scan_result` | VARCHAR(20) | `clean` / `flagged` |
| `created_at` | TIMESTAMPTZ | |

---

## Table: `agent_runs`

One record per investigation triggered on an alert.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `alert_id` | UUID FK → `alerts.id` | |
| `status` | VARCHAR(30) | `running` / `completed` / `failed` / `rejected` / `stopped` / `awaiting_approval` |
| `llm_provider` | VARCHAR(50) | e.g., `openai_gpt4`, `anthropic_claude`, `mock` |
| `model_version` | VARCHAR(50) | |
| `total_steps` | INT | |
| `total_tool_calls` | INT | |
| `total_tokens_used` | INT | Nullable |
| `evidence_grounding_score` | FLOAT | Final score |
| `risk_level` | VARCHAR(20) | `low` / `medium` / `high` / `critical` |
| `approval_status` | VARCHAR(20) | `not_required` / `pending` / `approved` / `rejected` / `expired` |
| `started_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ | Nullable |
| `duration_seconds` | FLOAT | Nullable |
| `error_message` | TEXT | Nullable |
| `is_demo` | BOOLEAN | |

---

## Table: `agent_steps`

One record per node execution in an agent run.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `agent_run_id` | UUID FK → `agent_runs.id` | |
| `step_index` | INT | Order within run |
| `node_name` | VARCHAR(100) | e.g., `classify_alert`, `retrieve_context` |
| `status` | VARCHAR(20) | `running` / `completed` / `failed` / `skipped` |
| `input_snapshot` | JSONB | State snapshot before node |
| `output_snapshot` | JSONB | State mutations from node |
| `duration_ms` | INT | |
| `error` | TEXT | Nullable |
| `created_at` | TIMESTAMPTZ | |

---

## Table: `self_assessments`

Metacognitive self-assessment records from each assessment node execution.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `agent_run_id` | UUID FK → `agent_runs.id` | |
| `step_id` | UUID FK → `agent_steps.id` | |
| `capability_area` | VARCHAR(100) | e.g., `gpu_incident_triage`, `security_analysis` |
| `confidence_score` | FLOAT | 0.0–1.0 |
| `uncertainty_level` | VARCHAR(20) | `low` / `medium` / `high` / `critical` |
| `what_agent_knows` | TEXT[] | List of available evidence items |
| `missing_evidence` | TEXT[] | List of missing evidence items |
| `within_capability` | BOOLEAN | |
| `decision` | VARCHAR(30) | `continue` / `retrieve_more` / `call_tool` / `ask_human` / `stop` / `delegate` |
| `rationale` | TEXT | Plain English explanation |
| `overridden_by_policy` | BOOLEAN | Whether watchdog overrode this decision |
| `created_at` | TIMESTAMPTZ | |

**Example row:**
```json
{
  "id": "assess-uuid-001",
  "agent_run_id": "run-uuid-001",
  "step_id": "step-uuid-003",
  "capability_area": "gpu_incident_triage",
  "confidence_score": 0.52,
  "uncertainty_level": "medium",
  "what_agent_knows": [
    "GPU memory utilization: 99.7%",
    "ECC memory errors detected",
    "Node: gpu-node-04, GPU: 3"
  ],
  "missing_evidence": [
    "Process-level memory breakdown",
    "Recent job history on this node",
    "Historical ECC error rate for this GPU"
  ],
  "within_capability": true,
  "decision": "retrieve_more",
  "rationale": "GPU memory overflow is within capability, but missing process breakdown and job history to confirm root cause. Retrieving runbook and querying job history before proceeding.",
  "overridden_by_policy": false
}
```

---

## Table: `tool_calls`

Audit log for every tool invocation during an agent run.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `agent_run_id` | UUID FK → `agent_runs.id` | |
| `step_id` | UUID FK → `agent_steps.id` | |
| `tool_name` | VARCHAR(100) | |
| `input_args` | JSONB | Validated input |
| `output` | JSONB | Raw tool output |
| `trust_level` | VARCHAR(20) | `trusted` / `untrusted` |
| `duration_ms` | INT | |
| `status` | VARCHAR(20) | `success` / `error` / `timeout` / `blocked` |
| `error_message` | TEXT | Nullable |
| `injection_scan_result` | VARCHAR(20) | `clean` / `flagged` |
| `created_at` | TIMESTAMPTZ | |

---

## Table: `safety_events`

All safety-relevant events: injections detected, policy violations, watchdog blocks.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `agent_run_id` | UUID FK → `agent_runs.id` | Nullable |
| `harness_result_id` | UUID FK → `security_harness_results.id` | Nullable |
| `event_type` | VARCHAR(100) | e.g., `prompt_injection_detected`, `policy_violation`, `dangerous_action_blocked` |
| `severity` | VARCHAR(20) | `info` / `warning` / `error` / `critical` |
| `source` | VARCHAR(100) | Which component detected it |
| `affected_component` | VARCHAR(100) | e.g., `retrieved_doc`, `tool_output`, `recommendation` |
| `details` | JSONB | Full event detail |
| `pattern_matched` | TEXT | The specific pattern that triggered |
| `resolved` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

---

## Table: `kill_chain_mappings`

Stores AI kill-chain analysis for each agent run.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `agent_run_id` | UUID FK → `agent_runs.id` | |
| `stages_detected` | TEXT[] | List of detected stage names |
| `primary_stage` | VARCHAR(100) | Nullable |
| `stage_confidence` | JSONB | `{stage_name: confidence_float}` |
| `stage_indicators` | JSONB | `{stage_name: [evidence_item]}` |
| `overall_confidence` | FLOAT | |
| `rationale` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

---

## Table: `human_feedback`

Stores human approval decisions and feedback on agent recommendations.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `agent_run_id` | UUID FK → `agent_runs.id` | |
| `decision` | VARCHAR(20) | `approved` / `rejected` |
| `reviewer_id` | VARCHAR(100) | e.g., user ID or demo "operator-1" |
| `reason` | TEXT | Free text reason |
| `modified_actions` | JSONB | Optional overridden action list |
| `created_at` | TIMESTAMPTZ | |

---

## Table: `evaluation_scores`

Per-run evaluation metrics.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `agent_run_id` | UUID FK → `agent_runs.id` | |
| `evidence_grounding` | FLOAT | 0.0–1.0 |
| `correctness` | FLOAT | 0.0–1.0 (vs. demo ground truth) |
| `non_speculativeness` | FLOAT | |
| `incident_focus` | FLOAT | |
| `actionability` | FLOAT | |
| `safety_score` | FLOAT | |
| `response_time_seconds` | FLOAT | |
| `safety_violations_blocked` | INT | |
| `prompt_injection_resistance` | FLOAT | |
| `tool_misuse_resistance` | FLOAT | |
| `uncertainty_calibration` | FLOAT | |
| `human_approval_usefulness` | FLOAT | Nullable (only if approval occurred) |
| `overall_score` | FLOAT | Weighted aggregate |
| `created_at` | TIMESTAMPTZ | |

---

## Table: `ticket_drafts`

Draft incident tickets generated by the agent.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `agent_run_id` | UUID FK → `agent_runs.id` | |
| `alert_id` | UUID FK → `alerts.id` | |
| `title` | VARCHAR(500) | |
| `severity` | VARCHAR(20) | |
| `description` | TEXT | |
| `steps_to_reproduce` | TEXT[] | |
| `suggested_actions` | JSONB | |
| `evidence_links` | TEXT[] | |
| `kill_chain_stage` | VARCHAR(100) | Nullable |
| `assigned_team` | VARCHAR(100) | |
| `sla_target` | VARCHAR(50) | |
| `exported` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

---

## Table: `security_harness_tests`

Definitions of security harness test scenarios (loaded from YAML/JSON registry).

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `test_id` | VARCHAR(50) | e.g., `PI-001` |
| `category` | VARCHAR(50) | `prompt_injection` / `kill_chain` / `secret_leakage` / `unsupported_conclusion` |
| `name` | VARCHAR(200) | |
| `description` | TEXT | |
| `injection_point` | VARCHAR(100) | Where the attack is injected |
| `attack_payload` | JSONB | The test input |
| `expected_behavior` | TEXT | |
| `detection_logic` | TEXT | |
| `max_score` | INT | |
| `weight` | FLOAT | For aggregate scoring |
| `active` | BOOLEAN | |

---

## Table: `security_harness_results`

Results of harness test runs.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `harness_run_id` | UUID | Groups tests from one harness run |
| `test_id` | UUID FK → `security_harness_tests.id` | |
| `score` | INT | 0–10 |
| `max_score` | INT | |
| `passed` | BOOLEAN | |
| `actual_behavior` | TEXT | What the agent actually did |
| `injection_detected` | BOOLEAN | |
| `action_blocked` | BOOLEAN | |
| `safety_event_id` | UUID FK → `safety_events.id` | Nullable |
| `details` | JSONB | Full test execution detail |
| `created_at` | TIMESTAMPTZ | |

---

## Relationships Summary

```
alerts 1──────────── 0..1 agent_runs
agent_runs 1──────── * agent_steps
agent_runs 1──────── * self_assessments
agent_runs 1──────── * tool_calls
agent_runs 1──────── * safety_events
agent_runs 1──────── 0..1 kill_chain_mappings
agent_runs 1──────── * human_feedback
agent_runs 1──────── 1 evaluation_scores
agent_runs 1──────── 0..1 ticket_drafts
alerts 1─────────── 0..1 incidents
documents 1────────── * document_chunks
security_harness_tests 1──── * security_harness_results
```
