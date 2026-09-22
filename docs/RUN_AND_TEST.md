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
3. Open **Investigations**, choose a `.log`, `.txt`, `.csv`, `.jsonl`, `.md`, or `.json` export (or `examples/incidents/normal-workload.json`). The page now shows three explicit states: **Select and convert locally**, **Save evidence to OpsGuard**, and **Run the investigation**. Conversion makes no network request. Saving stores data without reasoning. Only the final action starts the configured provider. To test bundled scenarios separately, use **Seed sample data** before starting a sample scenario.
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

## 4. Record a complete walkthrough

Use deterministic mode for a reproducible recording without API credentials. Start with a fresh SQLite filename or clearly identify existing history.

1. Show **Overview** with Backend connected and Deterministic reasoning.
2. Open **Investigations** and select `examples/incidents/normal-workload.json`. Point out the three states: converted locally, saved, then investigated.
3. Run it and show the recorded trace, evidence identities, recommendation, watchdog verdict, and human-review terminal state.
4. Select `examples/incidents/malicious-log.json`. Show that its instructions remain untrusted data and cannot authorize tools.
5. Open **Tools & policy** and show executable local adapters separately from blocked destructive definitions and audited attempts.
6. Run **Security harness**, then open **Evaluation** and generate the stored cohort report. Explain that these are deterministic regression checks rather than live-model benchmarks.
7. Return to **Evidence**, select a historical run, and export its Markdown or JSON report. Confirm the visible run ID matches the downloaded report.

Do not show `.env`, API keys, real operational logs, usernames, IP addresses, or private reports in the recording. Provider-specific setup belongs in [Provider Setup](PROVIDERS.md); it is not required to demonstrate the application workflow.

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
