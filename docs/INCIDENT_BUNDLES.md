# Investigate an incident bundle

An incident bundle is a bounded JSON record containing one alert and the observations you want OpsGuard to inspect. It is an import format, not a live integration: export the data from your monitoring system, remove secrets, and choose the file in Investigations. The browser automatically prepares the JSON bundle; the API accepts that canonical JSON format.

Importing only stores the data. Starting an investigation runs the configured reasoning provider. If a remote provider is selected, the alert and bounded evidence context are transmitted to that service. Start with deterministic mode and the synthetic examples when testing the workflow.

## Files and automatic conversion

The file picker accepts `.log`, `.txt`, `.md`, `.csv`, `.jsonl`, `.ndjson`, and `.json`. Conversion runs entirely in the browser, without a model request or uploading the file. It also works while the backend is disconnected. The preview shows conversion notes and the prepared JSON; **Download JSON** saves it locally. **Save evidence** is the separate action that sends it to the backend, and **Run investigation** starts reasoning only after that.

Existing versioned incident bundles retain their typed observations. Ordinary JSON records, JSONL entries, CSV rows, and plain text are preserved as untrusted log observations. This preserves their supplied content; it does not claim to understand arbitrary monitoring schemas or infer an incident's cause. Recognized host, severity, and timezone-aware timestamp fields supply metadata when available. Source labels are derived from the filename; any original source field stays in the log content. Conversion never invents a host or event time. Unknown metadata remains null and is recorded as an evidence gap.

Long content is split into bounded observations without silently discarding the remainder. More than 32 observations or a file over 1 MiB is rejected with a request to export a smaller incident window. Malformed `.json` syntax is preserved verbatim as an untrusted text observation with an explicit conversion warning; it is not repaired or interpreted as JSON. Parsed but invalid canonical bundles, duplicate JSON keys, and malformed JSONL/CSV produce actionable errors rather than discarding records. PDF, Word, archives, and binary files are not parsed; export their relevant contents as text or CSV first.

Conversion uses a descriptive file-derived title/source label. Any default severity is disclosed in the conversion notes; it is not an independent security assessment. Inspect the preview before import. The backend still validates the complete canonical bundle and applies its snapshot budgets and limited credential redaction.

### Journal and syslog exports

Common journal prefixes such as `Apr 07 13:53:49 compute-07 kernel:` identify the host explicitly. The converter extracts that host, preserves the original lines and separators, and groups adjacent lines into bounded evidence chunks. The preview distinguishes source lines from stored chunks; neither count represents detected incidents.

Short journal dates omit a year and timezone, so their event time remains unknown. Full ISO timestamps with an explicit timezone are retained when a chunk has a single event time. Chunks containing several event times keep those times in the source text and leave the single timestamp field empty. Unknown lines do not inherit metadata from neighboring lines, and different hosts are not combined into one attributed chunk. No year, timezone, or severity is inferred from log wording.

For an export with explicit timestamps, run `journalctl -o short-iso-precise` on the source system using your normal access and incident-window filters. OpsGuard itself does not execute that command or connect to the machine.

## Format

```json
{
  "schema_version": "incident-bundle-v1",
  "incident": {
    "title": "GPU utilization above the expected range",
    "description": "Investigate whether the observed workload matches its allocation.",
    "severity": "warning",
    "source": "manual://monitoring-export",
    "observed_at": "2026-09-22T10:00:00Z",
    "infrastructure_type": "gpu_cluster",
    "node": "compute-07"
  },
  "observations": [
    {
      "kind": "log",
      "source": "manual://scheduler-log",
      "observed_at": "2026-09-22T09:59:00Z",
      "node": "compute-07",
      "message": "Allocated training job started within its requested GPU quota."
    },
    {
      "kind": "metric",
      "source": "manual://metrics-export",
      "observed_at": "2026-09-22T10:00:00Z",
      "node": "compute-07",
      "name": "gpu_utilization",
      "value": 91,
      "unit": "percent"
    }
  ]
}
```

Supplied timestamps must include a timezone. Event timestamps and node identifiers may be null or omitted when unknown; they are never filled with fixture values. Source values are labels, not URLs to fetch. The server generates bundle and observation identifiers; callers cannot set trust, evidence IDs, or arbitrary extra fields.

| Field | Requirements |
| --- | --- |
| `schema_version` | Exactly `incident-bundle-v1` |
| `incident` | Title, description, severity, and source; optional event timestamp, node, job ID, user, and infrastructure type |
| `incident.severity` | `info`, `warning`, `high`, or `critical` |
| `observations` | Zero to 32 records, each with a typed kind and source; node and timezone-aware timestamp may be unknown |
| `log` | `message`; optional severity |
| `metric` | `name`, finite numeric `value`; optional unit |
| `job` | `job_id`, `user`, `command`, `status` |
| `network` | Valid IPv4/IPv6 `remote_ip`, integer `remote_port` (1–65535); optional process |

The transport limit is 1 MiB. Title length is at most 500 characters; description, log message, and job command at most 2000. Most source/target identifiers are bounded at 100 characters. The incident must fit 4,000 bytes and each observation 12,000 bytes when serialized as ASCII JSON, preserving room in the evidence/provider envelopes and audited tool output. These budgets apply to the retained redacted snapshot too. The [Pydantic schemas](../backend/app/services/incident_schema.py) and running OpenAPI schema are authoritative for field defaults and all limits.

A bundle can contain no observations, so an incomplete alert can be reviewed honestly. It must produce explicit gaps, never generated fixture observations. Split larger investigations into deliberate bounded inputs rather than assuming the importer silently truncates them.

## Included examples

- [Normal workload](../examples/incidents/normal-workload.json): legitimate workload context; high utilization does not establish abuse.
- [Suspicious activity](../examples/incidents/suspicious-activity.json): observations that warrant investigation, with attribution still requiring review.
- [Insufficient evidence](../examples/incidents/insufficient-evidence.json): missing observations and targets remain gaps.
- [Malicious log](../examples/incidents/malicious-log.json): embedded instructions remain untrusted evidence and are screened; they cannot authorize tools.

These are synthetic records for local reproduction. Their outcomes are regression examples, not a benchmark of live-model reliability.

## Dashboard workflow

1. Open Investigations and choose a supported file. Review the automatically prepared JSON and conversion notes; optionally download it.
2. Import it and check the receipt's observation count and untrusted status.
3. Confirm the selected reasoning provider, then start the imported investigation.
4. Inspect its evidence, trace, assessment, and policy result. Failed requests are not successful investigations.
5. Download the selected run's Markdown or JSON report. A successful run ends at human review; OpsGuard does not execute the proposed operational response.

Choosing a new file clears the previous investigation's displayed results and export links. Importing alone does not create a report. After running, check the incident title and run identifier above the report links. Use the recorded-run selector explicitly when you want a historical investigation.

Bundled scenarios remain available separately. Importing does not seed the scenario database. The imported path skips global document retrieval, prior-incident search, and fixture-backed observations. Existing documents are therefore not automatically consulted for imported bundles in this release.

## API workflow

From the repository root, with the backend running:

```bash
curl --fail-with-body http://localhost:8000/api/v1/incidents/import \
  -H 'Content-Type: application/json' \
  --data-binary @examples/incidents/normal-workload.json
```

The 201 response contains `bundle_id`, `alert_id`, `observation_count`, `imported_at`, and `trust_level: untrusted`. Copy its `alert_id` into:

```bash
curl --fail-with-body http://localhost:8000/api/v1/agent/runs \
  -H 'Content-Type: application/json' \
  -d '{"alert_id":"REPLACE_WITH_RETURNED_ALERT_ID"}'
```

Copy the returned `agent_run_id` into the report requests:

```bash
curl --fail-with-body \
  http://localhost:8000/api/v1/agent/runs/REPLACE_WITH_RUN_ID/report.md \
  -o investigation.md
curl --fail-with-body \
  http://localhost:8000/api/v1/agent/runs/REPLACE_WITH_RUN_ID/report.json \
  -o investigation.json
```

Inspect the run's `status` even after HTTP 200. Configuration errors may reject a run; provider or workflow errors can produce a persisted failed run. A report of an incomplete run is a record of that attempt, not a completed assessment.

## Evidence and historical guarantees

The saved ingest step binds the run to its bundle. A dedicated local adapter reads individual recorded observations, yielding unique tool-call and observation identities. It cannot fall back to fixture data even when an imported node has the same name as a fixture node.

Each successful observation retains its source, original time when supplied, content snapshot, and untrusted status. `timestamp_basis: source_observation` identifies a supplied source time; `recorded` identifies the application recording time when the event time is unknown. The source content keeps its null event time. Older evidence without this optional field remains readable without inventing a basis. Failed or denied attempts remain audit records. Models cannot assign trust or alter the stored source ledger. Observation content is screened for configured injection patterns; a clean scan never promotes trust.

Reports render persisted run records. They do not rerun the model, search current documents, refresh the imported alert, or execute tools. Editing the current alert/document catalog does not rewrite a historical report's source snapshot. SQL administrators can still alter stored records; the database is not tamper-evident storage.

OpsGuard validates source identity and output structure, not source authenticity or semantic truth. Deterministic import reasoning stays conservative about observations and gaps. External-model findings require operator review even if all structural checks pass.
