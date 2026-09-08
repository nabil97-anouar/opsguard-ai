# Tool Registry

OpsGuard exposes a closed registry of typed local tools through Python and REST. Each definition declares input/output schemas, a trust label, descriptive usage guidance, and approval metadata. Executable local adapters have implementation handlers; blocked action definitions do not. There is no MCP protocol server or external infrastructure connection.

## Registry and execution

[ToolDefinition](../backend/app/tools/base.py) is an immutable dataclass. [get_tool_registry](../backend/app/tools/registry.py) returns a cached read-only mapping. Its `executable` property requires a handler, `is_destructive=false`, and `requires_human_approval=false`. `execute_tool` records the request, validates input and run/step ownership, then enforces application policy before handler dispatch. Fixed destructive identities remain blocked even if their definition flags are corrupted. Approval-required nondestructive definitions return `approval_required`; absent handlers return `handler_unavailable`. Broad target selectors are denied. Output is schema-validated before a successful observation is recorded. Non-executable definitions return a denial without invoking an operational handler.

Results retain legacy `status` values `executed`, `blocked`, or `failed` for existing observation consumers and expose canonical `outcome` values `succeeded`, `denied`, or `failed`. They include `handler_invoked`, `error_code`, tool name, trust label, approval flag, bounded output/error, request timestamp, and an authoritative `tool_call_id`, including contextless calls. Unknown names return HTTP 404; invalid input/envelopes return HTTP 422. Both contain an audit ID, `outcome: denied`, and `handler_invoked: false` in `detail`. Invalid output or a handler exception produces `failed`, `handler_invoked: true` and empty output; it cannot support evidence.

## Available tools

| Tool | Implementation | Input | Output trust |
| --- | --- | --- | --- |
| `search_logs` | Lexical search over fixed local log entries | `query`, optional `limit` | `untrusted` |
| `get_node_metrics` | Fixed metrics for a known fixture node | `node` | `untrusted` |
| `get_running_jobs` | Fixed jobs, optionally filtered | Optional `node`, `user` | `untrusted` |
| `check_network_connections` | Fixed outbound connection records | `node`, optional `limit` | `untrusted` |
| `query_past_incidents` | Lexical search over SQL incident records | `query`, optional `limit` | `trusted` |
| `retrieve_runbook` | Local document retrieval, filtered to runbooks | `query`, optional `limit`, `include_untrusted` | `untrusted` |
| `create_ticket_draft` | Insert a local ticket linked to an existing run | `title`, `body`; run from execution context | `trusted` |
| `cancel_job`, `drain_node`, `block_user`, `isolate_node`, `disable_service` | Permanently blocked definitions | Arbitrary fields retained for the blocked attempt | `untrusted`; denial is not evidence |

Handlers and Pydantic schemas are defined in [implementations.py](../backend/app/tools/implementations.py). Infrastructure responses come from [mock_data.py](../backend/app/tools/mock_data.py). Incident lookup, runbook retrieval, and ticket persistence operate on the local database. Ticket creation does not send data to an external service.

All five destructive definitions have `handler=None` and `executable=false`. The dispatcher constructs a blocked response. Their returned approval flag does not offer a way to authorize execution.

## REST usage

`GET /api/v1/tools` lists definitions, including JSON schemas, usage metadata, and the explicit `executable` capability. The dashboard separates seven executable adapters from five blocked definitions.

For `POST /api/v1/tools/search_logs/execute`:

```json
{
  "input": {"query": "xmrig mining pool", "limit": 5},
  "agent_run_id": null
}
```

Attach the active run ID in the outer envelope when invoking a tool as part of an investigation. Inner `input.agent_run_id` is removed before validation and never controls audit or ticket ownership. Ticket creation requires a persisted outer run. No supplied approval field grants permission.

See [API Reference](API_SPEC.md) for response behavior.

## Trust and audit behavior

The registry uses the canonical `trusted`, `untrusted`, and `quarantined` trust type. A trusted output label identifies the adapter's configured category; it does not verify every free-text statement in that output. Retrieved runbook results also retain their individual effective document/chunk trust labels. Blocking is an execution outcome, not a fourth trust state. Historical audit rows may retain the former `restricted` label; new blocked calls use `untrusted` and never provide supporting evidence.

`ToolExecutionAudit` is authoritative for every attempt. It records requested tool, outer run/step context, origin, bounded input, authorized target, outcome, schema-validation flag, independent invocation flag, request/invocation/completion timestamps, output, error code, user-safe message, and diagnostic exception type. `GET /api/v1/tools/attempts` returns the latest 100 attempts, optionally filtered by `agent_run_id`; this is live history, not an evaluation cohort. The run detail response also includes `tool_attempts`.

The lifecycle is `requested` → `validated` → `invoked` → `succeeded` or `failed`; rejection produces `denied` without invocation. Missing completion remains visibly incomplete. An unknown run/step context can still be audited, so these audit links are logical references without foreign-key constraints. [record_tool_call](../backend/app/tools/audit.py) creates a compatible observation projection only for valid run/step context, sharing the audit ID. Manual calls may receive a synthetic step. Destructive denials also create a safety event; other denial types do not masquerade as destructive attempts.

The dispatcher owns a separate database transaction boundary. Orchestrators commit run/step identities before dispatch. Requested and invocation checkpoints become durable before handler entry; successful handler effects and the success audit commit together. Failed handler effects roll back, then a separate transaction records failure. Handlers may add/flush but cannot independently commit/rollback their session. A caller rollback cannot erase the completed audit. This covers local SQL effects, not arbitrary external side effects.

Snapshots use the [bounded serializer](../backend/app/tools/hygiene.py): 16 KiB maximum per snapshot, depth 6, 256 visited values, 40 entries per collection, and 2048 characters per string. Obvious credential keys and token/password patterns are redacted. Exception text is not persisted; diagnostics retain only the exception class. Unsupported objects and non-finite numbers become explicit markers. Consumers receive the same sanitized output that is persisted.

Ticket output includes `lifecycle_state`, `policy_validation`, and `policy_version`. Direct requests create `candidate`/`not_evaluated` drafts. The workflow passes its internal watchdog decision only after persisting policy review, creating either `pending_human_review` or `blocked` drafts marked `evaluated`. Neither state is human approval.

The agent scans tool outputs and surfaces untrusted or suspicious results in its assessment and watchdog input. Only successful observations with persisted call identity can supply supporting evidence. Failed and blocked attempts remain trace/audit information. Missing node, job, or user targets create evidence gaps; the planner omits affected tools and action recommendations instead of filling fixture values. Explicit node arguments must be nonblank. Tool output text does not become executable code.

## Current limits

- Contextless calls have authoritative attempt records but no legacy `ToolCall` projection. Old rows retain `handler_invoked: null` and `outcome: legacy_unknown`; success prose cannot reconstruct invocation.
- Audit finalization requires a working database. Crashes can leave incomplete checkpoints; there is no automatic recovery/resume or tamper-evident storage.
- Usage descriptions are documentation, not actor/resource authorization. The registry has no authenticated principal or resource permission model.
- Historical runs created before evidence snapshots were introduced may lack unique invocation references; their missing evidence is not reconstructed from current tools or documents.

Adding a real adapter requires explicit authorization and failure-handling design in addition to a typed schema. Existing local adapters do not provide production integration behavior.
