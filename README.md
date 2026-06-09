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
- executes a fixed graph of nodes: ingest, classify, retrieve, plan, execute safe tools, synthesize, self-assess, recommend, and wait for human approval
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
- final recommendations can create internal ticket drafts, but they never call external ticketing systems
- the workflow is designed for deterministic demos and tests, not for autonomous remediation

Frontend:

```bash
cd frontend
npm install
npm run dev
```

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

`Milestone 6 deterministic agent workflow`

Implemented in this milestone:

- backend FastAPI skeleton with CORS, structured logging, and `GET /api/v1/health`
- SQLModel session utilities, modular table models, and schema exports for the core backend entities
- `GET /api/v1/db/health` plus development-only `POST /api/v1/db/create-tables`
- static demo seed service, `POST /api/v1/demo/seed`, and backend tests covering model registration, database routes, and demo seeding
- deterministic document ingestion, chunking, prompt-injection flagging, and lexical chunk retrieval via `/api/v1/documents` and `/api/v1/rag/retrieve`
- typed, allowlisted, audited mock tool registry via `/api/v1/tools` with blocked dangerous-action definitions and database-backed tool-call auditing
- deterministic agent workflow via `/api/v1/agent/runs` with fixed nodes, mock reasoning, self-assessment, grounded citations, safe tool execution, ticket-draft creation, and mandatory human-review handoff
