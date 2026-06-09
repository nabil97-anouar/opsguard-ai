# PRODUCT.md — OpsGuard AI

## One-Sentence Pitch

OpsGuard AI is a secure, self-aware agentic incident triage copilot that combines RAG over operational runbooks, MCP-style controlled tool access, metacognitive confidence estimation, and an AI security harness — giving infrastructure and DevSecOps teams a production-grade AI assistant that knows when to stop and ask before acting.

---

## Target Users

| Segment | Role | Pain |
|---|---|---|
| Cloud/DevOps teams | SRE, Platform Engineer | Alert fatigue, slow incident triage, no AI they can trust |
| HPC/GPU cluster operators | MLOps, HPC Admin | GPU/Slurm incident complexity, sparse runbooks |
| AI-first startups | CTO, AI Infra Lead | Need agentic AI that is auditable and safe |
| Security/AI Red Teams | AI Security Engineer | No tooling to stress-test agentic AI in realistic scenarios |
| Enterprise DevSecOps | CISO, SecOps Lead | AI agents with uncontrolled tool access are a liability |

---

## Upwork Buyer Personas

### Persona 1 — The AI Startup CTO
- Building internal AI tooling for their SRE team
- Wants a working agentic copilot, not a prompt wrapper
- Budgets $5k–$25k for an MVP
- Needs: agent workflow, RAG, safety, clean API

### Persona 2 — The Enterprise AI Platform Lead
- Deploying AI agents in regulated infrastructure
- Needs auditability, human-in-the-loop, policy enforcement
- Budgets $20k–$80k for production integration
- Needs: security harness, evaluation, access controls

### Persona 3 — The AI Security Researcher / Red Teamer
- Wants to test their own AI systems for vulnerabilities
- Needs: prompt injection tests, kill-chain scenarios, scoring
- Budgets $5k–$20k for a security audit tool

### Persona 4 — The HPC / MLOps Manager
- Manages A100/H100 clusters with Slurm and complex incident workflows
- Frustrated with manual runbook triage
- Budgets $10k–$30k for operational automation
- Needs: GPU metrics, job queries, runbook RAG, safe recommendations

### Persona 5 — The Series A/B DevOps Lead
- Scaling infrastructure team, wants AI leverage
- Burned by hallucinating AI tools before
- Budgets $8k–$40k
- Needs: grounded recommendations, evidence citations, human approval

---

## What Pain This Solves

1. **Alert fatigue** — Modern infra teams receive hundreds of alerts daily. Triage is slow, manual, and error-prone. OpsGuard AI triages alerts against runbooks, past incidents, and live metrics automatically.

2. **Hallucinating AI copilots** — Generic LLM tools invent runbook steps, cite non-existent logs, and recommend dangerous actions with high confidence. OpsGuard AI estimates its own confidence and stops when evidence is insufficient.

3. **Uncontrolled tool access** — Giving AI agents shell access or unrestricted APIs is a security liability. OpsGuard AI uses a typed, allowlisted, audited tool registry — no arbitrary execution.

4. **No audit trail** — Teams cannot explain what the AI did, why, or whether it was safe. OpsGuard AI logs every step, tool call, retrieval, self-assessment, and human decision.

5. **Prompt injection in operational data** — Logs, metrics, and runbooks can contain adversarial text. OpsGuard AI treats all retrieved content as untrusted and runs injection detection before acting on it.

6. **No AI security testing tooling** — Teams deploying RAG and agents have no way to systematically test them for prompt injection, kill-chain attacks, or tool misuse. OpsGuard AI includes a built-in security harness.

---

## Why This Is More Valuable Than a Normal RAG Chatbot

| Feature | Generic RAG Chatbot | OpsGuard AI |
|---|---|---|
| Retrieval | Semantic search only | Hybrid retrieval + reranking + provenance |
| Tool access | None or unrestricted | MCP-style allowlisted typed tools |
| Confidence | Always answers | Estimates confidence, stops if weak |
| Safety | None | Watchdog policy layer, injection detection |
| Security testing | None | Built-in AI security harness |
| Auditability | None | Full step trace, tool audit log, human decisions |
| Agent design | Single-prompt chain | Multi-node LangGraph-style workflow |
| Threat modeling | None | AI kill-chain mapping layer |
| Human loop | None | Structured approval for risky actions |
| Evaluation | None | Grounding, correctness, safety metrics |

---

## What Makes It Unique

1. **Metacognitive self-assessment** — The agent explicitly scores its own confidence, identifies missing evidence, and decides whether to continue, retrieve more, call a tool, ask a human, or stop. This is not common in publicly available agentic systems.

2. **AI kill-chain threat layer** — Maps incidents and agent behaviors to an AI-era threat taxonomy: supply chain compromise, prompt injection delivery, model extraction, agentic pivot, unsafe tool use.

3. **Security harness with executable scenarios** — A built-in red-team harness that runs structured attack payloads against the agent, RAG pipeline, and tools, scoring each result.

4. **Operational domain specificity** — Built for real infrastructure teams (Cloud, GPU, HPC, DevOps), not generic Q&A. Runbooks, metrics, Slurm job data, GPU alerts.

5. **Production-style architecture** — FastAPI, LangGraph-style workflow, Qdrant, PostgreSQL, Docker Compose, typed schemas, audit logs. Not a notebook prototype.

---

## Services I Can Sell on Upwork Using This Project

| Service | Deliverable | Price Range |
|---|---|---|
| Agentic AI copilot for incident triage | Working FastAPI + Next.js system with RAG + tools | $8k–$25k |
| Secure AI agent audit and red team | Security harness report + findings | $3k–$15k |
| RAG pipeline for operational docs | Ingestion + retrieval + citation system | $3k–$10k |
| LLMOps evaluation framework | Grounding, safety, correctness metrics | $2k–$8k |
| AI agent workflow design | Architecture + LangGraph workflow + human loop | $2k–$6k |
| GPU/HPC AI copilot | Slurm-aware triage agent with GPU metrics | $10k–$30k |
| AI security harness tooling | Standalone kill-chain + injection tester | $5k–$20k |
| Full production deployment | Docker Compose + CI + monitoring | $3k–$8k |

---

## Portfolio Positioning

**Positioning statement:**
> I build production-grade AI agents and RAG systems for infrastructure teams — with built-in safety, auditability, and AI security testing. Not chatbots. Engineered AI systems.

**Differentiators to highlight:**
- Metacognitive agents that know their limits
- AI security harness and kill-chain threat modeling
- Real operational domain: Cloud, GPU, HPC, DevSecOps
- Full stack: FastAPI backend, Next.js frontend, Qdrant, PostgreSQL
- Clean code, typed schemas, Docker Compose, no-key demo mode

---

## Suggested GitHub Repo Description

```
OpsGuard AI — Secure self-aware agentic incident triage copilot. 
LangGraph-style workflow | RAG over runbooks | MCP-style tool registry | 
AI security harness | Metacognitive confidence estimation | Human-in-the-loop approval. 
FastAPI + Next.js + Qdrant + PostgreSQL. Docker Compose. Demo mode included.
```

**GitHub topics:**
`ai-agents` `rag` `langraph` `incident-response` `ai-security` `prompt-injection` `fastapi` `nextjs` `devops` `llmops` `mlops` `hpc` `metacognition` `ai-safety`

---

## Suggested LinkedIn / Upwork Project Description

> **OpsGuard AI — Secure Agentic Incident Triage Copilot**
>
> Built a production-style AI system for infrastructure and DevSecOps teams that combines:
> - A multi-node agentic workflow (LangGraph-style) for incident triage
> - RAG over runbooks, incident reports, and security documents (Qdrant + hybrid retrieval)
> - MCP-style tool registry with allowlisted, typed, audited tool access
> - Metacognitive self-assessment: the agent estimates confidence and stops when evidence is insufficient
> - AI security harness with prompt injection tests, AI kill-chain scenarios, and tool misuse detection
> - Human-in-the-loop approval for all risky recommendations
> - Full audit trail: every step, tool call, retrieval, and decision is logged
> - Clean Next.js dashboard with trace viewer, self-assessment panel, and security harness results
>
> Stack: FastAPI · Python 3.11 · LangGraph · LlamaIndex · Qdrant · PostgreSQL · SQLModel · Next.js · TypeScript · Tailwind CSS · Docker Compose
>
> Demonstrates: secure agentic AI engineering, LLMOps, RAG, AI security, DevOps automation.
