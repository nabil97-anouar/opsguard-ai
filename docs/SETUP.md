# Setup and configuration

Use Python **3.11**, Node **22** and npm (the version bundled with Node 22 is suitable). `.python-version` and `.nvmrc` record those supported lines. Initial package installation requires network access. The following commands run from the repository root unless specified otherwise.

## Native local setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r backend/requirements-dev.txt
export PYTHONPATH=backend
export DATABASE_URL=sqlite:///./opsguard.db
python -m app.db.init_db
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The initialization command creates missing tables and applies the existing additive compatibility updates. Run it explicitly before first use and after pulling schema changes. Ordinary routes never run DDL. An existing deployment can initialize with an owner account, then run the API with a SQL account that lacks DDL privileges. The local Compose example uses one development database account; it does not provision roles.

In a second terminal:

```bash
cd frontend
# If nvm is installed: nvm use
npm ci
npm run dev
```

Open `http://localhost:3000`. In a third terminal at the root:

```bash
curl --fail http://localhost:8000/api/v1/health
curl --fail http://localhost:8000/api/v1/ready
bash scripts/demo_walkthrough.sh
```

The walkthrough uses seeded IDs, executes two investigations, runs the harness without resetting prior activity, evaluates that explicit execution, and exports the stored report by evaluation ID. It requires curl and python3; jq is optional. Override `BASE_URL` or the complete `API_URL` for a different local port/prefix. Failed HTTP requests, missing JSON fields, failed investigations and failed harness assertions stop with an error.

## Configuration

[Settings](../backend/app/core/config.py) reads `.env` and `../.env` relative to the working directory (the latter wins), then process environment overrides both. `.env.example` is optional; the commands above supply their active settings explicitly. Do not commit local env files or databases.

| Setting | Behavior |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy `sqlite` or `postgresql+psycopg` URL; default local PostgreSQL. SQLite paths are relative to the process working directory. |
| `ENVIRONMENT` | `development` (default), `staging`, or `production`. Direct seed/create-table endpoints are disabled in production; this is not an authentication boundary. |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |
| `BACKEND_CORS_ORIGINS` | JSON array or comma-separated explicit HTTP(S) origins. Empty disables cross-origin access. Wildcards, credentials and paths are rejected. |
| `API_V1_PREFIX` | Defaults to `/api/v1`; must start with `/` without trailing slash, query or fragment. |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend **build-time** browser URL; defaults to `http://localhost:8000/api/v1`. May be a same-origin path when a proxy is provided externally. This repository does not provide a proxy. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Compose-only development database settings; native clients must set a matching `DATABASE_URL`. |

Removed provider/API-key, mock-toggle, Qdrant and unused secret settings have no effect. The only implemented reasoner is deterministic; `/health` identifies it explicitly. Unrecognized dotenv fields are ignored so Compose/frontend values can share the example file. No real integrations or auth are enabled by environment variables.

Next.js reads its process environment or `frontend/.env.local`; it does not load root `.env` in native mode. The browser API URL is public and embedded during build. Changing a running frontend container's environment cannot change it: pass a build argument and rebuild. Never place credentials in `NEXT_PUBLIC_*`. Google font compilation currently requires network access.

## Compose

```bash
docker compose config --quiet
docker compose build backend frontend
docker compose up -d --wait
```

The stack contains PostgreSQL, a one-shot schema initializer, backend and frontend. The database must become healthy before initialization, and initialization must succeed before backend startup. Backend health checks use `/ready`; frontend starts after backend readiness. All published ports bind to `127.0.0.1`. Qdrant is absent because it is unused.

Both runtime images use non-root users. Backend installs only hash-locked runtime dependencies; frontend copies Next.js standalone output without the full development dependency tree. Docker contexts exclude local env files, caches, databases and dependencies. Base images follow supported Python 3.11, Node 22 and PostgreSQL 16 lines, allowing upstream patch rebuilds; they are not digest-pinned.

For a native backend with Compose PostgreSQL, run `docker compose up -d postgres` and set `DATABASE_URL=postgresql+psycopg://opsguard:opsguard@localhost:5432/opsguard_ai` (or matching custom credentials), then initialize explicitly. Passwords interpolated into Compose's database URL must be URL-safe. Defaults are local development credentials, not deployment credentials.

`docker compose down` stops services and preserves the database volume. Do not delete the volume unless you intend to discard its data.

## Checks and dependency maintenance

[CONTRIBUTING.md](../CONTRIBUTING.md) lists the exact CI/local checks. CI uses one Python and Node line, with separate Backend, Frontend and Containers jobs. Scheduled runs refresh advisory results weekly. No remote CI success is implied by a local run.

Runtime inputs are in `backend/requirements.in`; development inputs are in `backend/requirements-dev.in`. `pip-tools` is a development-only lock generator; installation remains plain pip. Both generated `.txt` files pin transitive versions and package hashes. After intentionally updating the inputs, regenerate from the root with Python 3.11:

```bash
pip-compile --generate-hashes --strip-extras --output-file=backend/requirements.txt backend/requirements.in
pip-compile --generate-hashes --allow-unsafe --strip-extras --output-file=backend/requirements-dev.txt backend/requirements-dev.in
python -m pip install --require-hashes -r backend/requirements-dev.txt
```

Linux's SQLAlchemy Greenlet dependency is explicitly locked even when generating on macOS. The lock targets Linux/macOS Python 3.11; Windows setup has not been verified. Frontend updates use npm and commit the lockfile; installation uses `npm ci`. The Next.js-scoped PostCSS override selects a patched compatible 8.x release instead of forcing a Next.js major migration; review/remove it when upstream pins a corrected release.

See [SECURITY.md](../SECURITY.md) for audit severity policy. Scanner/network errors do not count as clean results. There is no license file yet; a maintainer license decision remains outstanding.
