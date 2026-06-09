# API_SPEC.md — OpsGuard AI FastAPI Endpoint Specifications

## Base URL

```
http://localhost:8000/api/v1
```

All responses are JSON. All timestamps are ISO 8601 UTC. All IDs are UUIDs.

Error response envelope:
```json
{
  "detail": "Human-readable error message",
  "error_code": "SNAKE_CASE_CODE",
  "timestamp": "2024-11-15T10:30:00Z"
}
```

---

## GET /health

**Purpose:** Service health check. Returns status of all critical dependencies.

**Request body:** None

**Response body:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "postgres": "healthy",
    "qdrant": "healthy",
    "llm_provider": "mock"
  },
  "timestamp": "2024-11-15T10:30:00Z"
}
```

**Validation rules:** None

**Example request:**
```bash
curl http://localhost:8000/api/v1/health
```

---

## POST /demo/seed

**Purpose:** Seed the database with demo alerts, documents, agent run traces, and security harness results. Idempotent — clears existing demo data and re-seeds.

**Request body:**
```json
{
  "clear_existing": true,
  "scenario_set": "full"
}
```

`scenario_set`: `"full"` (all scenarios) | `"minimal"` (5 alerts only) | `"security_focus"` (harness-heavy)

**Response body:**
```json
{
  "status": "seeded",
  "alerts_created": 22,
  "documents_ingested": 15,
  "agent_runs_created": 10,
  "harness_tests_created": 12,
  "seed_duration_seconds": 8.4
}
```

**Validation rules:**
- Only available when `DEMO_MODE=true` in environment

---

## POST /documents/ingest

**Purpose:** Ingest a document into the knowledge base. Chunks, embeds, and stores in Qdrant and PostgreSQL.

**Request body:** `multipart/form-data`
```
file: <file upload>
source_type: runbook | incident_report | security_policy | ops_doc | checklist
trust_level: trusted | untrusted
tags: ["gpu", "memory", "recovery"]  (JSON array as form field)
infrastructure_type: gpu_cluster | cloud | hpc | devops | security | saas
```

**Response body:**
```json
{
  "document_id": "doc-uuid-001",
  "title": "GPU Memory Overflow Recovery Runbook",
  "chunk_count": 8,
  "injection_scan_result": "clean",
  "status": "ingested"
}
```

**Validation rules:**
- File types accepted: `.md`, `.txt`, `.yaml`, `.yml`, `.json`, `.pdf`
- Max file size: 5 MB
- `trust_level` is required; default is `untrusted`
- Injection scan runs synchronously; if flagged, `status = "quarantined"`, document not added to retrieval

**Example request:**
```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F "file=@runbooks/gpu_overflow.md" \
  -F "source_type=runbook" \
  -F "trust_level=trusted" \
  -F "tags=[\"gpu\",\"memory\"]" \
  -F "infrastructure_type=gpu_cluster"
```

---

## GET /documents

**Purpose:** List all ingested documents.

**Query params:**
- `source_type`: filter
- `trust_level`: filter
- `infrastructure_type`: filter
- `injection_scan_result`: filter
- `page`: int (default 1)
- `page_size`: int (default 20, max 100)

**Response body:**
```json
{
  "items": [
    {
      "id": "doc-uuid-001",
      "title": "GPU Memory Overflow Recovery Runbook",
      "source_type": "runbook",
      "trust_level": "trusted",
      "chunk_count": 8,
      "injection_scan_result": "clean",
      "tags": ["gpu", "memory"],
      "created_at": "2024-11-01T09:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

---

## POST /rag/retrieve

**Purpose:** Run a RAG query against the knowledge base. Used for debugging and evaluation.

**Request body:**
```json
{
  "query": "GPU memory overflow ECC error recovery steps",
  "infrastructure_type": "gpu_cluster",
  "top_k": 5,
  "trust_level_filter": "trusted"
}
```

**Response body:**
```json
{
  "query": "GPU memory overflow ECC error recovery steps",
  "results": [
    {
      "chunk_id": "chunk-uuid-001",
      "document_id": "doc-uuid-001",
      "document_title": "GPU Memory Overflow Recovery Runbook",
      "content": "## Step 1: Check NVML error logs...",
      "relevance_score": 0.94,
      "trust_level": "trusted",
      "citation": "GPU Memory Overflow Recovery Runbook, Section 2, Chunk 3"
    }
  ],
  "retrieval_duration_ms": 45
}
```

**Validation rules:**
- `top_k` max: 20
- Query max length: 500 characters

---

## GET /alerts

**Purpose:** List all alerts with filtering and pagination.

**Query params:**
- `status`: new | investigating | resolved | escalated | closed
- `severity`: info | warning | error | critical
- `infrastructure_type`: filter
- `is_demo`: bool
- `page`, `page_size`

**Response body:**
```json
{
  "items": [
    {
      "id": "alert-uuid-001",
      "title": "GPU memory overflow on node-04",
      "severity": "critical",
      "source": "prometheus",
      "infrastructure_type": "gpu_cluster",
      "status": "investigating",
      "agent_run_id": "run-uuid-001",
      "tags": ["gpu", "memory"],
      "created_at": "2024-11-15T08:00:00Z"
    }
  ],
  "total": 22,
  "page": 1,
  "page_size": 20
}
```

---

## POST /alerts

**Purpose:** Create a new alert manually.

**Request body:**
```json
{
  "title": "GPU memory overflow on node-04",
  "severity": "critical",
  "source": "prometheus",
  "infrastructure_type": "gpu_cluster",
  "raw_data": {
    "node": "gpu-node-04",
    "gpu_id": 3,
    "memory_used_gb": 79.8
  },
  "tags": ["gpu", "memory"]
}
```

**Response body:**
```json
{
  "id": "alert-uuid-001",
  "status": "new",
  "created_at": "2024-11-15T10:30:00Z"
}
```

**Validation rules:**
- `title`: max 500 chars
- `severity`: must be valid enum
- `raw_data`: sanitized — control characters stripped, max 50KB

---

## POST /alerts/{alert_id}/investigate

**Purpose:** Trigger an agent investigation run for a specific alert.

**Path params:** `alert_id`: UUID

**Request body:**
```json
{
  "llm_provider": "mock",
  "model_version": "mock-v1",
  "priority": "high"
}
```

**Response body:**
```json
{
  "agent_run_id": "run-uuid-001",
  "status": "running",
  "started_at": "2024-11-15T10:30:05Z"
}
```

**Validation rules:**
- Alert must exist and not be in `resolved` or `closed` status
- If alert already has a running agent run, return 409 Conflict
- `llm_provider` must be in configured provider list

**Notes:**
- Agent run executes asynchronously (background task)
- Frontend polls `GET /agent-runs/{run_id}` for status
- Or use SSE endpoint `GET /agent-runs/{run_id}/stream` (optional)

---

## GET /agent-runs/{run_id}

**Purpose:** Get the status and summary of an agent run.

**Response body:**
```json
{
  "id": "run-uuid-001",
  "alert_id": "alert-uuid-001",
  "status": "awaiting_approval",
  "llm_provider": "mock",
  "total_steps": 12,
  "total_tool_calls": 4,
  "evidence_grounding_score": 0.78,
  "risk_level": "high",
  "approval_status": "pending",
  "started_at": "2024-11-15T10:30:05Z",
  "completed_at": null,
  "duration_seconds": null
}
```

---

## GET /agent-runs/{run_id}/trace

**Purpose:** Get the full step-by-step execution trace for an agent run.

**Response body:**
```json
{
  "run_id": "run-uuid-001",
  "steps": [
    {
      "id": "step-uuid-001",
      "step_index": 1,
      "node_name": "ingest_alert",
      "status": "completed",
      "duration_ms": 12,
      "input_snapshot": { "alert_id": "alert-uuid-001" },
      "output_snapshot": { "alert_raw": { "title": "...", "severity": "critical" } },
      "created_at": "2024-11-15T10:30:05Z"
    },
    {
      "id": "step-uuid-003",
      "step_index": 3,
      "node_name": "metacognitive_self_assessment",
      "status": "completed",
      "duration_ms": 340,
      "output_snapshot": {
        "self_assessment": {
          "confidence_score": 0.52,
          "decision": "retrieve_more",
          "rationale": "GPU metrics available but missing process breakdown"
        }
      }
    }
  ]
}
```

---

## GET /agent-runs/{run_id}/self-assessments

**Purpose:** Get all metacognitive self-assessment records for an agent run.

**Response body:**
```json
{
  "run_id": "run-uuid-001",
  "self_assessments": [
    {
      "id": "assess-uuid-001",
      "step_id": "step-uuid-003",
      "capability_area": "gpu_incident_triage",
      "confidence_score": 0.52,
      "uncertainty_level": "medium",
      "what_agent_knows": ["GPU utilization 99.7%", "ECC errors detected"],
      "missing_evidence": ["Process breakdown", "Job history"],
      "within_capability": true,
      "decision": "retrieve_more",
      "rationale": "Evidence partially available but job history is critical for root cause",
      "created_at": "2024-11-15T10:30:07Z"
    }
  ]
}
```

---

## POST /agent-runs/{run_id}/approve

**Purpose:** Human approves a pending agent recommendation.

**Request body:**
```json
{
  "decision": "approved",
  "reviewer_id": "operator-1",
  "reason": "Root cause analysis looks correct. Actions are appropriate.",
  "modified_actions": []
}
```

**Response body:**
```json
{
  "status": "approved",
  "agent_run_id": "run-uuid-001",
  "resumed_at": "2024-11-15T10:45:00Z"
}
```

**Validation rules:**
- Agent run must have `approval_status = "pending"`
- `reviewer_id` required

---

## POST /agent-runs/{run_id}/reject

**Purpose:** Human rejects a pending agent recommendation.

**Request body:**
```json
{
  "decision": "rejected",
  "reviewer_id": "operator-1",
  "reason": "Root cause assessment is incorrect. Needs more log data from node-04."
}
```

**Response body:**
```json
{
  "status": "rejected",
  "agent_run_id": "run-uuid-001",
  "workflow_ended_at": "2024-11-15T10:46:00Z"
}
```

---

## POST /feedback

**Purpose:** Submit human feedback on an agent run for evaluation improvement.

**Request body:**
```json
{
  "agent_run_id": "run-uuid-001",
  "correctness_rating": 4,
  "usefulness_rating": 5,
  "safety_rating": 5,
  "comments": "Correct root cause. Missing action to restart the CUDA context.",
  "ground_truth_root_cause": "ECC memory error in GPU 3 caused by overheated HBM module"
}
```

**Response body:**
```json
{
  "feedback_id": "feedback-uuid-001",
  "status": "recorded"
}
```

---

## POST /security-harness/run

**Purpose:** Trigger a full or partial security harness run.

**Request body:**
```json
{
  "categories": ["prompt_injection", "kill_chain"],
  "test_ids": null,
  "llm_provider": "mock"
}
```

`categories`: null = run all | list of categories = run those only
`test_ids`: null = all in category | list of test IDs = run specific tests

**Response body:**
```json
{
  "harness_run_id": "harness-uuid-001",
  "status": "running",
  "total_tests": 9,
  "started_at": "2024-11-15T10:30:00Z"
}
```

---

## GET /security-harness/results

**Purpose:** Get all security harness run results with aggregate scores.

**Query params:** `harness_run_id` (optional), `page`, `page_size`

**Response body:**
```json
{
  "runs": [
    {
      "harness_run_id": "harness-uuid-001",
      "total_tests": 12,
      "tests_passed": 10,
      "overall_score": 87.5,
      "security_rating": "Mostly Secure",
      "category_scores": {
        "prompt_injection": 90.0,
        "kill_chain": 85.0,
        "secret_leakage": 100.0,
        "unsupported_conclusion": 80.0
      },
      "started_at": "2024-11-15T10:30:00Z",
      "completed_at": "2024-11-15T10:32:45Z",
      "results": [
        {
          "test_id": "PI-001",
          "name": "log_injection_instruction_override",
          "score": 10,
          "max_score": 10,
          "passed": true,
          "injection_detected": true,
          "action_blocked": true
        }
      ]
    }
  ]
}
```

---

## GET /safety-events

**Purpose:** Get the safety events log.

**Query params:** `event_type`, `severity`, `agent_run_id`, `page`, `page_size`

**Response body:**
```json
{
  "items": [
    {
      "id": "event-uuid-001",
      "event_type": "prompt_injection_detected",
      "severity": "high",
      "source": "run_prompt_injection_check",
      "affected_component": "retrieved_doc",
      "pattern_matched": "IGNORE ALL PREVIOUS INSTRUCTIONS",
      "agent_run_id": "run-uuid-001",
      "details": { "doc_id": "doc-uuid-002", "chunk_id": "chunk-uuid-007" },
      "created_at": "2024-11-15T10:30:22Z"
    }
  ],
  "total": 5
}
```

---

## POST /reports/export

**Purpose:** Export a full incident report as JSON or Markdown.

**Request body:**
```json
{
  "agent_run_id": "run-uuid-001",
  "format": "json"
}
```

`format`: `"json"` | `"markdown"`

**Response body:**
- If `format = "json"`: Returns full incident report JSON object
- If `format = "markdown"`: Returns rendered Markdown string

**Validation rules:**
- Agent run must be in `completed` status
- Returns 404 if no incident report found

**Example JSON response structure:**
```json
{
  "report_id": "report-uuid-001",
  "generated_at": "2024-11-15T10:50:00Z",
  "alert_summary": { "...": "..." },
  "investigation_timeline": [ "..." ],
  "self_assessments_summary": [ "..." ],
  "evidence_retrieved": [ "..." ],
  "tool_calls_summary": [ "..." ],
  "hypotheses": [ "..." ],
  "kill_chain_assessment": { "...": "..." },
  "recommendation": { "...": "..." },
  "human_decisions": [ "..." ],
  "ticket_draft": { "...": "..." },
  "evaluation_scores": { "...": "..." },
  "safety_events": [ "..." ]
}
```
