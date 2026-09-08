# Investigation and Evaluation Walkthrough

This guide exercises the running API using a disposable local database. Start the services using the [Quick Start](../README.md#quick-start). The requests require curl; no model credentials or infrastructure connection are used.

## Seed and investigate

Seed the bundled alerts, documents, and illustrative history without requesting a reset:

```bash
curl --fail-with-body -X POST http://localhost:8000/api/v1/demo/seed \
  -H "Content-Type: application/json" \
  -d '{"reset": false}'
```

Investigate the bundled GPU alert:

```bash
curl --fail-with-body -X POST http://localhost:8000/api/v1/agent/runs \
  -H "Content-Type: application/json" \
  -d '{"alert_id":"909d28d2-5c9f-5fa2-a35e-f6b39c95f83f"}'
```

A successful response has `status: "waiting_for_human"`, an `agent_run_id`, step snapshots, an assessment, and a recommendation. A response with `status: "failed"` is an investigation failure even when the HTTP request succeeds.

Copy the returned run ID into the detail request:

```bash
curl --fail-with-body http://localhost:8000/api/v1/agent/runs/REPLACE_WITH_AGENT_RUN_ID
```

Review source references, recorded observations, missing evidence, and watchdog findings. Tool observations are deterministic local responses. A hypothesis's citations do not establish that its claims have been semantically verified.

For the retrieved-content injection example, use alert ID `e3e0e0d5-9e19-5243-a1f0-76c507be3641` with the same agent endpoint. These stable IDs identify bundled fixtures, not user-created incidents.

## Execute the harness and generate a report

Run the harness explicitly before evaluation:

```bash
curl --fail-with-body -X POST http://localhost:8000/api/v1/harness/run \
  -H "Content-Type: application/json" \
  -d '{"scenario_ids": null, "reset_demo_data": false}'

curl --fail-with-body -X POST http://localhost:8000/api/v1/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{"harness_run_id": "REPLACE_WITH_HARNESS_RUN_ID", "run_harness_if_empty": false, "report_type": "full"}'

curl --fail-with-body 'http://localhost:8000/api/v1/evaluation/report.md?evaluation_run_id=REPLACE_WITH_EVALUATION_ID'
curl --fail-with-body 'http://localhost:8000/api/v1/evaluation/report.json?evaluation_run_id=REPLACE_WITH_EVALUATION_ID'
```

Copy the harness response's execution ID into evaluation, then copy the evaluation response's ID into both report URLs. Check case pass/fail, test levels, and named mandatory-invariant failures individually. New executions never receive partial credit; `partial` is readable only for historical records. One scenario executes the full agent; two are component cases, five are policy cases, and one tests the tool boundary. See [scenario coverage](SECURITY_HARNESS.md).

The seed contains prewritten results labeled `fixture`. They cannot satisfy an execution requirement, including `run_harness_if_empty`. Reports evaluate one explicit executed cohort, show raw metric counts/denominators, and preserve scenario/provider/policy versions. The two exports identify the same stored cohort and remain unchanged after unrelated agent activity. See [evaluation formulas and scope](EVALUATION.md).

## Data and reset behavior

The seed operation upserts a fixed set of records; it can update sample history even with `reset: false`. The harness also reseeds data. Its default `reset_demo_data` is `false`, preserving existing history and Milestone 1 trust demotions.

Explicit reset recreates fixture records while retaining parents referenced by non-reset records. Foreign keys are enforced; deletion and reseeding commit atomically. Retained fixture parents may still be updated by the normal fixture upsert. Use a disposable database for reset experiments. Normal evaluation and harness requests do not need a reset.

The automated [integrity reproduction](../scripts/verify_evaluation_integrity.py) uses a disposable SQLite database to seed fixtures, execute a real harness, evaluate that ID, export both formats, perform unrelated agent activity, and verify that the stored exports remain byte-for-byte unchanged.

## Shell walkthrough

Run `bash scripts/demo_walkthrough.sh` from the repository root after explicit schema initialization and server startup. The helper checks readiness, reads JSON through [json_field.py](../scripts/json_field.py) without sharing stdin with Python source, preserves existing activity, evaluates the returned harness ID, and exports the matching stored report. Curl/python3 are required; jq is optional. `BASE_URL` or `API_URL` can select another local address. HTTP and extraction errors stop the script with a clear message.

## Troubleshooting

- **Connection refused:** confirm the backend is running and check `/api/v1/ready`.
- **Database connection error:** keep `DATABASE_URL` set in the server terminal; the default configuration targets PostgreSQL.
- **CORS settings error:** use a JSON array or comma-separated explicit HTTP(S) origins; see [Setup](SETUP.md).
- **Missing alert:** seed the same database used by the running backend.
- **Failed run:** inspect the run detail's `error_message` and failed step, rather than treating HTTP success as workflow success.
- **Stale evaluation:** report endpoints prefer the latest stored evaluation snapshot. Run evaluation explicitly to create a new snapshot.
