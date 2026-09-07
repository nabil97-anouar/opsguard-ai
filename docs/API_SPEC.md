# API Reference

The FastAPI service exposes JSON endpoints under `/api/v1` by default. With the backend running locally, use [Swagger UI](http://localhost:8000/docs) or the [OpenAPI schema](http://localhost:8000/openapi.json) for complete field definitions and response schemas. The prefix is configurable through `API_V1_PREFIX`.

Routes are registered in [app/main.py](../backend/app/main.py). This reference covers the routes currently implemented in [app/api/routes](../backend/app/api/routes).

## Access and request behavior

The API has no authentication or per-user authorization. Use it in a trusted local environment. CORS configuration and response security headers do not provide access control.

Agent, harness, and evaluation requests execute synchronously; they do not return background-job handles. A successful HTTP response can contain an application-level `failed` or `blocked` outcome. Check the response status, step errors, and watchdog findings.

Many data endpoints call table creation before accessing records. `GET /health` reports application/configuration state; `GET /db/health` actually tests the SQL connection.

## Endpoint inventory

All paths below are relative to `/api/v1`.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/health` | Application version, environment, and configured dependency labels |
| GET | `/db/health` | Database connectivity and latency |
| POST | `/db/create-tables` | Create missing SQL tables; explicit endpoint disabled when `ENVIRONMENT=production` |
| POST | `/demo/seed` | Seed fixture data; explicit endpoint disabled when `ENVIRONMENT=production` |
| POST | `/documents/ingest` | Insert or update a document and its chunks |
| GET | `/documents` | Document metadata list |
| POST | `/rag/retrieve` | Retrieve scored document excerpts with trust and scan metadata |
| GET | `/tools` | Tool definitions and input/output JSON schemas |
| POST | `/tools/{tool_name}/execute` | Invoke a registered local tool or return a blocked result |
| POST | `/agent/runs` | Run an investigation for an existing alert |
| GET | `/agent/runs` | Most recent 20 stored runs |
| GET | `/agent/runs/{agent_run_id}` | Run metadata, steps, tools, assessment, and recommendation |
| GET | `/watchdog/policies` | Seven implemented policy definitions |
| POST | `/watchdog/evaluate` | Evaluate caller-supplied context; does not persist this standalone decision |
| GET | `/harness/scenarios` | Available scenario definitions |
| POST | `/harness/run` | Run all or selected scenarios and persist results |
| GET | `/harness/results` | Most recent 50 scenario results |
| GET | `/harness/results/{harness_run_id}` | Aggregate and individual results for a harness run |
| POST | `/evaluation/run` | Calculate an evaluation and attempt to store its summary |
| GET | `/evaluation/summary` | Latest stored summary, or a calculation if none is available |
| GET | `/evaluation/report.md` | Evaluation report as `text/markdown` |
| GET | `/evaluation/report.json` | Structured evaluation report |
| GET | `/evaluation/scores` | Most recent 20 stored evaluation rows |

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

The response includes legacy `status` (`executed`, `blocked`, or `failed`), semantic `outcome` (`succeeded`, `blocked`, or `failed`), `tool_call_id`, `tool_name`, `trust_level`, `requires_human_approval`, `output`, `error`, and `created_at`. A run ID associates the call with the exact persisted investigation audit record; `tool_call_id` is null without run context. `GET /tools` exposes `executable` for each definition: seven local adapters are executable and five destructive definitions are blocked. Contextless calls and invalid requests have audit limitations described in [Tool Registry](TOOL_REGISTRY.md).

### Investigate an alert

`POST /agent/runs`:

```json
{"alert_id": "909d28d2-5c9f-5fa2-a35e-f6b39c95f83f"}
```

This ID identifies the seeded GPU alert. The response includes `agent_run_id`, `alert_id`, `steps`, `self_assessment`, and `final_recommendation`, with status `waiting_for_human` or `failed`.

Retrieve `/agent/runs/{agent_run_id}` for persisted tool calls, error details, provider metadata, and approval status. A pending approval is a terminal review state; there is no API to resume execution.

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

Optional context fields also include `retrieved_context`, `tool_results`, `hypotheses`, `evidence_items`, `planned_tools`, and `blocked_tools`. The response contains `status`, `summary`, and `findings`. Decision values are `allow`, `allow_with_warnings`, `require_human_approval`, and `block`. These checks do not authorize infrastructure execution.

### Run the security harness

`POST /harness/run`:

```json
{"scenario_ids": null, "reset_demo_data": false}
```

`scenario_ids=null` selects all scenarios; a list selects named scenarios from `GET /harness/scenarios`. `reset_demo_data` defaults to `true`; this example preserves existing fixture records where possible. The harness still seeds data and writes investigation/results records.

The response has status `completed`, a `harness_run_id`, aggregate `total`, `passed`, `failed`, `partial` counts, and individual `results`.

### Generate an evaluation

`POST /evaluation/run`:

```json
{"run_harness_if_empty": false, "report_type": "full"}
```

The response includes `persisted`, nullable `evaluation_score_id`, `summary`, and `scorecard`. If `run_harness_if_empty=true` (the default) and no harness rows exist, evaluation runs the harness with fixture reset enabled. `report_type` is a stored label, not a selector for different execution pipelines.

The report GET endpoints resolve the latest stored summary when available, so request a new evaluation to refresh a saved report. Reports contain deterministic engineering metrics, not a scientific assessment of model capability.

## Errors and schema sources

FastAPI rejects malformed typed request fields with HTTP 422. Missing agent/alert/harness resources and unknown tool names return 404; invalid ingestion content or harness selection can return 400. Database health failures return 503. Some internal failures surface as server errors or application-level failed results.

Request and response schemas live in [app/schemas](../backend/app/schemas). Detailed contracts are defined by [agent_run.py](../backend/app/schemas/agent_run.py), [rag.py](../backend/app/schemas/rag.py), [tools.py](../backend/app/schemas/tools.py), [watchdog.py](../backend/app/schemas/watchdog.py), [harness.py](../backend/app/schemas/harness.py), and [evaluation.py](../backend/app/schemas/evaluation.py).
