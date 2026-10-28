# PulseForge backend

The API behind PulseForge: FastAPI + Postgres. It checks Supabase login tokens and stores user profiles. Plan: [docs/BLUEPRINT.md](../docs/BLUEPRINT.md).

## What it does today

- `GET /healthz` (is the server up) and `GET /readyz` (is the database reachable).
- `GET /v1/me` and `PATCH /v1/me`: the signed-in user's profile (created on first request).
- `POST /v1/me/tos`: record that the user accepted the current terms version.
- Every error is a JSON problem document (`application/problem+json`).

## Run it locally

You need [uv](https://docs.astral.sh/uv/) and Docker Desktop (running).

```bash
# 1. Start Postgres (port 54322)
docker compose -f infra/compose.yml up -d     # run from the repo root

# 1b. One time only: create the dev database (the tests use pulseforge_test and wipe it)
docker compose -f infra/compose.yml exec postgres createdb -U postgres pulseforge

# 2. Install dependencies
cd backend
uv sync --extra api --locked
```

Settings come from environment variables (or a gitignored `backend/.env` file):

| Variable | Meaning | Default |
|---|---|---|
| `DATABASE_URL` | Postgres connection, e.g. `postgresql+psycopg://postgres:postgres@localhost:54322/pulseforge` (your dev database, not the test one) | required |
| `SUPABASE_URL` | Your Supabase project URL, used to fetch the signing keys | required |
| `JWT_AUDIENCE` | Expected token audience | `authenticated` |
| `TOS_VERSION` | Current terms version | `v1` |

```bash
# bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:54322/pulseforge
export SUPABASE_URL=https://YOUR-PROJECT.supabase.co
```

```powershell
# PowerShell
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:54322/pulseforge"
$env:SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
```

Create the tables, then start the server:

```bash
uv run alembic upgrade head
uv run uvicorn pulseforge.api.main:app --reload
```

Open http://localhost:8000/healthz to check it. `/v1/me` needs a real Supabase token (`Authorization: Bearer <token>`), which arrives with the web login (M1b).

## Run the tests

The tests use the Postgres from the step above.

```bash
# bash
export TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:54322/pulseforge_test
cd backend && uv run pytest -v
```

```powershell
# PowerShell
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:54322/pulseforge_test"
cd backend; uv run pytest -v
```

Lint from the repo root: `uvx ruff@0.17.3 check .`

## Good to know

- Database access is synchronous (SQLAlchemy 2 + psycopg 3), on purpose: simpler for the MVP (BLUEPRINT §20).
- `users_profile.id` is the token's `sub`. There is no link to Supabase's `auth.users` table, so migrations run on plain Postgres.
- Users can never change their own `plan` through the API.
