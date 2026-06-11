#!/usr/bin/env bash

set -euo pipefail

BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api/v1"
GPU_ALERT_ID="909d28d2-5c9f-5fa2-a35e-f6b39c95f83f"
PROMPT_ALERT_ID="e3e0e0d5-9e19-5243-a1f0-76c507be3641"

print_header() {
  printf '\n============================================================\n'
  printf '%s\n' "$1"
  printf '============================================================\n'
}

pretty_json() {
  if command -v jq >/dev/null 2>&1; then
    jq .
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool 2>/dev/null || cat
    return
  fi

  cat
}

json_field() {
  local path="$1"

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$path" <<'PY'
import json
import sys

path = sys.argv[1].split(".")
data = json.load(sys.stdin)
value = data
for part in path:
    if part.isdigit():
        value = value[int(part)]
    else:
        value = value.get(part)
print("" if value is None else value)
PY
    return
  fi

  printf ''
}

request_json() {
  local method="$1"
  local path="$2"
  local body="${3:-}"

  if [[ -n "$body" ]]; then
    curl -fsS -X "$method" "${API_URL}${path}" \
      -H "Content-Type: application/json" \
      -d "$body"
    return
  fi

  curl -fsS -X "$method" "${API_URL}${path}"
}

print_header "OpsGuard AI Demo Walkthrough"
printf 'Base URL: %s\n' "$BASE_URL"
printf 'This script is local-only, deterministic, and never executes infrastructure actions.\n'

print_header "1. Backend health"
health_payload="$(request_json GET "/health")" || {
  printf 'Backend health check failed.\n'
  printf 'Start the backend first:\n'
  printf '  cd backend\n'
  printf '  source .venv/bin/activate\n'
  printf '  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000\n'
  exit 1
}
printf '%s\n' "$health_payload" | pretty_json

print_header "2. Seed deterministic demo data"
seed_payload="$(request_json POST "/demo/seed" '{"reset": false}')"
printf '%s\n' "$seed_payload" | pretty_json

print_header "3. Run GPU abuse agent scenario"
gpu_run_payload="$(request_json POST "/agent/runs" "{\"alert_id\":\"${GPU_ALERT_ID}\"}")"
printf '%s\n' "$gpu_run_payload" | pretty_json
gpu_run_id="$(printf '%s\n' "$gpu_run_payload" | json_field "agent_run_id")"
if [[ -n "$gpu_run_id" ]]; then
  print_header "3a. GPU agent run detail"
  request_json GET "/agent/runs/${gpu_run_id}" | pretty_json
fi

print_header "4. Run prompt-injection agent scenario"
prompt_run_payload="$(request_json POST "/agent/runs" "{\"alert_id\":\"${PROMPT_ALERT_ID}\"}")"
printf '%s\n' "$prompt_run_payload" | pretty_json
prompt_run_id="$(printf '%s\n' "$prompt_run_payload" | json_field "agent_run_id")"
if [[ -n "$prompt_run_id" ]]; then
  print_header "4a. Prompt-injection run detail"
  request_json GET "/agent/runs/${prompt_run_id}" | pretty_json
fi

print_header "5. Run security harness"
harness_payload="$(request_json POST "/harness/run" '{"scenario_ids": null, "reset_demo_data": true}')"
printf '%s\n' "$harness_payload" | pretty_json

print_header "6. Run evaluation"
evaluation_payload="$(request_json POST "/evaluation/run" '{"run_harness_if_empty": true, "report_type": "full"}')"
printf '%s\n' "$evaluation_payload" | pretty_json

print_header "7. Fetch Markdown safety report"
curl -fsS "${API_URL}/evaluation/report.md"

print_header "Demo complete"
printf 'Stable alert IDs used:\n'
printf '  GPU abuse: %s\n' "$GPU_ALERT_ID"
printf '  Prompt injection: %s\n' "$PROMPT_ALERT_ID"
printf 'If you need raw API exploration, open %s/health or %s/evaluation/report.json\n' "$API_URL" "$API_URL"
