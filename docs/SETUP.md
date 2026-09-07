# Setup and Configuration

The [Quick Start](../README.md#quick-start) uses a local Python backend, a Next.js development server, and SQLite. Run its backend commands in the same terminal so the database and CORS environment variables remain available to the server.

## Configuration

Backend settings are defined in [Settings](../backend/app/core/config.py). Process environment variables override dotenv values. Dotenv paths are relative to the working directory: `.env` followed by `../.env`; the latter takes precedence when both define a setting.

| Setting | Current behavior |
| --- | --- |
| `DATABASE_URL` | Defaults to local PostgreSQL. Set `sqlite:///./opsguard.db` when running from `backend/` for the SQLite setup. |
| `ENVIRONMENT` | Defaults to `development`. The direct seed and create-tables endpoints reject `production`; this does not protect every indirect setup path. |
| `LOG_LEVEL` | Logging verbosity; defaults to `INFO`. |
| `BACKEND_CORS_ORIGINS` | Use a JSON array, such as `'["http://localhost:3000","http://127.0.0.1:3000"]'`. The comma-separated value in the existing example file is incompatible with settings-source JSON decoding. |
| `LLM_PROVIDER`, `MOCK_LLM` | Affect configuration/reporting, but do not select a reasoning implementation. Agent runs always use deterministic local functions. |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Reserved settings; no provider integrations consume them. Leave them empty. |
| `QDRANT_URL` | Reserved configuration; retrieval does not connect to Qdrant. |
| `SECRET_KEY` in `.env.example` | Not a declared application setting; it does not enable authentication. |

The [example environment file](../.env.example) includes reserved settings. It is not required by the primary setup, which supplies its active settings explicitly.

The frontend reads `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000/api/v1`. Next.js started from `frontend/` does not load a repository-root `.env` as its project environment file. Use a process variable, as in the Quick Start, or `frontend/.env.local`. Public variables are embedded in client code during a production build; do not put credentials in them.

Initial dependency installation requires network access. [layout.tsx](../frontend/src/app/layout.tsx) uses Google fonts through `next/font`, so font compilation also requires access to those resources.

## PostgreSQL alternative

With Docker running, start the database from the repository root:

```bash
docker compose up -d postgres
```

In the backend terminal, after creating and installing the Python environment as described in the Quick Start:

```bash
cd backend
export ENVIRONMENT=development
export DATABASE_URL=postgresql+psycopg://opsguard:opsguard@localhost:5432/opsguard_ai
export BACKEND_CORS_ORIGINS='["http://localhost:3000","http://127.0.0.1:3000"]'
.venv/bin/python -m app.db.init_db
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

These database credentials are the Compose defaults. If you override `POSTGRES_USER`, `POSTGRES_PASSWORD`, or `POSTGRES_DB`, use matching credentials in the native backend URL. Use the same frontend and seeding steps as the Quick Start.

Schema initialization uses SQLModel `create_all`; it creates missing tables but does not migrate an existing schema. SQLite foreign-key enforcement and PostgreSQL behavior differ in the current configuration. See [data model](DATA_MODEL.md) and [reset limitations](DEMO_SCRIPT.md#data-and-reset-behavior).

## Docker Compose alternative

The [Compose file](../docker-compose.yml) builds both applications and starts PostgreSQL and an unused Qdrant service. Supply CORS origins as JSON to override the current comma-separated default:

```bash
export BACKEND_CORS_ORIGINS='["http://localhost:3000","http://127.0.0.1:3000"]'
docker compose config --quiet
docker compose up --build
```

Wait for the backend and frontend to start, then follow the Quick Start's health and seed requests. The database volume persists across container restarts. Stop containers without deleting volumes with:

```bash
docker compose down
```

Current Compose constraints:

- Published ports bind beyond loopback by default, including PostgreSQL and Qdrant. Use a trusted local development environment; the application has no authentication.
- Qdrant is a backend startup dependency in Compose despite having no retrieval role.
- The frontend API URL is supplied only at container runtime. Its built client uses the default localhost URL; changing the runtime variable does not configure a different deployment address.
- Compose does not pass `ENVIRONMENT` to the backend, so setting it in the root dotenv file alone does not change the container's application environment.
- Backend application readiness and schema migrations are not managed by Compose.

## Verification scope

Use the commands in [Development](../README.md#development) for source checks. `docker compose config --quiet` validates Compose configuration only; it does not build images or check service health. `/api/v1/health` reports configuration, while `/api/v1/db/health` attempts a database connection.

The generated [OpenAPI schema](http://localhost:8000/openapi.json) is available with the backend running. The default content-security policy may block the external assets used by [Swagger UI](http://localhost:8000/docs).
