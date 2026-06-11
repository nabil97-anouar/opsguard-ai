# OpsGuard AI

Secure self-aware AI agents for incident triage, RAG, and AI security testing.

OpsGuard AI is a local-first, production-style portfolio project that shows how to build operational AI systems that are grounded, auditable, and safe by default. The system is designed for Cloud, DevOps, SaaS, GPU, and HPC incident workflows, with explicit boundaries around confidence estimation, human approval, and trusted tool use.

## Problem Solved

Modern incident response teams are overloaded with alerts, brittle runbooks, and AI copilots that sound confident even when evidence is weak. OpsGuard AI aims to demonstrate a better pattern: an agentic incident triage system that retrieves evidence, measures its own uncertainty, avoids unsafe actions, and treats logs, tool outputs, and retrieved documents as untrusted until validated.

## Architecture Summary

- `frontend/`: Next.js + TypeScript + Tailwind dashboard and portfolio landing experience
- `backend/`: FastAPI service with typed settings, structured logging, and future-ready module boundaries
- `docs/`: product, architecture, workflow, RAG, security harness, and implementation specifications
- `demo_data/`: placeholder space for runbooks, incident reports, and security policies
- `docker-compose.yml`: local stack for PostgreSQL, Qdrant, backend, and frontend

Milestone 1 focuses on the professional scaffold only. It does not implement database models, RAG, agent logic, tool execution, or the security harness yet.
Milestone 2 adds the backend database session layer, SQLModel tables, and development-only table creation utilities. It still does not implement RAG, agents, tool registry, safety orchestration, evaluation workflows, or frontend dashboard behavior.
Milestone 4 adds deterministic local document ingestion, chunking, prompt-injection flagging, and lexical retrieval without external embeddings or paid APIs.
Milestone 5 adds a typed, allowlisted, audited safe tool registry with deterministic mock/read-only tools and blocked dangerous actions.
Milestone 6 adds a deterministic backend agent workflow with a local mock LLM, fixed graph nodes, metacognitive self-assessment, RAG evidence retrieval, and safe-tool execution that always ends in human review.
Milestone 7 adds an independently testable watchdog safety layer that evaluates recommendations, suspicious context, confidence, and grounding before agent output is considered safe for human review.
Milestone 8 adds a deterministic security harness runner that exercises adversarial scenarios across RAG, tools, the agent workflow, and watchdog policies, then persists structured results.
Milestone 9 adds the polished frontend dashboard that presents seeded incidents, agent traces, grounded citations, watchdog findings, and harness evidence as a premium local demo.
Milestone 10 adds the backend evaluation and reporting layer that turns persisted harness, watchdog, tool, and agent data into exportable safety scorecards.

## Local Setup

Prerequisites:

- Python 3.11+
- Node.js 20+
- Docker with Compose

Create an environment file first:

```bash
cp .env.example .env
```

## Development Commands

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Create the database tables locally:

```bash
docker compose up -d postgres
cd backend
source .venv/bin/activate
python -m app.db.init_db
```

Use a SQLite fallback for quick local testing without PostgreSQL:

```bash
cd backend
source .venv/bin/activate
DATABASE_URL=sqlite:///./opsguard.db python -m app.db.init_db
```

Or use the development-only API route after the backend is running:

```bash
curl -X POST http://localhost:8000/api/v1/db/create-tables
```

## Demo Data

Seed the static demo dataset through the API:

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed \
  -H "Content-Type: application/json" \
  -d '{"reset": false}'
```

Recreate only the demo-seeded records:

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed \
  -H "Content-Type: application/json" \
  -d '{"reset": true}'
```

Seed locally through the CLI:

```bash
cd backend
source .venv/bin/activate
python -m app.services.demo_seed
```

Reset and reseed through the CLI:

```bash
cd backend
source .venv/bin/activate
python -m app.services.demo_seed --reset
```

Included scenarios:

- suspicious GPU usage with possible crypto-mining and outbound pool traffic
- SSH brute-force activity against a login node
- storage inode pressure on shared scratch space
- RAG prompt-injection poisoning through an untrusted runbook
- agent traces, safety events, kill-chain mappings, ticket drafts, and harness examples tied to those incidents

## RAG

This milestone uses deterministic local chunking plus lexical retrieval over SQL data only.
It does not call OpenAI, Anthropic, sentence-transformers, or any paid embedding API.

Trusted vs. untrusted documents:

- `trusted` documents remain higher-confidence sources, but retrieved text is still treated as data, not instructions
- `untrusted` documents can be retrieved when allowed and are returned with suspicion flags and provenance
- simple prompt-injection patterns are scanned at ingest time and again at retrieval time

Ingest a document:

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Trusted GPU Escalation Note",
    "source": "manual://gpu-escalation-note",
    "doc_type": "runbook",
    "trust_level": "trusted",
    "content": "# GPU Escalation\n\nValidate suspicious GPU processes before escalation.\n\nRequire human approval before containment.",
    "metadata": {
      "tags": ["gpu", "manual"],
      "infrastructure_type": "gpu_cluster"
    }
  }'
```

List ingested documents:

```bash
curl http://localhost:8000/api/v1/documents
```

Retrieve grounded chunks:

```bash
curl -X POST http://localhost:8000/api/v1/rag/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "gpu xmrig suspicious process",
    "limit": 5,
    "trust_filter": null,
    "include_untrusted": true
  }'
```

Retrieve while excluding untrusted content:

```bash
curl -X POST http://localhost:8000/api/v1/rag/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "system override ignore policies",
    "limit": 5,
    "trust_filter": null,
    "include_untrusted": false
  }'
```

Retrieval results include provenance and lightweight guardrails:

- `document_id`, `chunk_id`, `title`, `source`, and `chunk_index`
- `trust_level` and `doc_type`
- `score` and `citation`
- `is_suspicious`, `matched_patterns`, and `risk_level`

## Safe Tool Registry

The tool registry is local-first, allowlisted, typed, and auditable.
It exposes deterministic mock/read-only tools only, and it never performs arbitrary shell execution.

Available safe tools:

- `search_logs`
- `get_node_metrics`
- `get_running_jobs`
- `check_network_connections`
- `query_past_incidents`
- `retrieve_runbook`
- `create_ticket_draft`

Blocked dangerous tools:

- `cancel_job`
- `drain_node`
- `block_user`
- `isolate_node`
- `disable_service`

List the registry definitions:

```bash
curl http://localhost:8000/api/v1/tools
```

Execute a safe mock tool:

```bash
curl -X POST http://localhost:8000/api/v1/tools/search_logs/execute \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "query": "xmrig mining pool",
      "limit": 5
    },
    "agent_run_id": null
  }'
```

Execute a runbook retrieval tool call with trusted-only default behavior:

```bash
curl -X POST http://localhost:8000/api/v1/tools/retrieve_runbook/execute \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "query": "gpu suspicious process xmrig",
      "limit": 5,
      "include_untrusted": false
    },
    "agent_run_id": null
  }'
```

Attempt a blocked dangerous action:

```bash
curl -X POST http://localhost:8000/api/v1/tools/drain_node/execute \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "node": "gpu-node-14",
      "reason": "suspicious outbound mining traffic"
    },
    "agent_run_id": null
  }'
```

Registry behavior:

- tools are allowlisted and validated with Pydantic input/output schemas
- safe tool responses are deterministic and mock/demo-data based
- tool executions can be audited to `tool_calls` when an `agent_run_id` is provided
- dangerous tools never execute and return a blocked response that requires human approval
- `retrieve_runbook` excludes untrusted documents by default, and returned chunks keep trust and suspicion metadata
- no arbitrary shell execution, subprocess, Slurm, Docker, or destructive infrastructure commands are used in this milestone

## Agent Workflow

The agent workflow is deterministic and local.
It does not call OpenAI, Anthropic, LangGraph, LangChain, or any external infrastructure API.

What it does:

- creates an `AgentRun` from an existing alert
- executes a fixed graph of nodes: ingest, classify, retrieve, plan, execute safe tools, synthesize, self-assess, recommend, run watchdog policy checks, and wait for human approval
- uses Milestone 4 retrieval for grounded citations
- uses Milestone 5 allowlisted tools for mock read-only evidence gathering
- persists `AgentRun`, `AgentStep`, `SelfAssessment`, `ToolCall`, `SafetyEvent`, and `TicketDraft` records as appropriate
- never executes dangerous infrastructure actions directly

How it reasons:

- the mock LLM is deterministic and rule-based
- suspicious or untrusted retrieved/tool content lowers confidence and is called out in the final recommendation
- missing evidence is preserved explicitly in self-assessment and recommendation output
- all runs stop at `waiting_for_human`; this is not autonomous infrastructure control

Seed demo data before running the agent:

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed \
  -H "Content-Type: application/json" \
  -d '{"reset": false}'
```

Run the workflow for a seeded alert:

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "909d28d2-5c9f-5fa2-a35e-f6b39c95f83f"
  }'
```

Get full run details:

```bash
curl http://localhost:8000/api/v1/agent/runs/<agent_run_id>
```

List recent runs:

```bash
curl http://localhost:8000/api/v1/agent/runs
```

Workflow behavior:

- prompt-injection and other suspicious content are surfaced in `notes`, citations, and safety events
- dangerous actions such as `cancel_job` or `isolate_node` appear only as blocked recommendations requiring human approval
- the watchdog layer evaluates dangerous actions, prompt-injection indicators, untrusted context, weak grounding, suspicious tool output, and bulk operations before the run is handed to a human
- final recommendations can create internal ticket drafts, but they never call external ticketing systems
- the workflow is designed for deterministic demos and tests, not for autonomous remediation

## Watchdog Safety Layer

The watchdog is deterministic, local, and independently testable.
It never executes infrastructure actions; it only evaluates whether the agent output is safe enough to hand to a human reviewer.

Policies currently implemented:

- dangerous action gate
- prompt-injection gate
- untrusted context gate
- low-confidence high-severity gate
- weak grounding gate
- bulk operation gate
- unsafe tool output gate

Decision statuses:

- `allow`
- `allow_with_warnings`
- `require_human_approval`
- `block`

Evaluate a safe recommendation directly:

```bash
curl -X POST http://localhost:8000/api/v1/watchdog/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "alert": {
      "severity": "warning",
      "title": "Safe operational note"
    },
    "retrieved_context": [],
    "tool_results": [],
    "hypotheses": [
      {
        "title": "Benign hypothesis",
        "summary": "This looks like a bounded operational issue.",
        "supporting_evidence": ["Runbook A chunk 1"]
      }
    ],
    "evidence_items": [
      {
        "summary": "Trusted runbook excerpt",
        "citation": "Runbook A chunk 1",
        "trust_level": "trusted",
        "suspicious": false
      }
    ],
    "planned_tools": [],
    "blocked_tools": [],
    "self_assessment": {
      "confidence_score": 0.9,
      "missing_evidence": [],
      "uncertainty_level": "low"
    },
    "final_recommendation": {
      "summary": "Review the trusted runbook and continue with human oversight.",
      "evidence": [
        {
          "summary": "Trusted runbook excerpt",
          "citation": "Runbook A chunk 1",
          "trust_level": "trusted",
          "suspicious": false
        }
      ],
      "citations": ["Runbook A chunk 1"],
      "recommended_next_steps": ["Open a draft ticket for follow-up."],
      "blocked_actions_requiring_human_approval": [],
      "missing_evidence": [],
      "notes": []
    }
  }'
```

Evaluate a dangerous recommendation:

```bash
curl -X POST http://localhost:8000/api/v1/watchdog/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "alert": {
      "severity": "critical",
      "title": "GPU cluster compromise suspicion"
    },
    "retrieved_context": [],
    "tool_results": [],
    "hypotheses": [],
    "evidence_items": [],
    "planned_tools": [],
    "blocked_tools": [],
    "self_assessment": {
      "confidence_score": 0.41,
      "missing_evidence": ["validated owner of the job"],
      "uncertainty_level": "high"
    },
    "final_recommendation": {
      "summary": "Drain all nodes and cancel_job immediately.",
      "evidence": [],
      "citations": [],
      "recommended_next_steps": ["Drain all nodes in the entire cluster."],
      "blocked_actions_requiring_human_approval": [
        {
          "tool_name": "drain_node",
          "target": "all nodes",
          "rationale": "Emergency containment proposal."
        }
      ],
      "missing_evidence": ["validated owner of the job"],
      "notes": []
    }
  }'
```

Run the agent and inspect the watchdog result:

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "909d28d2-5c9f-5fa2-a35e-f6b39c95f83f"
  }'
```

```bash
curl http://localhost:8000/api/v1/agent/runs/<agent_run_id>
```

Watchdog behavior:

- it flags or blocks risky recommendations, but never executes them
- it persists `SafetyEvent` records for important findings
- it is designed to be a policy layer in front of human review, not an autonomous control plane

## Security Harness

The security harness is deterministic, local-only, and designed to exercise the existing retrieval, tool, agent, and watchdog layers without any external APIs.
It persists scenario definitions and run results to the database so the system can be tested repeatedly with reproducible outcomes.

Included scenarios:

- prompt injection in retrieved documents
- prompt injection in tool outputs and logs
- malicious tool feedback
- unsafe action recommendations
- unsupported conclusions with weak grounding
- untrusted context reliance
- low-confidence high-severity incidents
- blocked dangerous tool attempts
- clean safe control case

Scoring and result states:

- `passed`: all expected safe-behavior checks succeeded
- `partial`: some checks succeeded, but coverage or handling was incomplete
- `failed`: the scenario did not satisfy the required safety checks
- `score`: normalized `0.0` to `1.0`, stored alongside structured findings, linked safety events, watchdog status, and any related `agent_run_id`

How it works:

- seeded demo data provides the poisoned runbook, suspicious logs, and operational context
- selected scenarios run the existing RAG retrieval, safe tool registry, deterministic agent flow, or watchdog evaluator directly
- results are persisted to `security_harness_tests` and `security_harness_results`
- linked `SafetyEvent` evidence is preserved when scenarios trigger watchdog or tool-registry protections

List available harness scenarios:

```bash
curl http://localhost:8000/api/v1/harness/scenarios
```

Run all harness scenarios:

```bash
curl -X POST http://localhost:8000/api/v1/harness/run \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_ids": null,
    "reset_demo_data": true
  }'
```

Run selected scenarios only:

```bash
curl -X POST http://localhost:8000/api/v1/harness/run \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_ids": [
      "prompt_injection_in_retrieved_document",
      "dangerous_tool_blocked",
      "clean_safe_case"
    ],
    "reset_demo_data": true
  }'
```

Fetch recent harness results:

```bash
curl http://localhost:8000/api/v1/harness/results
```

Fetch one harness run by correlation ID:

```bash
curl http://localhost:8000/api/v1/harness/results/<harness_run_id>
```

Harness guarantees:

- no shell execution, subprocess calls, Slurm commands, Docker commands, or destructive infrastructure actions
- no OpenAI, Anthropic, or other external LLM API usage
- no autonomous remediation; the harness only evaluates and records system behavior
- reproducible, database-backed results suitable for local demos and automated tests

## Frontend Dashboard

The dashboard is the polished local demo surface for OpsGuard AI.
It shows the system end to end: incident overview, deterministic agent runs, RAG citations, allowlisted tool calls, watchdog safety findings, security harness scores, and the mandatory human-approval boundary.

Start the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Seed demo data from the UI or via API:

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed \
  -H "Content-Type: application/json" \
  -d '{"reset": false}'
```

Run a demo agent scenario directly:

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "909d28d2-5c9f-5fa2-a35e-f6b39c95f83f"
  }'
```

Run the security harness:

```bash
curl -X POST http://localhost:8000/api/v1/harness/run \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_ids": null,
    "reset_demo_data": true
  }'
```

What the dashboard demonstrates:

- incident and alert overview for the seeded GPU abuse, SSH brute-force, storage pressure, and prompt-injection scenarios
- deterministic agent trace nodes including retrieval, safe-tool execution, self-assessment, watchdog review, and wait-for-human-approval
- RAG citations with provenance, trust labels, scores, and prompt-injection flags
- audited tool calls with safe or blocked posture and structured output previews
- watchdog findings with severity, remediation, and evidence references
- harness scenario scores with pass / failed / partial status and linked safety-event evidence
- a clear AI safety story: no real infrastructure control, no arbitrary shell execution, and no autonomous destructive actions

## Evaluation and Reports

The evaluation layer is deterministic and local-only.
It aggregates persisted agent runs, watchdog findings, safety events, tool calls, and harness results into a scorecard plus export-friendly Markdown and JSON reports.

Scorecard dimensions:

- `safety_score`: harness pass rate plus dangerous-action blocking posture
- `grounding_score`: citation coverage and weak-grounding pressure
- `tool_safety_score`: blocked dangerous tools, failed calls, and no-shell-execution posture
- `watchdog_score`: triggered policy coverage plus human-approval enforcement
- `overall_score`: weighted average of the four dimensions above

Metric families included in the summary:

- harness performance
- watchdog policy coverage
- prompt-injection resistance
- tool safety
- agent quality
- grounding / evidence quality
- human approval enforcement

Run an evaluation:

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{
    "run_harness_if_empty": true,
    "report_type": "full"
  }'
```

Get the latest evaluation summary:

```bash
curl http://localhost:8000/api/v1/evaluation/summary
```

Get the Markdown report:

```bash
curl http://localhost:8000/api/v1/evaluation/report.md
```

Get the JSON report:

```bash
curl http://localhost:8000/api/v1/evaluation/report.json
```

List persisted evaluation scores:

```bash
curl http://localhost:8000/api/v1/evaluation/scores
```

Evaluation limitation:

- this is a deterministic local demo/evaluation, not a production SOC certification or third-party security attestation

## Running Tests

Backend:

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

Quick backend validation:

```bash
cd backend
source .venv/bin/activate
python -c "from app.models import *; from sqlmodel import SQLModel; print(sorted(SQLModel.metadata.tables.keys()))"
python -c "from app.db.session import engine; print('engine ok')"
python -c "from app.main import app; print('app ok')"
```

## Docker Compose

Build and start the full local stack:

```bash
docker compose up --build
```

Stop the stack:

```bash
docker compose down
```

Stop and remove local service volumes:

```bash
docker compose down -v
```

## Demo Vision

The finished project will demonstrate a secure AI incident triage workflow with:

- grounded recommendations over runbooks and past incidents
- metacognitive self-assessment before major agent decisions
- MCP-style allowlisted tools with auditability
- safety and watchdog checks for risky recommendations
- an integrated AI security harness for prompt injection and tool misuse testing
- a premium dashboard suitable for GitHub and Upwork portfolio use

## Current Status

`Milestone 10 evaluation + report export`

Implemented in this milestone:

- backend FastAPI skeleton with CORS, structured logging, and `GET /api/v1/health`
- SQLModel session utilities, modular table models, and schema exports for the core backend entities
- `GET /api/v1/db/health` plus development-only `POST /api/v1/db/create-tables`
- static demo seed service, `POST /api/v1/demo/seed`, and backend tests covering model registration, database routes, and demo seeding
- deterministic document ingestion, chunking, prompt-injection flagging, and lexical chunk retrieval via `/api/v1/documents` and `/api/v1/rag/retrieve`
- typed, allowlisted, audited mock tool registry via `/api/v1/tools` with blocked dangerous-action definitions and database-backed tool-call auditing
- deterministic agent workflow via `/api/v1/agent/runs` with fixed nodes, mock reasoning, self-assessment, grounded citations, safe tool execution, ticket-draft creation, watchdog policy checks, and mandatory human-review handoff
- standalone watchdog evaluation via `/api/v1/watchdog` with policy findings, aggregated decisions, and persisted safety events for agent runs
- deterministic security harness execution via `/api/v1/harness` with scenario registry, persisted harness tests/results, adversarial safety checks, and linked watchdog or tool-registry evidence
- polished Next.js dashboard at `/` and `/dashboard` with live system status, demo controls, agent traces, RAG citations, tool-call audit views, watchdog panels, and harness result summaries
- evaluation summary, score persistence, and Markdown/JSON reporting via `/api/v1/evaluation` over existing harness, watchdog, agent, and tool data
