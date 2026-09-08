# Contributing

Follow [Setup](docs/SETUP.md) using Python 3.11 and Node 22. The repository currently has no license; ask the maintainer about licensing before redistributing or incorporating it elsewhere.

From the repository root, with the Python virtual environment active:

```bash
python -m pytest backend/tests -q
python -m ruff check backend scripts
python -m mypy
python scripts/check_markdown_links.py
bash -n scripts/demo_walkthrough.sh
python scripts/verify_evaluation_integrity.py --output-dir /tmp/opsguard-evaluation
python scripts/verify_watchdog_audit.py --output-dir /tmp/opsguard-audit
python scripts/audit_python.py
```

From `frontend/`:

```bash
npm ci
npm test
npm run lint
npm run typecheck
npm run build
npm audit --audit-level=high
```

From the root, with Docker available:

```bash
docker compose config --quiet
docker compose build backend frontend
```

Keep changes focused. Follow the existing Python type annotations/Pydantic models and React/TypeScript conventions. Ruff checks correctness and unused code; scoped mypy checks actions, trust, audit serialization and health schemas. Do not claim the entire backend is statically checked.

Add exact regression tests and update affected docs when behavior changes. Preserve evidence identities, fixture/execution provenance, immutable evaluation cohorts, tool-attempt audit ownership, and mandatory policy invariants. Security-sensitive changes should exercise rejection and failure paths, not just successful runs. Avoid permissive assertions, score tuning, credentials in fixtures, or new integrations hidden in repository cleanup.

Update dependency inputs and regenerate both hash locks together as described in Setup. Commit `package-lock.json` with frontend dependency changes. Report vulnerabilities through [SECURITY.md](SECURITY.md), not public reproductions containing sensitive details.
