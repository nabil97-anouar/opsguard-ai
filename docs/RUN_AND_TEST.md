# Run and test the operations console

Use Python 3.11 and Node 22. This guide assumes the dependencies in [Setup](SETUP.md) are installed. Commands run from the repository root unless noted.

## 1. Start the backend locally

Stop an older backend with Ctrl+C in its terminal, then run:

```bash
source .venv/bin/activate
export PYTHONPATH=backend
export DATABASE_URL=sqlite:///./opsguard-test.db
export LLM_PROVIDER=deterministic
python -m app.db.init_db &&
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The initializer preserves existing records and applies supported additive schema updates. Use a different SQLite filename for a fresh database. Deterministic mode requires no API key and sends no model requests.

## 2. Start the frontend

In another terminal:

```bash
cd frontend
# macOS with Homebrew Node 22; omit this if node --version already reports v22.
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
node --version
npm run dev
```

Open **http://localhost:3000**. Use localhost on the same computer as the backend. A LAN URL such as `http://192.168.0.40:3000` is a different origin and is not allowed by the default backend CORS configuration. Do not work around this by allowing every origin. See [Setup](SETUP.md) for explicit origin configuration.

## 3. Test the interface and investigation flow

1. On Overview, confirm backend connectivity and deterministic reasoning. Empty data should be labeled as empty; unavailable data should be labeled unavailable.
2. Bright falling character streams should be visible immediately around the console, with no effects toolbar or decorative-signal label. A system reduced-motion preference takes priority and gives a static background.
3. Open **Investigations**, choose a `.log`, `.txt`, `.csv`, `.jsonl`, `.md`, or `.json` export (or `examples/incidents/normal-workload.json`), review the automatic conversion, import it, then start the imported investigation. Importing stores data without a model request. The run uses the recorded bundle, not cluster access or fixture observations. To test bundled scenarios separately, use **Seed sample data** before starting a sample scenario.
4. Inspect the trace, recorded tool observations, evidence references, and policy findings. A successful investigation ends at human review. Destructive tool definitions are context, not actions the model necessarily proposed.
5. Open Evidence and select an older run. Only that run's saved evidence should appear. A run without evidence should remain empty.
   Return to Investigations and choose another file: the old results and export links must disappear. Importing the new file must not bring them back. Run the new investigation and verify its title and run ID before exporting.
6. Open Tools & policy. Executable local adapters and blocked definitions must appear separately. Audit records distinguish denied, failed, incomplete, and successful attempts.
7. Open Security harness and execute the suite. Seeded example records must not count as executed passes. The harness uses deterministic reasoning even if an external provider is selected for investigations.
8. Open Evaluation, generate a report for the executed harness, and export it. The exported report must identify the same stored evaluation and cohort shown in the interface.
9. Narrow the browser to a phone-sized viewport. Workspace navigation and controls must remain usable without horizontal page scrolling.

The animated Matrix character field is decorative and never executes commands.

### Test your own incident and exports

Repeat the import/run flow with the four [example bundles](../examples/incidents), including insufficient evidence and malicious log instructions. The source remains untrusted. Missing observations must stay empty; malicious text must not authorize tools. Download both per-investigation report formats and compare their run ID with the selected investigation. Reopen an older run after another import: its evidence and exports should still describe the original run. See [Incident Bundles](INCIDENT_BUNDLES.md) for the schema and command-line equivalent.

## 4. Configure TU Darmstadt inference

Keep credentials in the root `.env`, never in `.env.example` or a `NEXT_PUBLIC_*` setting. Create `.env` from the example only if it does not already exist; preserve any existing local settings.

Set these backend values in `.env`:

```dotenv
LLM_PROVIDER=institutional
INSTITUTIONAL_LLM_BASE_URL=https://llm-service.ai.tu-darmstadt.de
INSTITUTIONAL_LLM_API_KEY=YOUR_PRIVATE_INSTITUTIONAL_KEY
INSTITUTIONAL_LLM_MODEL=gpt-oss-120b
INSTITUTIONAL_LLM_RESPONSE_FORMAT=json_object
```

The base URL above is the address supplied for this project. Confirm the exact API base path with the platform operator. The adapter preserves that path and does not add `/v1` automatically. Use `json_schema` only if the selected deployment supports it. Both modes require locally validated JSON; an unsupported format causes an explicit failure, without silently switching model or provider.

After stopping the backend, remove the earlier process override and restart it from the root:

```bash
source .venv/bin/activate
unset LLM_PROVIDER
export PYTHONPATH=backend
export DATABASE_URL=sqlite:///./opsguard-test.db
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The runtime card should show the institutional provider and requested model, with connectivity **not checked**. Configuration alone does not establish that the key works. A new investigation sends its context to the selected service and makes up to four bounded reasoning requests. Old runs keep their original provider and evidence snapshots.

The following deployment identifiers were supplied by the project operator. They are options, not verified availability or capability claims:

- `gpt-oss-120b`
- `gemma-4-31B-it`
- `Llama-3.1-70B-Instruct`
- `Kimi-K2.6`
- `Mistral-Medium-3.5-128B`

To change models, edit `INSTITUTIONAL_LLM_MODEL`, restart the backend, and create a new run. `gte-Qwen2-1.5B-instruct` is an embedding deployment and is rejected as a chat model. Retrieval remains lexical.

The existing OpenAI Responses adapter remains available through `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL`. Claude and Ollama adapters are also available; see [Provider Setup](PROVIDERS.md) for configuration.

### Optional one-request connectivity check

This script deliberately reads exported variables only; it does not load `.env`. In a separate terminal, enter the key privately at the prompt. These commands work in zsh and bash:

```bash
source .venv/bin/activate
export LLM_PROVIDER=institutional
export INSTITUTIONAL_LLM_BASE_URL=https://llm-service.ai.tu-darmstadt.de
export INSTITUTIONAL_LLM_MODEL=gpt-oss-120b
export INSTITUTIONAL_LLM_RESPONSE_FORMAT=json_object
printf 'Institutional key (hidden): '
read -rs INSTITUTIONAL_LLM_API_KEY
printf '\n'
export INSTITUTIONAL_LLM_API_KEY
python scripts/verify_institutional_provider.py
```

That command validates configuration without contacting the service. To send exactly one synthetic classification request:

```bash
python scripts/verify_institutional_provider.py --live
unset INSTITUTIONAL_LLM_API_KEY
```

Success reports the requested and served model, structured-output validation, timing, and token usage when available. It does not establish injection resistance or compatibility with every reasoning task. Failures are explicit and do not expose the key or raw service response. Never paste your key into an issue or chat. Confirm institutional usage and data-handling terms before sending operational telemetry.

## 5. Run automated checks

From the repository root:

```bash
source .venv/bin/activate
export LLM_PROVIDER=deterministic
export DATABASE_URL=sqlite://
python -m pytest backend/tests -q &&
python -m ruff check backend scripts &&
python -m mypy &&
python scripts/check_secrets.py &&
python scripts/check_markdown_links.py &&
git diff --check
```

These tests use local fixtures and simulated provider responses. They do not use your API key or measure live-model security.

```bash
cd frontend
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
npm test &&
npm run lint &&
npm run typecheck &&
npm run build
```

Stop the frontend development server before building into its default `.next` directory. To inspect the production build, run `npm run start` and open localhost:3000. An optional `OPSGUARD_NEXT_DIST_DIR` selects a separate build directory; use the same value when building and starting.

The targeted credential guard is also included in CI. Enable the local staged-file hook explicitly with `git config core.hooksPath .githooks`; merely having the file in the repository does not activate it. The guard is not a comprehensive secret scanner and cannot revoke a previously exposed credential.
