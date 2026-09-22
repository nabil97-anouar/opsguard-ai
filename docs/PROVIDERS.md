# Reasoning providers

OpsGuard uses one configured reasoning provider per investigation. Provider selection and credentials belong to the backend. The browser displays configuration and recorded run metadata; it does not store keys or select a different provider per request.

## Configuration and restart

Use the root `.env` for private settings. If it does not exist, copy `.env.example` to `.env`; do not overwrite an existing local file. All key fields in the example must remain empty.

Settings load `.env` and `../.env` relative to the backend's working directory; exported environment variables override both. If you previously started in deterministic mode, stop the backend, run `unset LLM_PROVIDER`, then restart from the repository root to use your `.env` choice:

```bash
source .venv/bin/activate
unset LLM_PROVIDER
export PYTHONPATH=backend
export DATABASE_URL=sqlite:///./opsguard.db
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Review `GET /api/v1/runtime/reasoning` or the Overview runtime card. Configuration is not a connectivity test. A new investigation makes up to four bounded model calls; a failure stops that run. The system does not retry through another provider. Old runs retain their original provider and evidence.

Set `LLM_TIMEOUT_SECONDS` (1–120, default 30) and `LLM_MAX_OUTPUT_TOKENS` (256–8000, default 1800) to control each call. A four-call run may take substantially longer than one timeout. Output must pass the same local Pydantic and evidence-reference validation regardless of provider.

## Deterministic: offline default

```dotenv
LLM_PROVIDER=deterministic
```

No key or model request is used. Imported incident reasoning summarizes the supplied observations and gaps using local rules; bundled scenarios use deterministic scenario logic. Confidence values are engineering heuristics, not probabilities. The security harness always selects this provider independently of the server's investigation configuration.

## OpenAI-compatible Chat Completions

```dotenv
LLM_PROVIDER=institutional
INSTITUTIONAL_LLM_BASE_URL=https://inference.example.org/api
INSTITUTIONAL_LLM_API_KEY=YOUR_PRIVATE_KEY
INSTITUTIONAL_LLM_MODEL=YOUR_CHAT_MODEL
INSTITUTIONAL_LLM_RESPONSE_FORMAT=json_object
```

Confirm the exact API base path with your service operator. The adapter preserves it and does not add `/v1`. HTTPS is required except for loopback development endpoints. Redirects are disabled. `json_schema` is an explicit alternative to `json_object` only if the deployment supports it; unsupported formats fail explicitly. Both modes validate the returned JSON locally.

Set a chat-capable deployment identifier in `INSTITUTIONAL_LLM_MODEL`. Embedding-only deployments are rejected as reasoning models. Retrieval remains lexical. An optional `INSTITUTIONAL_LLM_TIMEOUT_SECONDS` overrides the common timeout.

Confirm your account's model access, data retention, and permitted use with the institution before transmitting operational data. A repository license does not grant rights to an inference service.

The optional [compatible-endpoint probe](../scripts/verify_institutional_provider.py) reads exported variables only, not `.env`. Without `--live` it validates configuration without a request. With `--live` it sends one synthetic classification request. Success proves only that bounded request, not the security of every model task.

## OpenAI

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=YOUR_PRIVATE_KEY
OPENAI_MODEL=YOUR_STRUCTURED_OUTPUT_MODEL
```

Use a model available to your API project that supports structured output through the Responses API. The adapter uses typed parsed responses. API access and billing are separate from a consumer chat subscription. A key alone does not select the provider or model.

The optional [OpenAI probe](../scripts/verify_openai_provider.py) sends one real request when run; it is not part of CI. Normal unit tests simulate responses.

## Claude

```dotenv
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=YOUR_PRIVATE_KEY
ANTHROPIC_MODEL=YOUR_CLAUDE_MODEL_ID
```

Use a model identifier enabled for your Anthropic API account. The native Messages adapter requests one structured output matching the application schema; the backend validates it before use. Model output cannot dispatch operational tools. The Claude transport constrains arbitrary action `parameters` to an empty object for its closed schema; proposed details remain in the rationale for human review. Numeric and length constraints are always enforced locally even where the server schema does not support them. The chosen API model must support the adapter's structured response mechanism. Account access, quota, and model compatibility still require a live operator check.

An optional `ANTHROPIC_BASE_URL` defaults to `https://api.anthropic.com`; a proxy prefix is preserved before `/v1/messages`. `ANTHROPIC_TIMEOUT_SECONDS` overrides the common timeout.

## Ollama

Run an Ollama server and install a local chat model suitable for JSON structured output, then set:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=YOUR_INSTALLED_CHAT_MODEL
```

Use the exact model name shown by your Ollama installation. OpsGuard does not download models or start the server. The native chat adapter requests a non-streaming structured response and validates it locally. Slow cold starts may require a higher `LLM_TIMEOUT_SECONDS`. There is no automatic fallback if a model cannot follow the schema.

`OLLAMA_API_KEY` optionally supplies a bearer credential for an authenticated gateway. `OLLAMA_TIMEOUT_SECONDS` overrides the common timeout. The adapter appends `/api/chat` to the base URL and preserves an existing proxy prefix. Non-loopback endpoints require HTTPS.

Loopback URLs refer to the **backend's** machine. Inside a container, `127.0.0.1` points to that container, not the host's Ollama service. For the simplest local Ollama setup, run the backend natively as described in the README. A remote service requires deliberate endpoint/network configuration; the application does not expose your Ollama server for you.

## Data and failure boundaries

Selected providers receive bounded alert details, evidence snapshots, source/trust metadata, observed gaps, hypotheses, and allowed action vocabulary. Do not upload credentials or sensitive telemetry that you are not permitted to send to the chosen service. Obvious credential redaction is limited hygiene, not a comprehensive data-loss prevention system.

Credentials and raw provider exceptions are excluded from runtime responses, provider provenance, and frontend configuration. Authentication, quota, timeout, invalid output, refused requests, and unsupported model behavior surface as explicit failed runs with safe errors. Configured availability is distinct from a successful model call.

The committed tests exercise simulated protocol responses and failures. They do not establish that your key, model access, institution's terms, or machine's model-serving capacity have been verified.

## Protocol references and compatibility

- [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages/create) and [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs): the adapter uses `output_config.format` with a JSON schema. Older deployments without this mechanism fail explicitly.
- [Ollama chat API](https://docs.ollama.com/api/chat) and [structured outputs](https://docs.ollama.com/capabilities/structured-outputs): the adapter requires a completed non-streaming response with `done: true` and `done_reason: stop`. It targets schema-capable local deployments; Ollama Cloud's documented lack of structured outputs is not bypassed by accepting free-form text.

These transport contracts are exercised by simulated response tests. A loopback Ollama address only identifies the configured server location; it does not prove that the server never forwards requests elsewhere.
