# Security Boundaries

OpsGuard constrains incident triage through a fixed workflow, a closed tool registry, input screening, policy evaluation, and a terminal review state. Its current infrastructure adapters return local fixtures; the application has no live infrastructure credentials or command-execution integration.

This document describes implemented controls and their limits.

## Execution boundary

[execute_tool](../backend/app/tools/registry.py) accepts only registered tool names and validates input and output against Pydantic schemas. Current handlers read local fixtures or SQL data, retrieve document chunks, and create local ticket drafts. They do not run arbitrary shell commands or send tickets to an external system.

The five disruptive definitions—`cancel_job`, `drain_node`, `block_user`, `isolate_node`, and `disable_service`—have no executable handler. The dispatcher returns a blocked result and creates a safety event. Supplying an approval field does not make them executable.

This restriction comes from registered capabilities and handlers, not a general-purpose sandbox. The dispatcher denies definitions that are destructive, require approval, or lack a handler. Registry usage descriptions are informational; there is no reviewer identity or approval-grant mechanism. See [Tool Registry](TOOL_REGISTRY.md).

## Trust and evidence

Alert descriptions, documents, and tool outputs can contain untrusted text. The deterministic planner selects tools by incident category, and retrieved text does not become executable instructions.

The canonical trust labels are `trusted`, `untrusted`, and `quarantined`. Public ingestion rejects trusted declarations, including metadata declarations. Internal provisioning can create trusted sources; ordinary ingestion cannot promote existing content. Metadata-only demotions update existing chunks, and retrieval resolves document/chunk/metadata conflicts to the most restrictive label. Malformed persisted labels fail closed to quarantine. Screening does not promote trust.

The retrieval API can exclude untrusted content and always excludes quarantined chunks. Trust labels are not source authentication or access control. Fixture reseeding without reset preserves demotions; an explicit fixture reset deletes and recreates baseline records. No reviewed promotion or unquarantine workflow is implemented.

New recommendations preserve complete evidence snapshots, and hypothesis references must resolve to evidence recorded during that run. Failed or blocked tool attempts never become supporting observations. Missing operational targets create gaps instead of fixture-specific calls. Historical views use persisted evidence exclusively. These controls establish identity and retention; the application does not establish that each claim follows from its citations. [Retrieval and Evidence](RAG_DESIGN.md) describes these boundaries.

## Screening and watchdog checks

The [injection scanner](../backend/app/rag/injection.py) matches known instruction-override, secret-disclosure, exfiltration, safety-disabling, and shell-command patterns. Ingestion records chunk scan results; retrieval uses stored results when present. Tool outputs are also scanned in the audit and agent paths.

A clean result means no configured pattern matched. Screening does not cover every input field or attack formulation, and flagged documents are not automatically quarantined.

The [watchdog](../backend/app/watchdog/policies.py) checks dangerous actions, prompt-injection indicators, untrusted context, low confidence on severe alerts, weak grounding, broad operations, and suspicious tool output. Its decision is one of `allow`, `allow_with_warnings`, `require_human_approval`, or `block`.

These checks are heuristic. Text-based action checks have case and phrasing gaps, evidence discussion can trigger the same rules as proposed actions, and citation presence is not support verification. Watchdog results are review signals, not authorization to operate infrastructure.

The current reasoning layer is deterministic and does not interpret retrieved instructions as a language model would. Harness results for this implementation do not establish injection resistance for a future model provider.

## Human review and drafts

[wait_for_human_approval](../backend/app/agent/nodes.py) ends every successful investigation with `waiting_for_human` and approval `pending`. There is no authenticated reviewer identity, approve/reject endpoint, or resumed execution path.

Ticket drafts are written locally before watchdog evaluation and do not receive the later watchdog annotations. Review the final run status and findings with the draft. A failed run may retain earlier snapshots or candidate text; those records are not evidence of completed policy review.

## Audit coverage

The application stores step snapshots, assessments, tool calls, and safety events in SQL. Run-associated tool calls include arguments, output, timing, status, and screening results.

Coverage is incomplete: contextless tool calls lack `ToolCall` records, validation/unknown-tool failures are not comprehensively recorded, and ticket input can name a different run from its audit context. Commits occur at multiple stages, so partial investigation records can remain after failure. Audit rows are ordinary database records, not a tamper-evident log.

See [Data Model](DATA_MODEL.md) and [Tool Registry](TOOL_REGISTRY.md) for storage and association details.

## API and host exposure

The [FastAPI application](../backend/app/main.py) has CORS configuration and response security headers, but no authentication, per-user authorization, rate limiting, or tenant isolation. CORS and headers do not prevent direct API access.

[docker-compose.yml](../docker-compose.yml) publishes ports 3000, 8000, 5432, 6333, and 6334 without a `127.0.0.1` bind restriction. PostgreSQL defaults use local development credentials, and the backend listens on all container interfaces. Host reachability depends on Docker and network configuration; the Compose file itself does not restrict published ports to localhost.

The explicit seeding and table-creation endpoints reject `ENVIRONMENT=production`, but that setting does not harden the application: other routes create tables, and harness/evaluation paths can seed or reset data. Use disposable fixture databases for these workflows and keep the API on a trusted local network boundary.

The current runner requires no external model keys. Provider-related configuration fields do not enable a real provider. Avoid placing credentials in browser-visible `NEXT_PUBLIC_*` settings.

## Interpreting evaluation

Security-harness outcomes show whether particular implemented checks fired for particular fixtures. Evaluation includes counters and heuristic scores; it is not a certification of application security or a scientific measurement of model reliability.

See [Security Harness](SECURITY_HARNESS.md), [Evaluation](EVALUATION.md), and [API Reference](API_SPEC.md) for reproducible inputs, result semantics, and supported operations.
