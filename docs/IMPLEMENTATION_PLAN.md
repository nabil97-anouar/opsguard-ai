# IMPLEMENTATION_PLAN.md — OpsGuard AI Milestones for Codex

## Overview

This plan breaks the project into 11 milestones, each independently testable. Milestones are ordered by dependency. Do not implement components from later milestones early — each milestone has a clear stopping point.

Estimated total: 2–4 weeks of focused development (1 developer).

---

## Milestone 1: Repository Scaffold

### Objective
Create the complete project skeleton with all directories, config files, Docker Compose, environment setup, and empty module stubs. After this milestone, the repo is cloneable and bootable (even if most endpoints return 501).

### Files to Create

```
opsguard-ai/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app + router registration + CORS
│   │   ├── config.py            # Settings from pydantic-settings
│   │   ├── database.py          # SQLModel engine, create_all, get_session
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── health.py        # GET /health
│   │   │   ├── demo.py          # POST /demo/seed (stub)
│   │   │   ├── alerts.py        # stub
│   │   │   ├── documents.py     # stub
│   │   │   ├── rag.py           # stub
│   │   │   ├── agent_runs.py    # stub
│   │   │   ├── feedback.py      # stub
│   │   │   ├── security_harness.py # stub
│   │   │   ├── safety_events.py # stub
│   │   │   └── reports.py       # stub
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   └── __init__.py
│   │   ├── services/
│   │   │   └── __init__.py
│   │   ├── agent/
│   │   │   └── __init__.py
│   │   ├── rag/
│   │   │   └── __init__.py
│   │   ├── tools/
│   │   │   └── __init__.py
│   │   ├── harness/
│   │   │   └── __init__.py
│   │   └── evaluation/
│   │       └── __init__.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx         # Landing page stub
│   │   │   └── dashboard/
│   │   │       └── page.tsx     # Dashboard stub
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui components
│   │   │   └── layout/
│   │   │       ├── Sidebar.tsx
│   │   │       └── Header.tsx
│   │   └── lib/
│   │       ├── api.ts           # Typed API client stubs
│   │       └── utils.ts
│
├── demo_data/
│   ├── runbooks/
│   │   └── .gitkeep
│   ├── incident_reports/
│   │   └── .gitkeep
│   └── security_policies/
│       └── .gitkeep
│
└── docs/
    └── (all 12 spec documents)
```

### Expected Output
- `docker-compose up` starts postgres, qdrant, backend, frontend without errors
- `GET /health` returns `{"status": "healthy"}`
- Frontend loads at `localhost:3000` showing a placeholder page
- All other endpoints return `501 Not Implemented`

### Tests / Checks
- `docker-compose up --build` completes without errors
- `curl localhost:8000/api/v1/health` returns 200
- `curl localhost:3000` returns 200
- `pytest backend/tests/test_health.py` passes

### Stopping Point for Codex
Stop after all stubs are created, Docker boots, and health check passes. Do not add business logic.

### Common Mistakes to Avoid
- Do not install LangGraph or LlamaIndex yet — use stubs
- Do not create database tables yet — that is Milestone 2
- Do not implement any LLM calls — that is Milestone 6
- Keep docker-compose ports consistent with `.env.example`

---

## Milestone 2: Backend + Database Models

### Objective
Implement all SQLModel table definitions, Pydantic schemas, database migrations (or create_all), and basic CRUD for alerts and documents. Backend can now persist and retrieve data.

### Files to Create / Modify

```
backend/app/models/
├── alert.py          # Alert, Incident SQLModel tables
├── document.py       # Document, DocumentChunk tables
├── agent.py          # AgentRun, AgentStep tables
├── assessment.py     # SelfAssessment table
├── tools.py          # ToolCall table
├── safety.py         # SafetyEvent table
├── kill_chain.py     # KillChainMapping table
├── feedback.py       # HumanFeedback table
├── evaluation.py     # EvaluationScore table
├── ticket.py         # TicketDraft table
├── harness.py        # SecurityHarnessTest, SecurityHarnessResult tables
└── __init__.py       # imports all models for create_all

backend/app/schemas/
├── alert.py          # AlertCreate, AlertRead, AlertList Pydantic schemas
├── document.py
├── agent_run.py
└── ...               # one schema file per domain

backend/app/routers/alerts.py     # GET /alerts, POST /alerts (CRUD only, no agent)
backend/app/routers/documents.py  # GET /documents

backend/tests/
├── test_models.py    # Create and query each table
└── test_alerts_crud.py
```

### Expected Output
- All 15 tables created in PostgreSQL on startup
- `POST /alerts` creates an alert record
- `GET /alerts` returns paginated list
- `GET /documents` returns empty list (no ingestion yet)

### Tests / Checks
- `pytest backend/tests/test_models.py` — all tables create without error
- `pytest backend/tests/test_alerts_crud.py` — CRUD operations pass
- No SQLModel relationship errors

### Stopping Point for Codex
Stop after CRUD endpoints work for alerts and documents. Do not implement agent, RAG, or ingestion.

### Common Mistakes to Avoid
- Use UUIDs as primary keys (not integers)
- Use `TIMESTAMPTZ` for all timestamps
- Use JSONB for `raw_data`, `metadata`, `details` fields
- Do not use `relationship` lazy loading without explicit `selectin` — use explicit queries instead
- Keep `is_demo` field on all main tables for easy demo data cleanup

---

## Milestone 3: Demo Data Generator

### Objective
Build the seed script that populates the database with realistic demo data — alerts, runbook documents, past incident reports, pre-computed agent run traces, and security harness results. This is critical for the portfolio demo.

### Files to Create

```
backend/app/scripts/
└── seed_demo.py      # Main seed script

demo_data/
├── runbooks/
│   ├── gpu_memory_overflow.md
│   ├── node_unreachable.md
│   ├── slurm_job_failure.md
│   ├── network_latency_spike.md
│   ├── security_anomaly_response.md
│   └── disk_quota_exceeded.md
│
├── incident_reports/
│   ├── incident_2024_gpu_ecc_node02.md
│   ├── incident_2024_slurm_scheduler_hang.md
│   └── incident_2024_network_intrusion_attempt.md
│
└── security_policies/
    ├── access_control_policy.md
    └── incident_response_policy.md

backend/app/routers/demo.py      # POST /demo/seed endpoint
backend/tests/test_seed.py
```

### Demo Alert Scenarios (create at least these 10)

| # | Title | Severity | Type | Infra |
|---|---|---|---|---|
| 1 | GPU memory overflow node-04 GPU-3 | critical | gpu_memory_overflow | gpu_cluster |
| 2 | Slurm scheduler not responding | error | slurm_scheduler_hang | hpc |
| 3 | Node-12 unreachable via SSH | error | node_unreachable | hpc |
| 4 | Suspicious outbound connection from node-07 | critical | security_anomaly | security |
| 5 | High GPU temperature warning node-02 GPU-0 | warning | gpu_thermal | gpu_cluster |
| 6 | Disk quota exceeded on /scratch | warning | disk_quota | hpc |
| 7 | Network latency spike on infiniband fabric | error | network_latency | hpc |
| 8 | Failed authentication attempts on login node | warning | auth_failure | security |
| 9 | Cloud VM instance health check failing | error | vm_health | cloud |
| 10 | CUDA out-of-memory errors in training job | error | cuda_oom | gpu_cluster |

Each alert should have a realistic `raw_data` JSON payload and a `ground_truth_root_cause` field.

### Expected Output
- `POST /demo/seed` runs in < 15 seconds
- All 15+ demo documents ingested into PostgreSQL
- 10+ demo alerts created with realistic data
- At least 3 pre-built agent run traces visible in DB

### Tests / Checks
- `pytest backend/tests/test_seed.py` passes
- `GET /alerts?is_demo=true` returns 10+ alerts
- `GET /documents?is_demo=true` returns 15+ documents

### Stopping Point for Codex
Stop after seed data is in the database. Do not implement actual RAG ingestion pipeline yet (that is M4). Documents at this stage are stored as text in PostgreSQL but NOT in Qdrant.

### Common Mistakes to Avoid
- Make seed idempotent — clear `is_demo=true` records before re-seeding
- Ensure demo documents have varied `infrastructure_type` tags
- Include at least one document with an injection pattern (for harness demo)
- Do not hardcode random UUIDs — generate them dynamically

---

## Milestone 4: RAG Ingestion and Retrieval

### Objective
Implement the full RAG pipeline: document chunking, embedding, Qdrant storage, hybrid retrieval, reranking, and citation building. Demo documents should now be queryable via RAG.

### Files to Create

```
backend/app/rag/
├── __init__.py
├── ingestor.py        # Document → chunks → embed → Qdrant
├── chunker.py         # Heading-aware chunker
├── embedder.py        # Pluggable embedder (local or OpenAI)
├── retriever.py       # Hybrid retrieval (dense + sparse + RRF)
├── reranker.py        # Optional cross-encoder reranker
├── citations.py       # Citation builder
└── injection_scanner.py  # Pre-LLM injection pattern scanner

backend/app/routers/
├── documents.py       # POST /documents/ingest (now real)
└── rag.py             # POST /rag/retrieve (now real)

backend/tests/
├── test_ingestion.py
└── test_retrieval.py
```

### Expected Output
- `POST /documents/ingest` uploads, chunks, embeds, and stores in Qdrant
- `POST /rag/retrieve` returns relevant chunks with citations
- Injection scanner correctly flags test documents with injection patterns
- Re-running `POST /demo/seed` now also ingests documents into Qdrant

### Tests / Checks
- `pytest backend/tests/test_ingestion.py` — ingest 3 test docs, verify chunk count
- `pytest backend/tests/test_retrieval.py` — verify top-1 result is correct for known query
- Verify injection scanner flags a document containing "IGNORE ALL PREVIOUS INSTRUCTIONS"
- `GET /documents` shows `injection_scan_result: "flagged"` for poisoned doc

### Stopping Point for Codex
Stop after retrieval works end-to-end. Do not integrate RAG into the agent yet — that is M6.

### Common Mistakes to Avoid
- Use the same embedding model for ingestion and retrieval (must match)
- Wrap all retrieved text in UNTRUSTED delimiters immediately in `retriever.py`
- Do not pass retrieved text to any LLM in this milestone — just verify retrieval quality
- Handle Qdrant connection errors gracefully — log and return empty results

---

## Milestone 5: MCP-Style Tool Registry

### Objective
Implement the typed, allowlisted, audited tool registry. All 7 safe tools fully implemented with mock handlers. Dangerous action definitions in place but non-executable.

### Files to Create

```
backend/app/tools/
├── __init__.py
├── registry.py          # TOOL_ALLOWLIST, execute_tool(), audit_log()
├── schemas.py           # Input/output Pydantic schemas for all tools
├── handlers/
│   ├── __init__.py
│   ├── search_logs.py
│   ├── get_node_metrics.py
│   ├── get_running_jobs.py
│   ├── check_network_connections.py
│   ├── query_past_incidents.py
│   ├── retrieve_runbook.py
│   └── create_ticket_draft.py
├── mock_handlers/       # Demo/test mock data for each tool
│   ├── __init__.py
│   └── mock_data.py     # Realistic mock responses keyed by node_id
└── dangerous_actions.py # Definitions only, no handlers

backend/tests/
└── test_tool_registry.py
```

### Expected Output
- `execute_tool("search_logs", {...})` returns schema-validated mock data
- All tool calls logged to `tool_calls` table
- Calling a non-allowlisted tool raises `ToolNotAllowedError`
- Calling `cancel_job` raises `DangerousActionError` ("use recommendations only")
- Input validation rejects malformed args before execution

### Tests / Checks
- `pytest backend/tests/test_tool_registry.py`
- All 7 tools execute without error in mock mode
- Allowlist enforcement blocks 5 dangerous tools
- Tool call record created in DB for each execution
- Input with shell metacharacters in `node_id` is rejected

### Stopping Point for Codex
Stop after all tools work in mock mode. Do not integrate into agent yet.

### Common Mistakes to Avoid
- Never add shell execution to any handler
- Mock data should be keyed by node_id (e.g., `"gpu-node-04"`) for realistic demo consistency
- Log audit record BEFORE returning output, not after — so a handler crash still logs the attempt
- Validate both input AND output schemas

---

## Milestone 6: Agent Workflow + Metacognitive Self-Assessment

### Objective
Implement the full 15-node agent workflow with a mock LLM. The mock LLM returns pre-scripted, realistic responses. Each node fully implemented. Metacognitive self-assessment computes real confidence scores.

### Files to Create

```
backend/app/agent/
├── __init__.py
├── runner.py            # Graph runner: executes nodes in order, manages state
├── state.py             # AgentState TypedDict definition
├── nodes/
│   ├── __init__.py
│   ├── ingest_alert.py
│   ├── classify_alert.py
│   ├── metacognitive_self_assessment.py
│   ├── retrieve_context.py
│   ├── map_to_ai_kill_chain.py
│   ├── plan_tool_calls.py
│   ├── execute_safe_tools.py
│   ├── synthesize_hypotheses.py
│   ├── evaluate_evidence_grounding.py
│   ├── run_prompt_injection_check.py
│   ├── run_watchdog_policy_check.py
│   ├── generate_recommendation.py
│   ├── wait_for_human_approval.py
│   ├── create_ticket_draft.py
│   └── produce_incident_report.py
├── llm/
│   ├── __init__.py
│   ├── base.py          # LLMProvider abstract class
│   ├── mock.py          # MockLLMProvider with pre-scripted responses
│   └── openai.py        # OpenAIProvider (stub, activates when OPENAI_API_KEY set)
└── metacognition.py     # Confidence scoring logic

backend/app/routers/agent_runs.py   # All agent run endpoints (now real)
backend/tests/
├── test_agent_runner.py
└── test_metacognition.py
```

### Mock LLM Design
The mock LLM maps `(alert_type, node_name)` → pre-scripted response. This makes demo runs deterministic and fast. Responses are in `backend/app/agent/llm/mock_responses/` as JSON files per scenario.

### Expected Output
- `POST /alerts/{id}/investigate` triggers full 15-node workflow
- `GET /agent-runs/{run_id}/trace` returns all 15 steps
- `GET /agent-runs/{run_id}/self-assessments` returns 2 assessment records
- Mock workflow completes in < 3 seconds
- Human approval correctly pauses at `wait_for_human_approval` for high-risk runs
- `POST /agent-runs/{run_id}/approve` resumes workflow

### Tests / Checks
- `pytest backend/tests/test_agent_runner.py` — full workflow for 3 alert types
- Self-assessment confidence scores change between first and second call
- Dangerous actions appear only in recommendations, not in tool calls
- Injection check runs before recommendation
- Watchdog runs twice (before tools, before recommendation)

### Stopping Point for Codex
Stop after full workflow runs with mock LLM for at least 3 different alert types.

### Common Mistakes to Avoid
- Keep the graph runner explicit and readable — avoid magic abstractions
- The state object must be immutable per node — each node returns a new state dict
- Run the workflow as a background task (`asyncio.create_task`) — do not block the HTTP response
- Metacognitive assessment must actually compute confidence from evidence, not just return a hardcoded value
- Do not skip the injection check or watchdog under any circumstances

---

## Milestone 7: Watchdog / Safety Layer

### Objective
Implement the watchdog policy engine as a first-class module. It should be independently testable and observable.

### Files to Create

```
backend/app/agent/
├── watchdog.py          # WatchdogEngine: policy checks, safety gates
└── injection_checker.py # Injection pattern scanner (reused from RAG)

backend/tests/
└── test_watchdog.py
```

### Policies to Implement
1. Dangerous action gate (cancel_job, drain_node, etc. → human approval)
2. Allowlist gate (tool not in allowlist → blocked)
3. Confidence gate (severity=critical + confidence < 0.5 → human approval)
4. Injection gate (injection_detected → human approval)
5. Evidence gate (grounding_score < 0.3 on critical → stop)
6. Loop prevention (same tool called > 3 times → blocked)
7. Bulk operation gate (>5 nodes targeted → blocked)

### Expected Output
- Each policy gate independently testable
- Safety events created for every violation
- Watchdog decisions logged with policy name and rationale

### Tests / Checks
- `pytest backend/tests/test_watchdog.py` — test each of 7 policies
- Verify safety events created for blocked actions
- Verify injection gate triggers correctly

### Stopping Point for Codex
Stop after all 7 policies are tested. Watchdog is already integrated into M6 agent workflow.

---

## Milestone 8: Security Harness

### Objective
Implement the security harness as a standalone module. Load test scenarios from YAML, run them against the agent pipeline, score results.

### Files to Create

```
backend/app/harness/
├── __init__.py
├── runner.py            # HarnessRunner: load tests, inject payloads, run, score
├── scenarios/           # YAML test scenario definitions
│   ├── prompt_injection.yaml
│   ├── kill_chain.yaml
│   ├── secret_leakage.yaml
│   └── unsupported_conclusion.yaml
├── injector.py          # Payload injection into specific pipeline points
├── evaluator.py         # Compare actual output vs expected behavior
└── scorer.py            # Score computation per test

backend/app/routers/security_harness.py   # POST /security-harness/run (now real)
backend/tests/
└── test_harness.py
```

### Expected Output
- `POST /security-harness/run` executes all 12 tests
- All tests produce scored results stored in DB
- Injection scenarios score 10/10 (agent blocks them all)
- Results display in `GET /security-harness/results`
- Safety events created for each detected attack

### Tests / Checks
- `pytest backend/tests/test_harness.py`
- PI-001 through PI-003: injection detected in each test
- KCA-004: dangerous actions held for approval
- SL-001: no system prompt content in output
- UC-001: agent correctly states insufficient evidence

### Stopping Point for Codex
Stop after all 12 harness tests run and produce scores.

---

## Milestone 9: Frontend Dashboard

### Objective
Build all frontend pages. API is now complete from M6+M7+M8. Focus on impressive visual design.

### File Groups

```
frontend/src/app/
├── page.tsx                # Landing page (complete)
├── dashboard/page.tsx      # Dashboard (complete)
├── alerts/
│   ├── page.tsx            # Alert list
│   └── [id]/
│       ├── page.tsx        # Alert detail
│       ├── trace/page.tsx
│       ├── self-assessment/page.tsx
│       ├── tools/page.tsx
│       ├── evidence/page.tsx
│       ├── kill-chain/page.tsx
│       └── approve/page.tsx
├── safety/page.tsx
├── harness/
│   ├── page.tsx
│   └── [run_id]/page.tsx
├── evaluation/page.tsx
└── reports/page.tsx

frontend/src/components/
├── alerts/
│   ├── AlertTable.tsx
│   ├── SeverityBadge.tsx
│   └── AlertStatusBadge.tsx
├── trace/
│   ├── TraceTimeline.tsx
│   └── TraceNode.tsx
├── assessment/
│   ├── SelfAssessmentCard.tsx
│   └── ConfidenceGauge.tsx
├── tools/
│   └── ToolCallItem.tsx
├── evidence/
│   └── EvidenceCard.tsx
├── kill-chain/
│   └── KillChainMap.tsx
├── harness/
│   ├── HarnessScoreCard.tsx
│   └── TestResultCard.tsx
├── approval/
│   └── ApprovalPanel.tsx
└── evaluation/
    └── MetricCard.tsx
```

### Expected Output
- All pages load with demo data
- Trace timeline animated with real step data
- Self-assessment cards show confidence gauges
- Harness page shows 87.5 score with all tests
- Approval panel works for pending runs
- Dashboard shows live stats

### Stopping Point for Codex
Stop after all pages are visually complete with demo data. Do not work on mobile responsiveness — desktop only for portfolio.

---

## Milestone 10: Evaluation + Report Export

### Objective
Implement the evaluation engine (computing scores per run) and the incident report export.

### Files to Create

```
backend/app/evaluation/
├── __init__.py
├── engine.py         # EvaluationEngine: compute all metrics
├── metrics/
│   ├── grounding.py
│   ├── safety.py
│   ├── calibration.py
│   └── aggregate.py

backend/app/routers/reports.py    # POST /reports/export (now real)
frontend/src/app/evaluation/page.tsx  # Evaluation dashboard (complete)
```

### Expected Output
- Every completed agent run has evaluation scores in DB
- Evaluation panel shows radar chart and metric cards
- `POST /reports/export` returns valid JSON and Markdown

### Stopping Point for Codex
Stop after evaluation scores compute and export works.

---

## Milestone 11: Portfolio Polish

### Objective
Final polish for GitHub, Upwork, and demo video. Not new features.

### Tasks

1. **README.md** — Project overview, architecture diagram, setup instructions, demo instructions, screenshots
2. **Screenshots** — Take screenshots of 6 key pages, save to `docs/screenshots/`
3. **Demo seed quality** — Verify all demo scenarios look impressive and realistic
4. **.env.example** — Complete and documented
5. **Docker Compose** — Verify clean start from scratch
6. **Mock LLM parity** — Ensure mock responses produce good-looking evaluation scores
7. **Landing page** — Final polish, screenshots, tech badges
8. **GitHub topics** — Add all relevant topics

### Stopping Point
This is the final milestone. Project is complete.

---

## Dependency Graph

```
M1 (scaffold)
  └─ M2 (database)
       └─ M3 (demo data)
            ├─ M4 (RAG)
            └─ M5 (tools)
                 └─ M6 (agent workflow)  ← depends on M4 + M5
                      ├─ M7 (watchdog)   ← integrated into M6
                      ├─ M8 (harness)    ← depends on M6 + M7
                      └─ M9 (frontend)   ← depends on M6 + M7 + M8
                           └─ M10 (evaluation + export)
                                └─ M11 (polish)
```
