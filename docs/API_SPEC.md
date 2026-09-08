# API Reference

The FastAPI service exposes JSON endpoints under `/api/v1` by default. With the backend running locally, use [Swagger UI](http://localhost:8000/docs) or the [OpenAPI schema](http://localhost:8000/openapi.json) for complete field definitions and response schemas. The prefix is configurable through `API_V1_PREFIX`.

Routes are registered in [app/main.py](../backend/app/main.py). This reference covers the routes currently implemented in [app/api/routes](../backend/app/api/routes).

## Access and request behavior

The API has no authentication or per-user authorization. Use it in a trusted local environment. CORS configuration and response security headers do not provide access control.

Agent, harness, and evaluation requests execute synchronously; they do not return background-job handles. A successful HTTP response can contain an application-level `failed` or `blocked` outcome. Check the response status, step errors, and watchdog findings.

Ordinary data endpoints never create or alter tables. Run `python -m app.db.init_db` explicitly before serving requests; the development create-table/seed endpoints are also explicit setup operations. `GET /health` checks liveness, `/ready` checks SQL connectivity and schema readiness, and `/db/health` remains a connectivity-only probe.

## Endpoint inventory

All paths below are relative to `/api/v1`.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/health` | Liveness only: version, environment, deterministic reasoner, timestamp; no dependency checks |
| GET | `/ready` | SQL connection plus required tables/columns; 200 ready or 503 unavailable/schema missing; no DDL |
| GET | `/db/health` | Database connectivity and latency |
| POST | `/db/create-tables` | Create missing SQL tables; explicit endpoint disabled when `ENVIRONMENT=production` |
| POST | `/demo/seed` | Seed fixture data; explicit endpoint disabled when `ENVIRONMENT=production` |
| POST | `/documents/ingest` | Insert or update a document and its chunks |
| GET | `/documents` | Document metadata list |
| POST | `/rag/retrieve` | Retrieve scored document excerpts with trust and scan metadata |
| GET | `/tools` | Tool definitions and input/output JSON schemas |
| POST | `/tools/{tool_name}/execute` | Audit the attempt, enforce application policy, then dispatch or deny |
| GET | `/tools/attempts` | Latest 100 authoritative tool attempts; optional `agent_run_id` filter |
| POST | `/agent/runs` | Run an investigation for an existing alert |
| GET | `/agent/runs` | Most recent 20 stored runs |
| GET | `/agent/runs/{agent_run_id}` | Run metadata, steps, tools, assessment, and recommendation |
| GET | `/watchdog/policies` | Eight implemented policy definitions |
| POST | `/watchdog/evaluate` | Review supplied proposals against persisted same-run source evidence; does not persist this standalone decision |
| GET | `/harness/scenarios` | Available scenario definitions |
| POST | `/harness/run` | Run all or selected scenarios and persist results |
| GET | `/harness/results` | Most recent 50 scenario results |
| GET | `/harness/results/{harness_run_id}` | Aggregate and individual results for a harness run |
| POST | `/evaluation/run` | Evaluate a completed executed harness cohort and store a new snapshot |
| GET | `/evaluation/summary` | Latest stored current-format summary, or labeled live preview of the latest eligible execution |
| GET | `/evaluation/report.md` | Stored report as `text/markdown`; optional `evaluation_run_id` query |
| GET | `/evaluation/report.json` | Same stored report as JSON; optional `evaluation_run_id` query |
| GET | `/evaluation/scores` | Report-history envelopes with origin/report-kind labels |

The list endpoints above do not expose configurable pagination. There are no alert CRUD, approval/rejection, feedback submission, ticket export, or per-incident report endpoints.

## Request examples

These are request bodies for the named endpoints. Replace example run/alert UUIDs with existing record IDs.

### Seed fixtures

`POST /demo/seed`:

```json
{"reset": false}
```

`reset` defaults to `false`. Resetting changes fixture-related database records. Use a disposable local database for harness and reset workflows; see [Local Walkthrough](DEMO_SCRIPT.md).

### Ingest a document

`POST /documents/ingest`:

```json
{
  "title": "GPU ownership investigation",
  "source": "manual://gpu-ownership",
  "doc_type": "runbook",
  "trust_level": "untrusted",
  "content": "Confirm the workload owner and preserve process and network evidence.",
  "metadata": {"tags": ["gpu", "ownership"]}
}
```

The response includes `status`, `document_id`, `created`, `updated`, `skipped`, and `chunk_count`. The source is a label, not a URL-fetch instruction. Public `trust_level` defaults to `untrusted` and accepts only `untrusted` or `quarantined`. Invalid labels and trusted declarations, including metadata trust labels, return HTTP 422. There is no public trusted-ingestion override or trust-promotion endpoint.

Updates identify a source by title and source label. Demotions apply to existing chunks even when content is unchanged, and later ingestion cannot remove existing restrictions or release quarantine. Trust labels remain local policy assertions; ingestion does not authenticate source ownership.

### Retrieve context

`POST /rag/retrieve`:

```json
{
  "query": "gpu workload ownership",
  "limit": 5,
  "trust_filter": null,
  "include_untrusted": false
}
```

The response contains `status`, `query`, and `results`. Results include document/chunk IDs, title, source, type, index, effective trust level, lexical score, excerpt, citation, and injection indicators. The API default for `include_untrusted` is `true`; the example selects trusted-only retrieval. `trust_filter` accepts only the three canonical labels, with exact matching; quarantined content is always excluded. Empty or lexically irrelevant queries return an empty `results` list. Trust never creates a positive score.

`GET /documents` reports each document's normalized document-level trust label, while retrieval can apply stricter chunk/metadata restrictions. See [Retrieval and Evidence](RAG_DESIGN.md) for filtering and grounding limits.

### Execute a tool

`POST /tools/search_logs/execute`:

```json
{
  "input": {"query": "xmrig mining pool", "limit": 5},
  "agent_run_id": null
}
```

The response includes legacy `status` (`executed`, `blocked`, or `failed`), canonical `outcome` (`succeeded`, `denied`, or `failed`), `handler_invoked`, `error_code`, `tool_call_id`, `tool_name`, `trust_level`, `requires_human_approval`, bounded `output`, user-safe `error`, and `created_at`. The call ID identifies a durable `ToolExecutionAudit`, including requests without run context. Only the outer `agent_run_id` owns the execution; inner IDs are ignored. Invalid run/step ownership is denied before invocation.

Unknown tools return 404 and malformed/invalid inputs return 422 with structured `detail`: `message`, `tool_call_id`, `outcome: denied`, `handler_invoked: false` (schema validation adds `errors` without raw input). Policy denial and handler failure return 200 with the application outcome. Bodies over 64 KiB are denied and audited. Audit snapshots are bounded/redacted, and raw exception text is not returned or persisted.

`GET /tools/attempts?agent_run_id=UUID` lists matching recent attempts, or all recent attempts without the filter. Each row exposes `id`, outer run/step IDs, requested tool/origin, input snapshot, authorized target, `validated`, outcome, `handler_invoked`, requested/invoked/completed timestamps, output snapshot, error code, user error and diagnostic exception type. `requested`, `validated` or `invoked` without completion is an incomplete attempt, not success. This list is live activity, not a stored evaluation cohort.

`GET /tools` exposes `executable` for each definition: seven local adapters are executable and five destructive definitions are blocked. Ticket input now contains only `title` and `body`, with run ID in the envelope. Its output adds `lifecycle_state`, `policy_validation`, and `policy_version`; direct calls produce unreviewed candidates. See [Tool Registry](TOOL_REGISTRY.md) for authorization and transaction ownership.

### Investigate an alert

`POST /agent/runs`:

```json
{"alert_id": "909d28d2-5c9f-5fa2-a35e-f6b39c95f83f"}
```

This ID identifies the seeded GPU alert. The response includes `agent_run_id`, `alert_id`, `steps`, `self_assessment`, and `final_recommendation`, with status `waiting_for_human` or `failed`.

Retrieve `/agent/runs/{agent_run_id}` for persisted tool calls and authoritative `tool_attempts`, error details, provider metadata, and approval status. The final recommendation adds typed `proposed_actions`, `lifecycle_state`, `review_valid`, `policy_version` and `watchdog_decision`. A pending approval is a terminal review state; there is no API to resume execution.

### Evaluate a recommendation

`POST /watchdog/evaluate`:

```json
{
  "alert": {"severity": "critical"},
  "self_assessment": {
    "confidence_score": 0.4,
    "missing_evidence": ["Confirmed workload owner"]
  },
  "final_recommendation": {
    "summary": "Request operator review.",
    "evidence": [],
    "citations": [],
    "recommended_next_steps": ["Confirm workload ownership."],
    "blocked_actions_requiring_human_approval": [],
    "notes": []
  }
}
```

For an actual action review, supply `agent_run_id` and `proposed_actions` with `action_id` (optional generated UUID), constrained `action_type`, optional `target`, `parameters`, `risk_level`, `requires_approval`, `supporting_evidence_ids` and `rationale`. Supported types are declared in [actions.py](../backend/app/agent/actions.py). Normalized equivalent type spellings resolve to the enum; unknown types and conflicting/duplicate action IDs return 422. Proposals nested in `final_recommendation.proposed_actions` are also validated.

Optional context fields include `retrieved_context`, `tool_results`, `hypotheses`, `evidence_items`, `planned_tools`, and `blocked_tools`. Supplied evidence is not authoritative: the endpoint resolves the selected run's persisted source-node ledger and verified tool calls. A nonexistent run or unresolved/empty claim references causes `grounding_reference_integrity` findings. The example above intentionally lacks support and blocks; it is not a valid reviewed artifact.

The response contains exact `verdict` (`allow`, `allow_with_warnings`, `require_human_approval`, or `block`), compatibility `status` with the same value, severity, `blocking`, `mandatory_review`, `reason`, `summary`, `policy_version`, finding IDs, affected action IDs, and typed findings. Findings expose ID/type, policy ID, severity, status, affected actions, blocking/review flags, reason, references and remediation. These are structural/pattern policy results, not semantic grounding or dispatch authorization. Standalone evaluation does not persist or promote any artifact.

### Run the security harness

`POST /harness/run`:

```json
{"scenario_ids": null, "reset_demo_data": false}
```

`scenario_ids=null` selects all scenarios; a list selects named scenarios from `GET /harness/scenarios`. `reset_demo_data` defaults to `false`. The harness still seeds input data and writes execution/result records. Fixture history has `fixture` provenance; newly observed outcomes have `executed` provenance. Existing unidentified results are `legacy_unknown`.

The response includes execution `status`, `harness_run_id`, provenance, start/end timestamps, expected/completed case counts, provider/policy versions, scenario manifest, aggregate `total`, `passed`, `failed`, `partial` counts, and individual `results`. New executions are binary pass/fail; `partial` remains for reading historical records. Each result identifies test level, scenario version, explicit expectations, observations, mandatory invariants/failures, and required/reached human review.

Reading a fixture group without a manifest returns `status: not_executed`; an unidentified legacy group returns `status: legacy_unknown`. Their completed execution count is zero and expected count is null. Stored row totals do not establish scenario completion.

### Generate an evaluation

`POST /evaluation/run`:

```json
{"harness_run_id": "REPLACE_WITH_EXECUTED_HARNESS_UUID", "run_harness_if_empty": false, "report_type": "full"}
```

The response includes `persisted`, `evaluation_run_id`, and `summary`. The summary identifies its `report_kind`, metric-definition version, exact `cohort`, scenario snapshots, failed cases, mandatory-invariant failures, and limitations. `metrics` is a dictionary of `{numerator, denominator, value, unit, definition}` objects; a zero denominator gives `value:null`. There is no scorecard or overall safety score.

Omit `harness_run_id` to select the latest completed executed manifest. If none exists and `run_harness_if_empty=true` (the default), evaluation executes the harness. Seeded fixture rows cannot prevent that execution; an explicitly selected fixture/non-execution is rejected. `report_type` remains a descriptive label.

Use `?evaluation_run_id=UUID` on both report exports to select the same stored snapshot. Later unrelated activity does not change it. Without an ID, GET endpoints return the latest current report or an explicitly labeled live preview of the latest eligible execution (empty if none exists). Historical `/evaluation/scores` envelopes label old payloads `legacy_archive` with `legacy_unknown` provenance and do not turn them into current executed reports. See [Evaluation](EVALUATION.md) for exact metric definitions and compatibility details.

## Errors and schema sources

FastAPI rejects malformed typed request fields with HTTP 422. Missing agent/alert/harness resources and unknown tool names return 404; invalid ingestion content or harness selection can return 400. Database health failures return 503. Unhandled HTTP failures return a generic 500 with a generated `request_id`, also exposed as `X-Request-ID` on every response. Logs record the exception class and correlation ID without exception text or request bodies. Database probe errors never expose connection strings. Workflow failures may still be represented as application-level failed results.

Request and response schemas live in [app/schemas](../backend/app/schemas). Detailed contracts are defined by [agent_run.py](../backend/app/schemas/agent_run.py), [rag.py](../backend/app/schemas/rag.py), [tools.py](../backend/app/schemas/tools.py), [watchdog.py](../backend/app/schemas/watchdog.py), [harness.py](../backend/app/schemas/harness.py), and [evaluation.py](../backend/app/schemas/evaluation.py).
