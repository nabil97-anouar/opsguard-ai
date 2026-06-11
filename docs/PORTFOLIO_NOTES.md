# Portfolio Notes

These notes are for interviews, portfolio walkthroughs, and Upwork proposals.

## 30-Second Explanation

OpsGuard AI is a local-first demo of a secure agentic incident-triage system. It combines deterministic RAG retrieval, allowlisted mock tools, metacognitive self-assessment, watchdog policy checks, adversarial security-harness testing, and evaluation/report export into one coherent backend and dashboard.

## What Makes It Strong Portfolio Material

- It shows full-stack systems thinking instead of a single prompt demo.
- It treats AI safety as part of the product architecture, not an afterthought.
- It demonstrates real engineering tradeoffs: trust boundaries, auditability, human approval, and deterministic local testing.
- It is easy to run locally, which makes it demo-friendly for clients and hiring teams.

## Talking Points For Interviews

- “I wanted to show what a safer operational AI assistant looks like, not just a chatbot with admin access.”
- “The system keeps documents, logs, and tool outputs untrusted by default and forces human approval for risky actions.”
- “The backend is intentionally deterministic, so every milestone stays testable without paid APIs or fragile infrastructure.”
- “I added a security harness and evaluation layer so the project can measure safety behavior instead of only claiming it.”

## Upwork Positioning

This project is especially relevant for clients who need:

- AI copilots for internal operations
- secure RAG workflows
- tool-calling systems with strict boundaries
- AI safety and policy enforcement prototypes
- developer-facing dashboards for demos or stakeholder review
- proof-of-concept systems that are local, testable, and easy to explain

## Honest Limitations To State Up Front

- no external LLM calls by default
- no real infrastructure execution
- no production authentication or deployment stack
- no SOC certification or third-party security attestation
- deterministic demo behavior instead of live autonomous reasoning

Those constraints are deliberate. They make the project safe to review, easy to reproduce, and strong for architecture conversations.

## Good Demo Narrative

1. Seed the demo data.
2. Run the GPU abuse scenario to show grounded retrieval plus safe tool calls.
3. Run the prompt-injection scenario to show suspicious-context handling and watchdog gating.
4. Run the harness to show reproducible adversarial testing.
5. Run the evaluation to show measurable safety posture and exportable reports.

## Positioning Statement

If you need a short portfolio line, use:

> Built a local-first AI incident-triage platform with grounded retrieval, safe tool calling, policy gating, adversarial harness testing, and exportable safety evaluation reports.
