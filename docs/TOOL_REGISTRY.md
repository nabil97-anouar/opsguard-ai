# Tool Registry

OpsGuard exposes a closed registry of typed local tools through Python and REST. Each definition declares input/output schemas, a trust label, descriptive usage guidance, and approval metadata. Executable local adapters have implementation handlers; blocked action definitions do not. There is no MCP protocol server or external infrastructure connection.

## Registry and execution

[ToolDefinition](../backend/app/tools/base.py) is an immutable dataclass. [get_tool_registry](../backend/app/tools/registry.py) returns a cached read-only mapping. Its `executable` property requires a handler, `is_destructive=false`, and `requires_human_approval=false`. `execute_tool` validates input and enforces that capability before calling a handler, then validates successful output and returns a structured result. Non-executable definitions return a denial without invoking an operational handler.

Results retain legacy `status` values `executed`, `blocked`, or `failed` for audit compatibility and expose semantic `outcome` values `succeeded`, `blocked`, or `failed`. They include the tool name, trust level, approval flag, output, error, timestamp, and the exact persisted `tool_call_id` when run context is supplied. Contextless calls return a null call ID. Unknown names are rejected. Invalid input returns HTTP 422 before execution; invalid adapter output produces an audited `failed` outcome with empty output and cannot supply supporting evidence.

## Available tools

| Tool | Implementation | Input | Output trust |
| --- | --- | --- | --- |
| `search_logs` | Lexical search over fixed local log entries | `query`, optional `limit` | `untrusted` |
| `get_node_metrics` | Fixed metrics for a known fixture node | `node` | `untrusted` |
| `get_running_jobs` | Fixed jobs, optionally filtered | Optional `node`, `user` | `untrusted` |
| `check_network_connections` | Fixed outbound connection records | `node`, optional `limit` | `untrusted` |
| `query_past_incidents` | Lexical search over SQL incident records | `query`, optional `limit` | `trusted` |
| `retrieve_runbook` | Local document retrieval, filtered to runbooks | `query`, optional `limit`, `include_untrusted` | `untrusted` |
| `create_ticket_draft` | Insert a local ticket linked to an existing run | `agent_run_id`, `title`, `body` | `trusted` |
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

Attach the active run ID when invoking a tool as part of an investigation. For ticket drafts, the run ID in `input` and the outer `agent_run_id` should identify the same run.

See [API Reference](API_SPEC.md) for response behavior.

## Trust and audit behavior

The registry uses the canonical `trusted`, `untrusted`, and `quarantined` trust type. A trusted output label identifies the adapter's configured category; it does not verify every free-text statement in that output. Retrieved runbook results also retain their individual effective document/chunk trust labels. Blocking is an execution outcome, not a fourth trust state. Historical audit rows may retain the former `restricted` label; new blocked calls use `untrusted` and never provide supporting evidence.

[record_tool_call](../backend/app/tools/audit.py) stores validated arguments, output, status, timing, and injection scan status when an agent-run context is supplied. A manual invocation may attach to an existing step or receive a synthetic audit step. Blocked destructive attempts additionally create a safety event.

The agent scans tool outputs and surfaces untrusted or suspicious results in its assessment and watchdog input. Only successful observations with persisted call identity can supply supporting evidence. Failed and blocked attempts remain trace/audit information. Missing node, job, or user targets create evidence gaps; the planner omits affected tools and action recommendations instead of filling fixture values. Explicit node arguments must be nonblank. Tool output text does not become executable code.

## Current limits

- Calls without run context do not create a `ToolCall` row. Unknown tools and input validation failures are not comprehensively audited.
- Ticket input and audit context use separate run IDs; the current API does not reject a mismatch.
- Usage descriptions are documentation, not actor/resource authorization. The registry has no authenticated principal or resource permission model.
- Historical runs created before evidence snapshots were introduced may lack unique invocation references; their missing evidence is not reconstructed from current tools or documents.

Adding a real adapter requires explicit authorization and failure-handling design in addition to a typed schema. Existing local adapters do not provide production integration behavior.
