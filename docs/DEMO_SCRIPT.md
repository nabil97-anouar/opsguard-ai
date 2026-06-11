# Demo Walkthrough Script

`./scripts/demo_walkthrough.sh` is the fastest way to exercise OpsGuard AI end to end on a local machine.

## What It Does

The script is intentionally safe and local-only. It:

1. checks `GET /api/v1/health`
2. seeds the deterministic demo dataset
3. runs the GPU abuse agent scenario
4. runs the prompt-injection agent scenario
5. runs the security harness
6. runs the evaluation summary/report generation
7. fetches the Markdown evaluation report

It does not execute infrastructure actions, shell into hosts, or call any external LLM API.

## Prerequisites

- backend running on `http://localhost:8000`
- `curl`
- optional: `jq` for prettier JSON output

If `jq` is not installed, the script falls back to `python3 -m json.tool` when available, or raw JSON output.

## Run It

```bash
./scripts/demo_walkthrough.sh
```

## Stable Demo Alert IDs

The demo seed uses deterministic UUIDs, so the script can safely target stable alert IDs:

- GPU abuse alert: `909d28d2-5c9f-5fa2-a35e-f6b39c95f83f`
- Prompt-injection alert: `e3e0e0d5-9e19-5243-a1f0-76c507be3641`

## Expected Output Sections

You should see these section headers:

- `1. Backend health`
- `2. Seed deterministic demo data`
- `3. Run GPU abuse agent scenario`
- `4. Run prompt-injection agent scenario`
- `5. Run security harness`
- `6. Run evaluation`
- `7. Fetch Markdown safety report`

The exact JSON payloads can evolve slightly, but the high-level flow should stay stable.

## Troubleshooting

If the script fails at the health check:

- make sure the backend is running on port `8000`
- confirm you activated the backend virtual environment
- retry `curl http://localhost:8000/api/v1/health`

If the script prints raw JSON instead of pretty output:

- install `jq`, or
- keep using the fallback output; the script is still working

If the agent or harness requests fail:

- rerun the seed step manually:
  - `curl -X POST http://localhost:8000/api/v1/demo/seed -H "Content-Type: application/json" -d '{"reset": false}'`
- then retry the script

## Why This Exists

This walkthrough is part of the portfolio story. It gives reviewers a single command that demonstrates:

- grounded retrieval
- safe mock tools
- self-assessment
- watchdog gating
- adversarial harness coverage
- evaluation/report export
