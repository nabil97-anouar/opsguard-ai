# Security Boundaries

OpsGuard constrains incident triage through a fixed workflow, a closed tool registry, input screening, policy evaluation, and a terminal review state. Its current infrastructure adapters return local fixtures; the application has no live infrastructure credentials or command-execution integration.

This document describes implemented controls and their limits.

## Execution boundary

[execute_tool](../backend/app/tools/registry.py) accepts only registered tool names and validates input and output against Pydantic schemas. Current handlers read local fixtures or SQL data, retrieve document chunks, and create local ticket drafts. They do not run arbitrary shell commands or send tickets to an external system.

The five disruptive definitions—`cancel_job`, `drain_node`, `block_user`, `isolate_node`, and `disable_service`—have no executable handler. The dispatcher records a denied attempt without handler invocation; run-associated destructive denials also create a safety event. Supplying an approval field does not make them executable.

This restriction comes from registered capabilities and handlers, not a general-purpose sandbox. The dispatcher denies definitions that are destructive, require approval, or lack a handler. Registry usage descriptions are informational; there is no reviewer identity or approval-grant mechanism. See [Tool Registry](TOOL_REGISTRY.md).

## Trust and evidence

Alert descriptions, documents, and tool outputs can contain untrusted text. The deterministic planner selects tools by incident category, and retrieved text does not become executable instructions.

The canonical trust labels are `trusted`, `untrusted`, and `quarantined`. Public ingestion rejects trusted declarations, including metadata declarations. Internal provisioning can create trusted sources; ordinary ingestion cannot promote existing content. Metadata-only demotions update existing chunks, and retrieval resolves document/chunk/metadata conflicts to the most restrictive label. Malformed persisted labels fail closed to quarantine. Screening does not promote trust.

The retrieval API can exclude untrusted content and always excludes quarantined chunks. Trust labels are not source authentication or access control. Fixture reseeding without reset preserves demotions; an explicit fixture reset deletes and recreates baseline records. No reviewed promotion or unquarantine workflow is implemented.

New recommendations preserve complete evidence snapshots, and hypothesis references must resolve to evidence recorded during that run. Failed or blocked tool attempts never become supporting observations. Missing operational targets create gaps instead of fixture-specific calls. Historical views use persisted evidence exclusively. These controls establish identity and retention; the application does not establish that each claim follows from its citations. [Retrieval and Evidence](RAG_DESIGN.md) describes these boundaries.

## Screening and watchdog checks

The [injection scanner](../backend/app/rag/injection.py) matches known instruction-override, secret-disclosure, exfiltration, safety-disabling, and shell-command patterns. Ingestion records chunk scan results; retrieval uses stored results when present. Tool outputs are also scanned in the audit and agent paths.

A clean result means no configured pattern matched. Screening does not cover every input field or attack formulation, and flagged documents are not automatically quarantined.

The [watchdog](../backend/app/watchdog/policies.py) checks structured action intent, reference integrity, prompt-injection indicators, untrusted context, low confidence on severe alerts, missing references, broad operations, and suspicious tool output. Its decision is one of `allow`, `allow_with_warnings`, `require_human_approval`, or `block`.

[ProposedAction](../backend/app/agent/actions.py) carries an action ID/type, target, parameters, risk label, approval requirement, supporting evidence IDs, and rationale. Action checks normalize Unicode, casing, whitespace and punctuation. Structured types, parameters, target counts, selectors and wildcard scopes drive decisions; proposal narrative and intent-bearing rationale receive supplemental screening. Retrieved evidence, tool observations and hypotheses are separate input fields and never become proposed actions merely by mentioning a command. Injection screening can still flag that content independently.

`grounding_reference_integrity` requires same-run references to valid source observations, rejects missing/empty references, failed or blocked tool support, quarantine, and altered recommendation snapshots. The standalone API loads its authoritative evidence ledger from persisted source steps and successful tool-call records, ignoring caller-supplied evidence as authority. Internal workflow and harness callers supply their source ledgers explicitly. This is structural reference validation, not semantic entailment.

Decisions expose exact `verdict`, severity, finding IDs/types, affected action IDs, `blocking`, `mandatory_review`, reason, and `policy_version: watchdog-policy-v3`. `status` remains an exact compatibility alias. Explicit action approval requirements produce review findings; disruptive intent blocks regardless of a caller's risk or approval label. These checks remain deterministic and incomplete for arbitrary language. A policy verdict does not authorize tool dispatch or infrastructure operation.

The current reasoning layer is deterministic and does not interpret retrieved instructions as a language model would. Harness results for this implementation do not establish injection resistance for a future model provider.

## Human review and drafts

[wait_for_human_approval](../backend/app/agent/nodes.py) ends every successful investigation with `waiting_for_human` and approval `pending`. There is no authenticated reviewer identity, approve/reject endpoint, or resumed execution path.

Recommendation generation persists `candidate`, `review_valid=false` and no ticket. The watchdog then records its decision and transitions the artifact to `pending_human_review` (policy checked, not human approved) or `blocked` (`review_valid=false`). Only then does the workflow create its local ticket with lifecycle, policy-validation and version fields. Blocked drafts remain traceable as blocked artifacts. Direct API ticket creation has no policy decision and produces a candidate marked `not_evaluated`. Provider-supplied validation labels cannot skip this lifecycle. Earlier candidate snapshots remain candidates if a later step fails.

## Audit coverage

The application stores step snapshots, assessments, tool calls, and safety events in SQL. Run-associated tool calls include arguments, output, timing, status, and screening results.

Every request reaching the tool dispatcher or execution route creates `ToolExecutionAudit`, including contextless, unknown-tool, malformed-input, validation and policy denials. The outer execution context alone determines run ownership; an inner `agent_run_id` is ignored. Run-associated `ToolCall` projections share the authoritative attempt ID. `handler_invoked` and its timestamp are checkpointed before handler entry, independently of the final outcome; a failed outcome can therefore have `handler_invoked=true`.

The dispatcher owns a separate persistence boundary. It commits requested/validated/invoked checkpoints, then commits handler effects and success together. On exceptions it rolls back handler effects and finalizes failure in a separate transaction. Handlers may flush but cannot commit/rollback their dispatcher session. Orchestration commits run/step identities before dispatch. Caller rollback does not erase a completed tool audit. A database outage or process crash can leave a requested/invoked attempt without completion; that is not reported as success.

Snapshots are serializable, redacted for obvious credential keys/text, and bounded to 16 KiB each, with depth/item/string limits. Errors expose a generic user message and an internal exception-type diagnostic, not raw exception text. This is limited hygiene, not comprehensive secret classification. Existing historical records are not rewritten. Audit rows remain ordinary mutable SQL records, not a tamper-evident log.

See [Data Model](DATA_MODEL.md) and [Tool Registry](TOOL_REGISTRY.md) for storage and association details.

## API and host exposure

The [FastAPI application](../backend/app/main.py) has CORS configuration and response security headers, but no authentication, per-user authorization, rate limiting, or tenant isolation. CORS and headers do not prevent direct API access.

[docker-compose.yml](../docker-compose.yml) binds ports 3000, 8000 and 5432 to `127.0.0.1`. PostgreSQL uses local development credentials. Qdrant is not started. Loopback exposure does not supply authentication or protect against other local processes.

The explicit seeding and table-creation endpoints reject `ENVIRONMENT=production`, but that setting does not harden the application: harness/evaluation paths can still seed or reset data. Ordinary routes perform no DDL; schema initialization is an explicit command or development setup endpoint Use disposable fixture databases for these workflows and keep the API on a trusted local network boundary.

The current runner requires no external model keys. Unused provider, API-key and Qdrant configuration fields have been removed. Avoid placing credentials in browser-visible `NEXT_PUBLIC_*` settings.

## Interpreting evaluation

Security-harness outcomes show whether particular implemented checks fired for particular fixtures. Evaluation includes cohort-scoped counts and explicitly defined rates; it is not a certification of application security or a scientific measurement of model reliability.

See [Security Harness](SECURITY_HARNESS.md), [Evaluation](EVALUATION.md), and [API Reference](API_SPEC.md) for reproducible inputs, result semantics, and supported operations.
