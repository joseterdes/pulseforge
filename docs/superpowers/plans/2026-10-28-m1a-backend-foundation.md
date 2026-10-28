# M1a Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tested FastAPI backend that verifies Supabase login tokens locally, stores a user profile in Postgres via Alembic migrations, and serves `GET/PATCH /v1/me` and `POST /v1/me/tos`. This is the backend half of Milestone 1 ("`GET /v1/me` works"), built and tested without any cloud account.

**Architecture:** One Python package `pulseforge` under `backend/src/`, built by an app factory `create_app(settings, verifier)` so tests can inject a fake token verifier and a test database. Token checks use PyJWT against Supabase's JWKS (asymmetric keys only). Errors are RFC 9457 problem+json. Sync SQLAlchemy 2 with psycopg 3: simpler than async, and FastAPI runs sync endpoints in a thread pool, which is plenty for the MVP. *This deviates from the blueprint's "async" note on purpose; record it in BLUEPRINT §20 in Task 6.*

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2 (sync) + psycopg 3, Alembic, PyJWT[crypto], pytest + FastAPI TestClient, Postgres 17 (Docker locally, service container in CI).

**Spec:** [docs/BLUEPRINT.md](../../BLUEPRINT.md): §3 (stack), §9 (`users_profile`), §10 (API conventions and `/v1/me`), §11 (folder layout), §12 (Milestone 1), §14 (CI/migrations).

## Where this sits

1. **Phase 0 (at home, in parallel):** follow [phase0/README.md](../../../phase0/README.md) on the RTX 3060. It's a run-book, not code, and it gates the AI choice but not this plan.
2. **This plan (M1a), on the laptop:** backend foundation.
3. **Later plans:** M1b, web app skeleton + Supabase login UI (needs a Supabase project); M1c, deployment to the Oracle VM, Cloudflare Pages and Sentry (needs those accounts).

## Global Constraints

- Python **3.12** (`requires-python = ">=3.12"`); dependencies managed with **uv**, with `uv.lock` committed and CI using `uv sync --locked`.
- Dependencies sit in extras as in BLUEPRINT §3: the runtime goes in the `api` extra; test tools in the `dev` dependency group. No torch or audio libraries in this plan.
- All API routes under `/v1`, except the unversioned health checks `/healthz` and `/readyz`.
- Every error response is RFC 9457 with `Content-Type: application/problem+json` and the fields `type`, `title`, `status` (+ `detail` when useful). A 500 never includes exception text.
- Auth: `Authorization: Bearer <Supabase JWT>`. Verify locally against `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, issuer `{SUPABASE_URL}/auth/v1`, audience `authenticated`, algorithms **ES256 and RS256 only**, 30 s clock leeway, and require `exp`, `sub`, `aud`, `iss`.
- Settings come from environment variables only: `DATABASE_URL`, `SUPABASE_URL`, `JWT_AUDIENCE` (default `authenticated`), `TOS_VERSION` (default `v1`). `.env` is gitignored and never committed.
- `users_profile.id` equals the token's `sub`. There is **no FK to `auth.users`**, so migrations run on plain Postgres; integrity comes from the verified token.
- Users can never change `plan` through the API.
- `main` is protected: do all work on branch `feat/backend-foundation` and finish with a PR whose checks pass. Commits use the repo's noreply identity (see CLAUDE.md).
- `ruff check .` (ruff **0.17.3**, root `ruff.toml`) passes.

**Prerequisites on the laptop:** install uv (PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`); have Docker Desktop running.

**Test database URL** (used from Task 4 on):
- bash: `export TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:54322/pulseforge_test`
- PowerShell: `$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:54322/pulseforge_test"`

## Review Focus

1. **Algorithm-confusion tokens** (`alg: HS256` signed with any secret, or `alg: none`) must get a 401, never be accepted. Covered in Task 3 by `test_hs256_token_rejected` and `test_unsigned_token_rejected`.
2. **Two simultaneous first requests from a brand-new user** must both succeed and leave exactly one profile row. Covered in Task 5 by `test_get_me_when_row_already_exists` (the conflict path) and `test_get_me_is_idempotent`.
3. **Malformed `Authorization` headers** (`Basic …`, `Bearer` with no token, a garbage token) must give a 401 problem, not a 500; a lowercase `bearer` scheme must work (RFC 7235). Covered in Task 5 by `test_me_rejects_bad_auth_headers` and `test_me_accepts_lowercase_bearer`.
4. **Supabase JWKS unreachable** (outage, DNS) must give a 503 problem, not a 500 or a misleading 401; a token whose key id isn't in the JWKS gives a 401. Covered in Task 3 (`test_jwks_unreachable_raises_unavailable`, `test_unknown_key_id_rejected`) and Task 5 (`test_me_returns_503_when_jwks_unreachable`).
5. **A user trying to upgrade themselves** (`PATCH /v1/me {"plan": "pro"}`) or sending a wrong-case value (`"ui_mode": "PRO"`) must get a 422 and change nothing. Covered in Task 5 by `test_patch_me_rejects_plan_and_bad_values`.

---

## File map

| File | Responsibility |
|---|---|
| `backend/pyproject.toml`, `backend/uv.lock` | Package metadata, extras, pytest config |
| `backend/src/pulseforge/core/settings.py` | `Settings` from env vars + derived Supabase URLs |
| `backend/src/pulseforge/core/problems.py` | `Problem` exception + problem+json handlers |
| `backend/src/pulseforge/core/auth.py` | `TokenVerifier`, `Claims`, `AuthError`, `AuthUnavailable` |
| `backend/src/pulseforge/db/session.py` | Engine/session factory, `Base` |
| `backend/src/pulseforge/db/models.py` | `UserProfile` ORM model |
| `backend/src/pulseforge/db/profiles.py` | `get_or_create_profile` (race-safe) |
| `backend/src/pulseforge/api/app.py` | `create_app()` factory |
| `backend/src/pulseforge/api/main.py` | ASGI entry point `app = create_app()` (reads env vars) |
| `backend/src/pulseforge/api/deps.py` | FastAPI dependencies: settings, session, current claims |
| `backend/src/pulseforge/api/routers/health.py` | `/healthz`, `/readyz` |
| `backend/src/pulseforge/api/routers/me.py` | `/v1/me` endpoints + schemas |
| `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/versions/0001_users_profile.py` | Schema migrations |
| `backend/tests/…` | Tests per module; `conftest.py` holds keys, tokens, app, DB fixtures |
| `infra/compose.yml` | Local Postgres 17 on port 54322 |
| `.github/workflows/ci.yml` | New `backend` job |
| `backend/README.md`, `docs/STATUS.md`, `CLAUDE.md`, `docs/BLUEPRINT.md` | Docs |

---

### Task 1: Package scaffold, settings, `/healthz`, CI job

**Files:**
- Create: `backend/pyproject.toml`, `backend/src/pulseforge/__init__.py`, `backend/src/pulseforge/core/__init__.py`, `backend/src/pulseforge/core/settings.py`, `backend/src/pulseforge/api/__init__.py`, `backend/src/pulseforge/api/app.py`, `backend/src/pulseforge/api/main.py`, `backend/src/pulseforge/api/routers/__init__.py`, `backend/src/pulseforge/api/routers/health.py`, `backend/tests/conftest.py`, `backend/tests/test_settings.py`, `backend/tests/test_health.py`
- Modify: `.github/workflows/ci.yml` (add `backend` job)

**Interfaces:**
- Produces: `Settings` (fields `database_url: str`, `supabase_url: str`, `jwt_audience: str = "authenticated"`, `tos_version: str = "v1"`; properties `jwks_url: str`, `jwt_issuer: str`); `get_settings() -> Settings` (lru_cache); `create_app(settings: Settings | None = None, *, verifier: "TokenVerifier | None" = None) -> FastAPI` (stores both on `app.state`); module-level `app = create_app()` lives in `pulseforge/api/main.py`, *not* in `app.py`, so importing the factory never needs env vars.
- Test fixture `settings` in `conftest.py`: `Settings(database_url=os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://nobody@127.0.0.1:1/none"), supabase_url="https://test.supabase.co")`.

- [ ] **Step 1: Create the branch and scaffold.** `git switch -c feat/backend-foundation`. Then in `backend/`: `uv init --package --name pulseforge --python 3.12` (or write `pyproject.toml` by hand). Use the `uv_build` backend, a `[project.optional-dependencies] api = ["fastapi", "uvicorn[standard]", "pydantic-settings", "sqlalchemy>=2", "psycopg[binary]>=3", "alembic", "pyjwt[crypto]>=2.8"]`, `[dependency-groups] dev = ["pytest", "httpx"]`, and `[tool.pytest.ini_options] testpaths = ["tests"]`. Run `uv sync --extra api`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_settings.py
def test_settings_derive_supabase_urls():
    s = Settings(database_url="postgresql+psycopg://x", supabase_url="https://abc.supabase.co/")
    assert s.jwks_url == "https://abc.supabase.co/auth/v1/.well-known/jwks.json"
    assert s.jwt_issuer == "https://abc.supabase.co/auth/v1"
    assert s.jwt_audience == "authenticated"
    assert s.tos_version == "v1"

# tests/test_health.py
def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

with `client` fixture = `TestClient(create_app(settings))`.

- [ ] **Step 3: Run:** `uv run pytest -v`. Expected: FAIL (import errors).

- [ ] **Step 4: Implement** `Settings` with pydantic-settings (`SettingsConfigDict(env_file=".env", extra="ignore")`; strip a trailing `/` from `supabase_url`), `create_app`, and `health.router` with `GET /healthz`.

- [ ] **Step 5: Run:** `uv run pytest -v`. Expected: 2 passed. `ruff check .` passes from the repo root.

- [ ] **Step 6: Add the CI job** `backend` to `.github/workflows/ci.yml`: `ubuntu-latest`, `working-directory: backend`, `actions/checkout@v7`, `actions/setup-python@v7` (3.12), `pip install uv`, `uv sync --extra api --locked`, `uv run pytest -v`.

- [ ] **Step 7: Commit:** `git add backend .github/workflows/ci.yml && git commit -m "feat(backend): scaffold package with settings and /healthz"`

---

### Task 2: Problem+JSON errors

**Files:**
- Create: `backend/src/pulseforge/core/problems.py`, `backend/tests/test_problems.py`
- Modify: `backend/src/pulseforge/api/app.py` (call `install_problem_handlers(app)`)

**Interfaces:**
- Produces: `class Problem(Exception)` with `__init__(self, status: int, title: str, detail: str | None = None, *, type_: str = "about:blank")`; `install_problem_handlers(app: FastAPI) -> None`, which handles `Problem`, Starlette `HTTPException`, `RequestValidationError` (422, with an `errors` list of `{"loc", "msg"}`) and any `Exception` (500, title `"Internal Server Error"`, no detail).

- [ ] **Step 1: Write the failing tests.** Tests add throwaway routes to `create_app(settings)` and use `TestClient(app, raise_server_exceptions=False)`.

```python
def test_unknown_route_is_problem_json(client):
    r = client.get("/nope")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json() == {"type": "about:blank", "title": "Not Found", "status": 404}

def test_problem_exception_renders(app_with_routes):   # route raises Problem(409, "Conflict", "already done")
    r = app_with_routes.get("/conflict")
    assert r.status_code == 409 and r.json()["detail"] == "already done"

def test_validation_error_is_422_problem(app_with_routes):  # POST /echo expects {"n": int}
    r = app_with_routes.post("/echo", json={"n": "x"})
    assert r.status_code == 422 and r.json()["title"] == "Validation Error"
    assert r.json()["errors"][0]["loc"][-1] == "n"

def test_unhandled_error_hides_details(app_with_routes):  # route raises RuntimeError("db password=hunter2")
    r = app_with_routes.get("/boom")
    assert r.status_code == 500 and "hunter2" not in r.text
    assert r.json() == {"type": "about:blank", "title": "Internal Server Error", "status": 500}
```

- [ ] **Step 2: Run:** `uv run pytest tests/test_problems.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `problems.py`, using `http.HTTPStatus(status).phrase` for titles of plain HTTP errors. Log unhandled exceptions with `logger.exception` before returning the 500.
- [ ] **Step 4: Run:** `uv run pytest -v`. Expected: all pass.
- [ ] **Step 5: Commit:** `git commit -am "feat(backend): RFC 9457 problem+json errors"` (`git add` the new files first).

---

### Task 3: Token verification

**Files:**
- Create: `backend/src/pulseforge/core/auth.py`, `backend/tests/test_auth.py`
- Modify: `backend/tests/conftest.py` (key and token fixtures)

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Claims: sub: uuid.UUID; email: str | None`
  - `class AuthError(Exception)` (maps to 401) and `class AuthUnavailable(Exception)` (maps to 503)
  - `SigningKeyGetter = Callable[[str], Any]` (raw token → public key)
  - `class TokenVerifier: __init__(self, *, issuer: str, audience: str, get_signing_key: SigningKeyGetter)`; `verify(self, token: str) -> Claims`; `@classmethod for_supabase(cls, settings: Settings) -> TokenVerifier`, which uses `jwt.PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=3600)` and `.get_signing_key_from_jwt(token).key`.
  - `ALGORITHMS = ["ES256", "RS256"]`, `LEEWAY_SECONDS = 30`
- Conftest fixtures: `private_key` (`ec.generate_private_key(ec.SECP256R1())`), `make_token(**claims_overrides) -> str` (defaults: `sub` new uuid4, `email "dj@example.com"`, `aud "authenticated"`, `iss "https://test.supabase.co/auth/v1"`, `role "authenticated"`, `exp now+3600`; a value of `None` removes that claim; signed ES256 with header `kid "test-key"`), `verifier` (getter returns `private_key.public_key()`).

- [ ] **Step 1: Write the failing tests**

```python
def test_valid_token_returns_claims(verifier, make_token):
    uid = uuid.uuid4()
    assert verifier.verify(make_token(sub=str(uid))) == Claims(sub=uid, email="dj@example.com")

@pytest.mark.parametrize("overrides", [
    {"exp": int(time.time()) - 120},          # expired beyond the 30 s leeway
    {"aud": "anon"},
    {"iss": "https://evil.example/auth/v1"},
    {"sub": None},
    {"sub": "not-a-uuid"},
    {"exp": None},
])
def test_bad_claims_rejected(verifier, make_token, overrides):
    with pytest.raises(AuthError):
        verifier.verify(make_token(**overrides))

def test_token_from_other_key_rejected(verifier):           # signed with a fresh EC key
def test_hs256_token_rejected(verifier):                    # jwt.encode(valid_claims, "secret", algorithm="HS256")
def test_unsigned_token_rejected(verifier):                 # jwt.encode(valid_claims, None, algorithm="none")
def test_garbage_token_rejected(verifier):                  # verifier.verify("abc.def") raises AuthError
def test_unknown_key_id_rejected(make_token):               # getter raises jwt.PyJWKClientError("no key") -> AuthError
def test_jwks_unreachable_raises_unavailable(make_token):   # getter raises jwt.PyJWKClientConnectionError -> AuthUnavailable
```

Each of the last six asserts `pytest.raises(AuthError)` or `pytest.raises(AuthUnavailable)` as named.

- [ ] **Step 2: Run:** `uv run pytest tests/test_auth.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `verify`. Get the key with the getter, catching `PyJWKClientConnectionError` → `AuthUnavailable` *before* `PyJWKClientError` → `AuthError` (the first is a subclass of the second). Then `jwt.decode(token, key, algorithms=ALGORITHMS, audience=..., issuer=..., leeway=LEEWAY_SECONDS, options={"require": ["exp", "sub", "aud", "iss"]})`; map any `jwt.InvalidTokenError` or `ValueError` from `uuid.UUID(sub)` to `AuthError`. Never pass the token's own `alg` header into `algorithms`.
- [ ] **Step 4: Run:** `uv run pytest -v`. Expected: all pass.
- [ ] **Step 5: Commit:** `git commit -m "feat(backend): verify Supabase JWTs locally via JWKS"`

---

### Task 4: Database, migration, `/readyz`

**Files:**
- Create: `infra/compose.yml`, `backend/src/pulseforge/db/__init__.py`, `backend/src/pulseforge/db/session.py`, `backend/src/pulseforge/db/models.py`, `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/migrations/versions/0001_users_profile.py`, `backend/tests/test_migrations.py`, `backend/tests/test_ready.py`
- Modify: `backend/src/pulseforge/api/routers/health.py`, `backend/src/pulseforge/api/app.py`, `backend/tests/conftest.py`, `.github/workflows/ci.yml` (postgres service + `TEST_DATABASE_URL`)

**Interfaces:**
- Produces: `class Base(DeclarativeBase)`; `make_session_factory(database_url: str) -> sessionmaker[Session]` (engine created with `pool_pre_ping=True`, `connect_args={"connect_timeout": 3}`), stored on `app.state.session_factory`; `UserProfile` mapped to `users_profile`.
- `users_profile` columns (BLUEPRINT §9): `id uuid PK` (no default), `display_name text NULL`, `plan text NOT NULL DEFAULT 'free' CHECK (plan IN ('free','creator','pro'))`, `ui_mode text NOT NULL DEFAULT 'simple' CHECK (ui_mode IN ('simple','pro'))`, `tos_version_accepted text NULL`, `tos_accepted_at timestamptz NULL`, `created_at timestamptz NOT NULL DEFAULT now()`, `updated_at timestamptz NOT NULL DEFAULT now()`.
- `migrations/env.py`: URL = `config.get_main_option("sqlalchemy.url")` if set, else `get_settings().database_url`; `target_metadata = Base.metadata`.
- Conftest: `database_url` fixture. If `TEST_DATABASE_URL` is unset, `pytest.fail` when `CI` is set and `pytest.skip` otherwise, so CI can never silently skip DB tests. A session-scoped `migrated_db` runs `alembic upgrade head` through `alembic.config.Config("alembic.ini")` with `sqlalchemy.url` overridden; a function-scoped `db_session` truncates `users_profile` after each test.
- `infra/compose.yml`: service `postgres`, image `postgres:17`, `POSTGRES_PASSWORD=postgres`, `POSTGRES_DB=pulseforge_test`, ports `54322:5432`, with a healthcheck on `pg_isready`.

- [ ] **Step 1: Start Postgres:** `docker compose -f infra/compose.yml up -d`, then set `TEST_DATABASE_URL` (see Global Constraints).
- [ ] **Step 2: Write the failing tests**

```python
def test_migration_creates_users_profile_with_defaults(migrated_db, db_session):
    uid = uuid.uuid4()
    db_session.execute(text("INSERT INTO users_profile (id) VALUES (:id)"), {"id": uid})
    row = db_session.execute(text("SELECT plan, ui_mode, created_at FROM users_profile WHERE id=:id"), {"id": uid}).one()
    assert (row.plan, row.ui_mode) == ("free", "simple") and row.created_at is not None

def test_ui_mode_check_constraint(migrated_db, db_session):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.execute(text("INSERT INTO users_profile (id, ui_mode) VALUES (:id, 'PRO')"), {"id": uuid.uuid4()})

def test_downgrade_then_upgrade_roundtrip(database_url):   # downgrade base -> table gone; upgrade head -> back

def test_readyz_ok_with_database(migrated_db, settings):
    r = TestClient(create_app(settings)).get("/readyz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}

def test_readyz_503_when_database_unreachable(settings):
    bad = settings.model_copy(update={"database_url": "postgresql+psycopg://nobody@127.0.0.1:1/none"})
    r = TestClient(create_app(bad)).get("/readyz")
    assert r.status_code == 503 and r.headers["content-type"].startswith("application/problem+json")
```

- [ ] **Step 3: Run:** `uv run pytest tests/test_migrations.py tests/test_ready.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement** the session factory, the model, `alembic.ini` (`script_location = migrations`), `env.py`, and the hand-written migration `0001` (revision id `"0001"`, `down_revision = None`). `/readyz` runs `SELECT 1` and raises `Problem(503, "Service Unavailable", "database unreachable")` on `sqlalchemy.exc.OperationalError`.
- [ ] **Step 5: Run:** `uv run pytest -v`. Expected: all pass.
- [ ] **Step 6: CI.** In the `backend` job, add the `services.postgres` block (same image, env and healthcheck as compose; port `5432:5432`) and the job env `TEST_DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/pulseforge_test`.
- [ ] **Step 7: Commit:** `git commit -m "feat(backend): users_profile migration, session factory and /readyz"`

---

### Task 5: `/v1/me` endpoints

**Files:**
- Create: `backend/src/pulseforge/db/profiles.py`, `backend/src/pulseforge/api/deps.py`, `backend/src/pulseforge/api/routers/me.py`, `backend/tests/test_me.py`
- Modify: `backend/src/pulseforge/api/app.py` (include the router; default `verifier=TokenVerifier.for_supabase(settings)`)

**Interfaces:**
- Consumes: `TokenVerifier.verify`, `Claims`, `AuthError`, `AuthUnavailable` (Task 3); `Problem` (Task 2); `UserProfile`, `app.state.session_factory` (Task 4).
- Produces:
  - `get_or_create_profile(session: Session, user_id: uuid.UUID) -> UserProfile`, using `postgresql.insert(UserProfile).values(id=user_id).on_conflict_do_nothing(index_elements=["id"])` and then a select.
  - Dependencies `get_session()` (yields a session and commits on success) and `current_claims(request) -> Claims`. The scheme match is case-insensitive; a missing or malformed header raises `Problem(401, "Unauthorized")` with a `WWW-Authenticate: Bearer` header. `AuthError` → 401, `AuthUnavailable` → `Problem(503, "Service Unavailable", "login service unreachable")`.
  - Schemas: `MeOut {id: UUID, email: str | None, display_name: str | None, plan: str, ui_mode: Literal["simple","pro"], tos_version_accepted: str | None, tos_accepted_at: datetime | None, tos_current_version: str, created_at: datetime}`; `MePatch {display_name: constr(strip_whitespace=True, min_length=1, max_length=50) | None = None, ui_mode: Literal["simple","pro"] | None = None}` with `extra="forbid"`; `TosAccept {version: str}` with `extra="forbid"`.
  - Not in this plan: the "remaining quota" fields of BLUEPRINT §10 (they arrive with `usage_ledger` in M2) and `DELETE /v1/me` (it needs uploads and storage to delete first).
  - Routes: `GET /v1/me` → `MeOut` (creates the profile on first call; `email` comes from the token, not the DB); `PATCH /v1/me` → `MeOut` (updates only the fields sent and bumps `updated_at`); `POST /v1/me/tos` → `MeOut` (a version different from `settings.tos_version` gives `Problem(409, "Conflict", "ToS version is not current")`).
- Test fixtures: `api` = `TestClient(create_app(settings, verifier=verifier))` with `migrated_db`; `auth(token) -> dict` builds the header.

- [ ] **Step 1: Write the failing tests**

```python
def test_get_me_creates_profile_with_defaults(api, make_token):
    uid = uuid.uuid4()
    r = api.get("/v1/me", headers=auth(make_token(sub=str(uid))))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(uid) and body["email"] == "dj@example.com"
    assert (body["plan"], body["ui_mode"], body["tos_version_accepted"], body["tos_current_version"]) == ("free", "simple", None, "v1")

def test_get_me_is_idempotent(api, make_token, db_session):        # two GETs: same created_at; COUNT(*) == 1
def test_get_me_when_row_already_exists(api, make_token, db_session):  # INSERT row first, then GET -> 200, COUNT(*) == 1

@pytest.mark.parametrize("header", [None, "Basic abc", "Bearer", "Bearer ", "Bearer not.a.jwt"])
def test_me_rejects_bad_auth_headers(api, header):
    r = api.get("/v1/me", headers={"Authorization": header} if header else {})
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/problem+json")
    assert r.headers["www-authenticate"] == "Bearer"

def test_me_accepts_lowercase_bearer(api, make_token):   # "bearer <token>" -> 200

def test_patch_me_updates_ui_mode_and_display_name(api, make_token):
    h = auth(make_token())
    r = api.patch("/v1/me", headers=h, json={"ui_mode": "pro", "display_name": "  DJ Imz  "})
    assert r.status_code == 200 and r.json()["ui_mode"] == "pro" and r.json()["display_name"] == "DJ Imz"
    assert api.get("/v1/me", headers=h).json()["ui_mode"] == "pro"

@pytest.mark.parametrize("payload", [{"plan": "pro"}, {"ui_mode": "PRO"}, {"display_name": ""}, {"display_name": "x" * 51}])
def test_patch_me_rejects_plan_and_bad_values(api, make_token, payload):   # 422 problem; a follow-up GET still shows plan "free", ui_mode "simple"

def test_accept_current_tos(api, make_token):           # POST {"version": "v1"} -> 200, tos_version_accepted "v1", tos_accepted_at not None
def test_accept_outdated_tos_conflicts(api, make_token): # POST {"version": "v0"} -> 409 problem

def test_me_returns_503_when_jwks_unreachable(settings, migrated_db, make_token):
    # verifier whose getter raises jwt.PyJWKClientConnectionError -> GET /v1/me is 503 problem
```

- [ ] **Step 2: Run:** `uv run pytest tests/test_me.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `profiles.py`, `deps.py` and `me.py` as specified in Interfaces.
- [ ] **Step 4: Run:** `uv run pytest -v` and `ruff check .` (repo root). Expected: all pass.
- [ ] **Step 5: Smoke-run the server:** `uv run uvicorn pulseforge.api.main:app --port 8000` with `DATABASE_URL` set to the test DB and `SUPABASE_URL=https://test.supabase.co`. Check that `GET http://localhost:8000/healthz` returns `{"status":"ok"}` and that `http://localhost:8000/docs` lists the three `/v1/me` routes.
- [ ] **Step 6: Commit:** `git commit -m "feat(backend): GET/PATCH /v1/me and ToS acceptance"`

---

### Task 6: Docs, PR, required check

**Files:**
- Create: `backend/README.md` (run locally: compose up, env vars, `uv run pytest`, `uv run alembic upgrade head`, `uv run uvicorn pulseforge.api.main:app`)
- Modify: `docs/STATUS.md` (M1a done; next M1b/M1c and the accounts they need), `CLAUDE.md` (backend commands), `docs/BLUEPRINT.md` §20 (decision: sync SQLAlchemy + psycopg 3 for the MVP; async only if load ever demands it), `CONTRIBUTING.md` (backend test command)

- [ ] **Step 1: Write the docs above.**
- [ ] **Step 2: Verify:** `ruff check .` and `cd backend && uv run pytest -v` both pass with `TEST_DATABASE_URL` set.
- [ ] **Step 3: Commit and open the PR:** `git commit -m "docs: backend foundation usage and status"`, `git push -u origin feat/backend-foundation`, then `gh pr create` with What/Why/Checked sections and the Claude Code footer line.
- [ ] **Step 4: Wait for CI:** `gh pr checks --watch`. Expected: `lint`, `phase0`, `secrets`, `backend` all pass.
- [ ] **Step 5: Merge:** `gh pr merge --squash --delete-branch`, then `git switch main && git pull --ff-only`.
- [ ] **Step 6: Make `backend` a required check.** Read ruleset `26042204` (`gh api repos/joseterdes/pulseforge/rulesets/26042204`), add `{"context": "backend"}` to the `required_status_checks` list, and `PUT` the full ruleset back. Verify with `gh api repos/joseterdes/pulseforge/rulesets/26042204 --jq '[.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context]'`. Expected: `["lint","phase0","secrets","backend"]`.
