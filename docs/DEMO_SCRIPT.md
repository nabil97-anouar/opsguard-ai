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
  -d '{"run_harness_if_empty": false, "report_type": "full"}'

curl --fail-with-body http://localhost:8000/api/v1/evaluation/report.md
curl --fail-with-body http://localhost:8000/api/v1/evaluation/report.json
```

Check the harness's passed, partial, and failed cases individually. One scenario executes the full agent; the others exercise tool or watchdog components. See [scenario coverage](SECURITY_HARNESS.md).

The seed contains prewritten results. Evaluation does not automatically distinguish those from executed results, and its non-harness counters span broader database history. Explicit harness execution establishes which cases just ran, but it does not isolate every report metric. See [evaluation formulas and scope](EVALUATION.md).

## Data and reset behavior

The seed operation upserts a fixed set of records; it can update sample history even with `reset: false`. The harness also reseeds data. Its default `reset_demo_data` is `true`; the requests above explicitly use `false`.

Reset deletes fixed seeded IDs, not every dependent record created later. It can fail with foreign-key enforcement when later runs or evaluations reference those records. Use an isolated database for these procedures. The dashboard's harness button requests a reset and therefore has the same constraint.

## Existing shell helper

[scripts/demo_walkthrough.sh](../scripts/demo_walkthrough.sh) sequences similar operations, but currently has a known input-parsing defect: `json_field` supplies Python code and JSON through the same stdin stream. When Python is available, it fails while extracting the first run ID. Its harness request also enables reset.

Use the explicit requests above until the helper's parsing and reset handling are corrected.

## Troubleshooting

- **Connection refused:** confirm the backend is running and check `/api/v1/db/health`.
- **Database connection error:** keep `DATABASE_URL` set in the server terminal; the default configuration targets PostgreSQL.
- **CORS settings error:** use the JSON-array environment value in the Quick Start.
- **Missing alert:** seed the same database used by the running backend.
- **Failed run:** inspect the run detail's `error_message` and failed step, rather than treating HTTP success as workflow success.
- **Stale evaluation:** report endpoints prefer the latest stored evaluation snapshot. Run evaluation explicitly to create a new snapshot.
