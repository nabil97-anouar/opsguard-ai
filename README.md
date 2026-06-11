# OpsGuard AI

Secure self-aware agentic incident triage.

OpsGuard AI is a polished local-first portfolio project that demonstrates how to build an AI-assisted incident-triage system with grounded retrieval, safe tool calling, watchdog policy checks, adversarial harness testing, and exportable safety evaluation reports.

## 30-Second Pitch

Most AI incident copilots optimize for speed and confidence. OpsGuard AI optimizes for evidence, uncertainty, auditability, and safety boundaries.

This project shows a better pattern:

- retrieve context with provenance and trust labels
- call only allowlisted, typed, deterministic mock tools
- preserve self-assessment and missing evidence
- run policy checks before handing anything to a human
- evaluate the whole stack with adversarial security scenarios

It is intentionally local, deterministic, and safe to demo without external LLM APIs or real infrastructure access.

## Why This Project Matters

Operational AI is useful only if it is grounded and governable. A system that can summarize alerts but cannot explain its evidence, resist prompt injection, or respect approval boundaries is risky in exactly the environments where trust matters most.

OpsGuard AI is a concrete answer to that problem. It demonstrates:

- secure self-aware agentic incident triage
- RAG-grounded investigation
- safe MCP-style tool exposure
- watchdog safety enforcement
- reproducible security-harness testing
- measurable evaluation and reporting

## Architecture Overview

### Frontend

- Next.js + TypeScript + Tailwind dashboard
- polished demo surface for alerts, traces, citations, watchdog findings, harness results, and evaluation summary

### Backend

- FastAPI + SQLModel service
- deterministic RAG ingestion and lexical retrieval
- allowlisted mock tool registry
- fixed agent workflow with mock LLM reasoning
- watchdog policy layer
- security harness runner
- evaluation and report export endpoints

### Data / Local Stack

- PostgreSQL supported via Docker Compose
- SQLite fallback for local tests and simple runs
- Qdrant is present in the compose file for future-facing architecture, but Milestone 4 retrieval works without it

## Core Capabilities

- Demo data seeding for realistic GPU abuse, SSH brute-force, storage pressure, and prompt-injection scenarios
- Deterministic document ingestion, chunking, and retrieval with provenance
- Prompt-injection scanning on retrieved and untrusted content
- MCP-style safe tool registry with audited tool calls
- Deterministic agent workflow with metacognitive self-assessment
- Watchdog policy evaluation for dangerous actions, weak grounding, low confidence, and suspicious context
- Security harness scenarios for adversarial AI-safety testing
- Evaluation scorecard plus Markdown and JSON reporting
- Premium local dashboard for screenshots, demos, and portfolio walkthroughs

## Safety Design

OpsGuard AI is built around explicit safety boundaries.

- Retrieved documents, logs, and tool outputs are treated as untrusted by default.
- Dangerous tools are blocked and never executed.
- Agent runs always stop at human approval.
- Suspicious context lowers confidence and is surfaced in the final recommendation.
- Watchdog policies inspect the recommendation before it is considered safe for review.
- The harness tests whether the system resists poisoned evidence, unsafe tool feedback, and destructive suggestions.

This is not autonomous infrastructure control. It is a safe demo of how such systems should be architected.

## Demo Walkthrough

### What the Demo Shows

1. Seed deterministic demo data.
2. Run a GPU abuse investigation with RAG-grounded context and safe mock tools.
3. Run a prompt-injection scenario and show suspicious-context handling.
4. Run the security harness across adversarial AI-safety cases.
5. Run the evaluation layer and export a Markdown or JSON report.

### Stable Demo Alert IDs

The seeded alert IDs are deterministic:

- GPU abuse alert: `909d28d2-5c9f-5fa2-a35e-f6b39c95f83f`
- Prompt-injection alert: `e3e0e0d5-9e19-5243-a1f0-76c507be3641`

### One-Command Demo

```bash
./scripts/demo_walkthrough.sh
```

See [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for expected output and troubleshooting.

## Quick Start

### 1. Prepare Environment

```bash
cp .env.example .env
```

### 2. Start the Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Run the Full Demo

```bash
./scripts/demo_walkthrough.sh
```

## Backend Commands

Create tables with PostgreSQL:

```bash
docker compose up -d postgres
cd backend
source .venv/bin/activate
python -m app.db.init_db
```

Create tables with SQLite fallback:

```bash
cd backend
source .venv/bin/activate
DATABASE_URL=sqlite:///./opsguard.db python -m app.db.init_db
```

Development-only create-tables endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/db/create-tables
```

## Frontend Commands

```bash
cd frontend
npm install
npm run dev
```

Frontend sanity checks:

```bash
npm run lint
npx tsc --noEmit
```

## Seed Demo Data

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed \
  -H "Content-Type: application/json" \
  -d '{"reset": false}'
```

Reset only demo-created records and reseed:

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed \
  -H "Content-Type: application/json" \
  -d '{"reset": true}'
```

## Run Agent Scenario

GPU abuse:

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs \
  -H "Content-Type: application/json" \
  -d '{"alert_id":"909d28d2-5c9f-5fa2-a35e-f6b39c95f83f"}'
```

Prompt injection:

```bash
curl -X POST http://localhost:8000/api/v1/agent/runs \
  -H "Content-Type: application/json" \
  -d '{"alert_id":"e3e0e0d5-9e19-5243-a1f0-76c507be3641"}'
```

Fetch run details:

```bash
curl http://localhost:8000/api/v1/agent/runs/<agent_run_id>
```

## Run Security Harness

Run all scenarios:

```bash
curl -X POST http://localhost:8000/api/v1/harness/run \
  -H "Content-Type: application/json" \
  -d '{"scenario_ids": null, "reset_demo_data": true}'
```

List scenarios:

```bash
curl http://localhost:8000/api/v1/harness/scenarios
```

Fetch recent results:

```bash
curl http://localhost:8000/api/v1/harness/results
```

## Run Evaluation Report

Run evaluation:

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{"run_harness_if_empty": true, "report_type": "full"}'
```

Get summary:

```bash
curl http://localhost:8000/api/v1/evaluation/summary
```

Get Markdown report:

```bash
curl http://localhost:8000/api/v1/evaluation/report.md
```

Get JSON report:

```bash
curl http://localhost:8000/api/v1/evaluation/report.json
```

List stored evaluation scores:

```bash
curl http://localhost:8000/api/v1/evaluation/scores
```

## Screenshots Placeholders

Add these screenshots before publishing a final portfolio page or Upwork attachment set:

- Dashboard overview hero with system posture and demo controls
- Agent trace focused on `retrieve_context`, `execute_safe_tools`, `metacognitive_self_assessment`, and `watchdog_policy_check`
- RAG citations panel showing trusted and untrusted chunks
- Watchdog findings panel with a blocked or require-human-approval result
- Security harness results grid with pass / partial / failed breakdown
- Evaluation report summary card or rendered Markdown report

## API Overview

### Core Health / Setup

- `GET /api/v1/health`
- `GET /api/v1/db/health`
- `POST /api/v1/db/create-tables`
- `POST /api/v1/demo/seed`

### Documents / RAG

- `POST /api/v1/documents/ingest`
- `GET /api/v1/documents`
- `POST /api/v1/rag/retrieve`

### Safe Tool Registry

- `GET /api/v1/tools`
- `POST /api/v1/tools/{tool_name}/execute`

### Agent Workflow

- `POST /api/v1/agent/runs`
- `GET /api/v1/agent/runs`
- `GET /api/v1/agent/runs/{agent_run_id}`

### Watchdog

- `GET /api/v1/watchdog/policies`
- `POST /api/v1/watchdog/evaluate`

### Security Harness

- `GET /api/v1/harness/scenarios`
- `POST /api/v1/harness/run`
- `GET /api/v1/harness/results`
- `GET /api/v1/harness/results/{harness_run_id}`

### Evaluation / Reporting

- `POST /api/v1/evaluation/run`
- `GET /api/v1/evaluation/summary`
- `GET /api/v1/evaluation/report.md`
- `GET /api/v1/evaluation/report.json`
- `GET /api/v1/evaluation/scores`

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   ├── api/routes/
│   │   ├── db/
│   │   ├── evaluation/
│   │   ├── harness/
│   │   ├── models/
│   │   ├── rag/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tools/
│   │   └── watchdog/
│   └── tests/
├── docs/
├── frontend/
│   ├── components/
│   ├── lib/
│   └── src/app/
├── scripts/
├── demo_data/
├── docker-compose.yml
└── .env.example
```

## Tech Stack

- Backend: FastAPI, SQLModel, Pydantic, SQLAlchemy
- Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS
- Local data: PostgreSQL, SQLite fallback
- Demo/runtime model behavior: deterministic mock logic only
- Testing: pytest, frontend lint, TypeScript type-checking

## Security Boundaries

- no arbitrary shell execution
- no subprocess-based infrastructure control
- no real Slurm, Docker, network, or system commands
- no autonomous destructive actions
- no prompt text treated as authority over policy
- no bypass of human approval for dangerous recommendations

Detailed boundary notes live in [docs/SECURITY_BOUNDARIES.md](docs/SECURITY_BOUNDARIES.md).

## What Is Mocked vs Real

| Area | In this project |
| --- | --- |
| LLM reasoning | Mocked, deterministic, local-only |
| Tool execution | Mocked, allowlisted, typed, auditable |
| Infrastructure control | Not implemented and intentionally blocked |
| RAG retrieval | Real local deterministic lexical retrieval over SQL data |
| Database persistence | Real |
| Agent workflow persistence | Real |
| Watchdog policy evaluation | Real deterministic local logic |
| Security harness execution | Real deterministic local logic |
| Evaluation / report export | Real deterministic local logic |

## Docker Compose

Bring up the local stack:

```bash
docker compose up --build
```

Stop it:

```bash
docker compose down
```

Remove local volumes:

```bash
docker compose down -v
```

## Verification Commands

Backend:

```bash
cd backend
.venv/bin/pytest tests/ -v
.venv/bin/python -c "from app.main import app; print('app ok')"
```

Frontend:

```bash
cd frontend
npm run lint
npx tsc --noEmit
```

## Roadmap / Future Work

- optional real embedding backend behind the existing RAG interfaces
- real ticketing or case-management integrations behind explicit approval boundaries
- stronger report history and comparison views
- deployment hardening, auth, and production operations only after the local safety story is already solid

## Portfolio Positioning / Upwork Relevance

OpsGuard AI is a strong portfolio piece for:

- AI safety engineering
- secure RAG systems
- agentic workflow design
- backend-heavy AI product prototyping
- DevOps / platform tooling demos
- full-stack technical portfolio presentation

If you are showing this to a client or recruiter, the message is:

> This is not a toy chatbot. It is a local, testable, audit-friendly AI operations prototype that demonstrates how to combine retrieval, tool calling, policy enforcement, harness testing, and exportable evaluation into one coherent system.

See also:

- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- [docs/PORTFOLIO_NOTES.md](docs/PORTFOLIO_NOTES.md)
- [docs/SECURITY_BOUNDARIES.md](docs/SECURITY_BOUNDARIES.md)

## Honesty Statement

OpsGuard AI is a deterministic local demo and portfolio project.

It does not claim:

- production deployment maturity
- SOC certification
- live autonomous remediation
- external LLM usage by default
- real infrastructure access

That honesty is intentional. The point of the project is to show strong architecture, safety boundaries, and demo readiness without pretending the system is something it is not.
