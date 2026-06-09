# CODEX_BRIEF.md — OpsGuard AI Implementation Brief for Codex

## What You Are Building

OpsGuard AI is a production-style AI system for infrastructure operations teams. It is NOT a chatbot. It is a multi-node agentic workflow that triages infrastructure alerts, retrieves evidence from a knowledge base, calls safe read-only tools, estimates its own confidence, enforces safety policies, and generates grounded incident recommendations with a human-in-the-loop approval step.

The project is designed as a premium portfolio piece for an AI engineer. It must be visually impressive, architecturally sound, and practically useful. Every component has a spec document in the `docs/` folder.

---

## Project Goal

Build a system where:
1. An operator submits an alert (or loads demo data)
2. A 15-node agent workflow runs automatically
3. The agent retrieves relevant runbooks and past incidents via RAG
4. The agent calls safe, allowlisted tools (no shell execution)
5. The agent estimates its own confidence at two checkpoints
6. A safety watchdog validates all plans and recommendations
7. High-risk recommendations are held for human approval
8. A full audit trail is stored in PostgreSQL
9. A premium Next.js dashboard shows everything
10. A built-in security harness red-teams the agent pipeline

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.11, Pydantic v2, SQLModel |
| Database | PostgreSQL 15 (via Docker) |
| Vector DB | Qdrant (via Docker) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (local default) |
| Agent framework | Custom LangGraph-style Python runner (no heavy framework required) |
| LLM | Pluggable via env var; default: MockLLMProvider |
| Deployment | Docker Compose (local-first) |

---

## Repository Structure

```
opsguard-ai/
├── .env.example           # All environment variables documented
├── .gitignore
├── docker-compose.yml     # postgres, qdrant, backend, frontend
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py        # FastAPI app + router registration
│       ├── config.py      # pydantic-settings Settings class
│       ├── database.py    # SQLModel engine + session
│       ├── routers/       # One file per domain
│       ├── models/        # SQLModel ORM tables
│       ├── schemas/       # Pydantic request/response schemas
│       ├── services/      # Business logic
│       ├── agent/         # Agent workflow engine
│       ├── rag/           # RAG pipeline
│       ├── tools/         # MCP-style tool registry
│       ├── harness/       # Security harness
│       └── evaluation/    # Evaluation engine
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── src/
│       ├── app/           # Next.js App Router pages
│       ├── components/    # Reusable UI components
│       └── lib/           # API client, utilities
│
├── demo_data/             # Runbooks, incident reports, policies (Markdown files)
│
└── docs/                  # Architecture and spec documents
    ├── PRODUCT.md
    ├── ARCHITECTURE.md
    ├── AGENT_GRAPH.md
    ├── SECURITY_HARNESS.md
    ├── DATA_MODEL.md
    ├── API_SPEC.md
    ├── RAG_DESIGN.md
    ├── TOOL_REGISTRY.md
    ├── FRONTEND_SPEC.md
    ├── EVALUATION.md
    ├── IMPLEMENTATION_PLAN.md
    └── CODEX_BRIEF.md
```

---

## Coding Rules

### General
- Python 3.11+. All types annotated. No `Any` unless unavoidable.
- Pydantic v2 for all schemas. Use `model_dump()`, not `.dict()`.
- No bare `except:` — catch specific exceptions.
- No `print()` in production code — use Python `logging`.
- No hardcoded secrets — all from env vars via `config.py`.

### Backend
- SQLModel for all database tables. Use `Optional[X]` for nullable fields.
- Async FastAPI handlers with `AsyncSession` from SQLModel.
- All UUIDs use `uuid.uuid4()`. Store as UUID type, not string.
- All timestamps use `datetime.utcnow()` with `timezone=True`.
- Use `Literal` types for enums in schemas.
- Return types for all endpoints must be explicit Pydantic models.

### Agent Workflow
- Agent state is a TypedDict. Each node receives state, returns mutated state copy.
- Do NOT mutate state in place. Return a new dict from each node.
- Each node must log its execution to `agent_steps` table.
- LLM calls must use structured output (Pydantic schema passed to LLM).
- If LLM returns malformed output, retry once, then use safe fallback.
- Metacognitive self-assessment must be a real computation, not a hardcoded value.

### Safety Rules (Non-Negotiable)
- No arbitrary shell execution. Ever. Not even `subprocess.run`.
- TOOL_ALLOWLIST is the single source of truth. No tool executes outside it.
- All retrieved text is UNTRUSTED until injection-scanned.
- Dangerous actions (cancel_job, drain_node, etc.) NEVER execute. They appear as `requires_human_approval` recommendations only.
- Every tool call is logged to the database before the handler executes.
- Watchdog runs before tool execution AND before recommendation generation.

### Frontend
- TypeScript strict mode. No `any` types.
- All API calls go through the typed client in `src/lib/api.ts`.
- Dark theme only. Use the color palette from FRONTEND_SPEC.md.
- All loading states use skeleton components, not spinners.
- Error states must be visible and actionable (not blank pages).

---

## Environment Variables

```bash
# Required
POSTGRES_URL=postgresql+asyncpg://opsguard:opsguard@postgres:5432/opsguard
QDRANT_URL=http://qdrant:6333
SECRET_KEY=change-me-in-production

# LLM Configuration
LLM_PROVIDER=mock              # mock | openai | anthropic
OPENAI_API_KEY=                # optional, only for openai provider
ANTHROPIC_API_KEY=             # optional, only for anthropic provider

# Feature flags
DEMO_MODE=true                 # enables POST /demo/seed endpoint
RERANKER=none                  # none | cross_encoder

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
# EMBEDDING_MODEL=openai:text-embedding-3-small  # alternative if API key set

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## Mock LLM Mode

When `LLM_PROVIDER=mock`, the `MockLLMProvider` returns pre-scripted responses. This means:
- No API key required
- Responses are deterministic (useful for testing)
- Demo runs complete in < 3 seconds
- All evaluation scores are pre-computed to look realistic

Mock responses are stored in `backend/app/agent/llm/mock_responses/` as JSON files keyed by `(alert_type, node_name)`.

The system must work completely in mock mode. Do not require a real LLM for any core functionality.

---

## How to Proceed: Milestones

**Read IMPLEMENTATION_PLAN.md first.** It defines 11 milestones with exact file lists, expected outputs, and stopping points.

**Important rules for Codex:**
1. Start only with Milestone 1.
2. Complete Milestone 1 fully before moving to Milestone 2.
3. After each milestone, summarize: what files were created, what works, what is stubbed.
4. Do not implement business logic from a later milestone during an earlier one.
5. Do not add features beyond what the milestone specifies.
6. Do not install packages not in `requirements.txt` without noting the addition.

---

## Milestone 1 Instructions (Start Here)

Your first task is Milestone 1: Repository Scaffold.

**Create:**
1. `docker-compose.yml` — four services: `postgres`, `qdrant`, `backend`, `frontend`
2. `.env.example` — all variables documented above
3. `.gitignore` — Python, Node, Docker, env file patterns
4. `backend/Dockerfile` — Python 3.11 slim, install requirements, run uvicorn
5. `backend/requirements.txt` — fastapi, uvicorn, sqlmodel, asyncpg, pydantic-settings, pydantic, python-multipart, httpx, qdrant-client, sentence-transformers, pytest, pytest-asyncio
6. `backend/app/main.py` — FastAPI app with CORS, all routers registered
7. `backend/app/config.py` — Settings class with all env vars
8. `backend/app/database.py` — SQLModel engine, `create_db_and_tables()`, `get_session()`
9. `backend/app/routers/health.py` — `GET /health` returning dependency status
10. All other routers as stubs returning `501 Not Implemented`
11. All `models/`, `schemas/`, `services/`, `agent/`, `rag/`, `tools/`, `harness/`, `evaluation/` as empty packages with `__init__.py`
12. `frontend/` — Next.js project with TypeScript, Tailwind, shadcn/ui setup
13. `frontend/src/app/page.tsx` — Minimal landing page with "OpsGuard AI" text
14. `frontend/src/app/dashboard/page.tsx` — Placeholder dashboard
15. `frontend/src/components/layout/Sidebar.tsx` — Navigation sidebar stub
16. `demo_data/runbooks/.gitkeep`, `demo_data/incident_reports/.gitkeep`, `demo_data/security_policies/.gitkeep`

**Do NOT implement:**
- Database tables (Milestone 2)
- Demo data (Milestone 3)
- RAG pipeline (Milestone 4)
- Tool registry (Milestone 5)
- Agent workflow (Milestone 6)
- Any LLM calls

**Stop when:**
- `docker-compose up --build` completes without errors
- `GET /api/v1/health` returns 200
- Frontend loads at `localhost:3000`
- All other backend routes return 501

**Then summarize:**
- List all files created
- Confirm health check passes
- Note any deviations from the plan

---

## Key Reference Documents

| Question | Document |
|---|---|
| What tables exist in the DB? | DATA_MODEL.md |
| What endpoints exist? | API_SPEC.md |
| What does each agent node do? | AGENT_GRAPH.md |
| What tools exist and how are they secured? | TOOL_REGISTRY.md |
| What does the RAG pipeline do? | RAG_DESIGN.md |
| What security tests exist? | SECURITY_HARNESS.md |
| What does each page look like? | FRONTEND_SPEC.md |
| How are evaluation metrics computed? | EVALUATION.md |
| What is the full system architecture? | ARCHITECTURE.md |

---

## What Makes This System Different from a RAG Chatbot

Every time you write code, remember these architectural differentiators:

1. **Metacognitive self-assessment** — the agent computes its own confidence and can decide to stop, not just answer
2. **All tool calls are typed, allowlisted, and audited** — no shell execution, ever
3. **All retrieved text is UNTRUSTED** — wrapped in delimiters before LLM context
4. **Injection scanning runs pre-LLM** — not just post-recommendation
5. **Dangerous actions require human approval** — the workflow actually pauses and waits
6. **Security harness runs against the live pipeline** — not just hypothetical tests
7. **Everything is logged** — every step, tool call, self-assessment, and human decision is in PostgreSQL

These properties must be preserved throughout implementation. They are what makes this project worth building.
