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

`Milestone 1 scaffold`

Implemented in this milestone:

- backend FastAPI skeleton with CORS, structured logging, and `GET /api/v1/health`
- frontend Next.js skeleton with a polished landing page and dashboard placeholder
- Docker Compose stack for PostgreSQL, Qdrant, backend, and frontend
- environment template, demo data placeholders, and clean repo structure for future milestones
