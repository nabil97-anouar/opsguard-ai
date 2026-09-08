#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_URL="${API_URL:-${BASE_URL}/api/v1}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { printf "python3 is required.\n" >&2; exit 1; }
trap 'printf "Walkthrough failed at line %s. Check the preceding API error.\n" "$LINENO" >&2' ERR
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
    python3 -m json.tool
    return
  fi

  cat
}

json_field() {
  python3 "${SCRIPT_DIR}/json_field.py" "$1"
}

require_field() {
  local actual
  actual="$(printf '%s\n' "$1" | json_field "$2")"
  if [[ "$actual" != "$3" ]]; then
    printf 'Unexpected %s: %s (expected %s). Inspect the response above.\n' "$2" "$actual" "$3" >&2
    exit 1
  fi
}

request_json() {
  local method="$1"
  local path="$2"
  local body="${3:-}"

  if [[ -n "$body" ]]; then
    curl --connect-timeout 5 --max-time 120 -fsS -X "$method" "${API_URL}${path}" \
      -H "Content-Type: application/json" \
      -d "$body"
    return
  fi

  curl --connect-timeout 5 --max-time 120 -fsS -X "$method" "${API_URL}${path}"
}

print_header "OpsGuard AI Demo Walkthrough"
printf 'Base URL: %s\n' "$BASE_URL"
printf 'This script is local-only, deterministic, and never executes infrastructure actions.\n'

print_header "1. Backend readiness"
health_payload="$(request_json GET "/ready")" || {
  printf 'Backend readiness check failed.\n'
  printf 'Start the backend first:\n'
  printf 'Follow docs/SETUP.md with the same DATABASE_URL; initialize the schema before starting the server.\n'
  exit 1
}
printf '%s\n' "$health_payload" | pretty_json

print_header "2. Seed deterministic demo data"
seed_payload="$(request_json POST "/demo/seed" '{"reset": false}')"
printf '%s\n' "$seed_payload" | pretty_json

print_header "3. Run GPU abuse agent scenario"
gpu_run_payload="$(request_json POST "/agent/runs" "{\"alert_id\":\"${GPU_ALERT_ID}\"}")"
printf '%s\n' "$gpu_run_payload" | pretty_json
require_field "$gpu_run_payload" "status" "waiting_for_human"
gpu_run_id="$(printf '%s\n' "$gpu_run_payload" | json_field "agent_run_id")"
if [[ -n "$gpu_run_id" ]]; then
  print_header "3a. GPU agent run detail"
  request_json GET "/agent/runs/${gpu_run_id}" | pretty_json
fi

print_header "4. Run prompt-injection agent scenario"
prompt_run_payload="$(request_json POST "/agent/runs" "{\"alert_id\":\"${PROMPT_ALERT_ID}\"}")"
printf '%s\n' "$prompt_run_payload" | pretty_json
require_field "$prompt_run_payload" "status" "waiting_for_human"
prompt_run_id="$(printf '%s\n' "$prompt_run_payload" | json_field "agent_run_id")"
if [[ -n "$prompt_run_id" ]]; then
  print_header "4a. Prompt-injection run detail"
  request_json GET "/agent/runs/${prompt_run_id}" | pretty_json
fi

print_header "5. Run security harness"
harness_payload="$(request_json POST "/harness/run" '{"scenario_ids": null, "reset_demo_data": false}')"
printf '%s\n' "$harness_payload" | pretty_json

require_field "$harness_payload" "status" "completed"
require_field "$harness_payload" "failed" "0"
require_field "$harness_payload" "partial" "0"

print_header "6. Run evaluation"
harness_run_id="$(printf '%s\n' "$harness_payload" | json_field "harness_run_id")"
evaluation_payload="$(request_json POST "/evaluation/run" "{\"harness_run_id\":\"${harness_run_id}\",\"run_harness_if_empty\":false}")"
printf '%s\n' "$evaluation_payload" | pretty_json

evaluation_id="$(printf '%s\n' "$evaluation_payload" | json_field "evaluation_run_id")"
print_header "7. Fetch stored Markdown evaluation report"
curl --connect-timeout 5 --max-time 120 -fsS "${API_URL}/evaluation/report.md?evaluation_run_id=${evaluation_id}"

print_header "Demo complete"
printf 'Stable alert IDs used:\n'
printf '  GPU abuse: %s\n' "$GPU_ALERT_ID"
printf '  Prompt injection: %s\n' "$PROMPT_ALERT_ID"
printf 'If you need raw API exploration, open %s/health or %s/evaluation/report.json\n' "$API_URL" "$API_URL"
