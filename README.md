# haruna-api-2025

## About

This application is the back-end API for the HarunaDB project.
It provides a small amount of functionality that should or can only run on the server to support the project's needs.

The application's namesake is derived from the
battleship [Haruna](https://en.wikipedia.org/wiki/Japanese_battleship_Haruna).

## Project specification

- FastAPI
- Supabase
- PostgreSQL via SQLModel, SQLAlchemy, and asyncpg

## System requirement

- Python 3.14
- uv package and project manager
- Docker

## Project setup for development

### Create a virtual environment

```shell
uv venv
```

### Install dependencies using uv

```shell
uv sync
```

### Set up environment variablesSet up environment variables

- Copy the example environment file using:

```shell
cp .env.example .env
```

- Edit `.env` and fill in your configuration values

`LOG_LEVEL` sets the level of the `app` logger. Use `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. The default is `INFO`. You can leave it out of `.env`.

The API writes its log lines to stderr. `fly logs` shows those lines. Fly.io does not need a new secret for logging.

A FastAPI-built feature dependency takes its feature-specific `<Name>LoggerDep` from `app/features/<feature>/logger.py`. For example, `AuthenticationLoggerDep` injects `app.auth`. Port constructors use `Annotated[logging.Logger, Depends(logger_dependency(name))]` directly. Middleware and startup call `get_logger("auth")` directly.

For direct PostgreSQL access, configure `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `DB_SCHEMA`.
The asynchronous connection settings support Supabase's connection pooler as well as a direct database host. Keep the
password in server-side environment configuration and use a least-privilege database role where practical. Supabase
authentication, object storage, and simple table queries continue to use the Supabase client.

SQLModel table models describe the existing schema. This application does not manage migrations or create hosted
tables at startup.

`SUPABASE_SERVICE_ROLE_KEY` may be a secret key (`sb_secret_...`) or a legacy JWT `service_role` key. A secret key is sent only in the `apikey` header. A legacy JWT key is also sent as `Authorization: Bearer`.

Protected routes verify the caller's Supabase access token in the API process. Public keys are loaded from
`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`. Only ES256 and RS256 access tokens are accepted. Verification
accepts a token until it expires and does not see a ban, deletion, or sign-out that happens earlier.
`User.created_at` comes from a `created_at` claim when the token has one, and otherwise from the token's
issued-at time. Callers use `user.id`.

### Running the Development Server

```shell
uvicorn app.main:app --reload
```

- The API will be available at: `http://localhost:8000`
- The `--reload` flag enables auto-restart when code changes are detected
- All changes to Python files in the `app/` directory will trigger an automatic reload
- Check the console output for any startup errors or warnings

## Code quality

```shell
ruff format
```

## Application tests

Tests run in memory. They do not read `.env`, call Supabase, call the AI service, connect to PostgreSQL, or open a network connection. Supabase table rows and direct SQLModel records use fresh in-memory SQLite databases. Rules are in [Application tests](doc/conventions-and-standards/application-tests.md).

```shell
uv run pytest
uv run pytest tests/features/media
uv run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=lcov
```

Coverage is written to `coverage/` and is not a merge gate.

## Deploying to Fly.io

This project is ready to run on Fly.io using the included `Dockerfile` and `fly.toml`.

### Prerequisites

- Install Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
- Have a Fly.io account and be logged in: `fly auth login`

### Deploy

- (Optional) Configure secrets (for any env values you need): `fly secrets set KEY=value OTHER=value`
- From the project root, run: `fly deploy`
- Open the app in your browser: `fly open`

### Notes:

- The service listens on internal port 8000 (mapped to 80/443 externally). `PORT=8000` is set in `fly.toml` and the
  scontainer.
- The app uses `pydantic-settings`; environment variables can override defaults in `app/core/config.py`.
- Logs go to stderr at `INFO` unless you set `LOG_LEVEL`. You do not need a new Fly secret.
- Scale memory/CPU (example): `fly scale vm shared-cpu-1x --memory 256`
- Set min/max machines via `fly scale count` or adjust autoscaling in `fly.toml`.

## Local build/run

- Build: `docker build -t haruna-api-2025 .`
- Run: `docker run -p 8000:8000 haruna-api-2025`
- The app will be available at: `http://localhost:8000/`

## Conventions and standards

- [Coding](./doc/conventions-and-standards/coding.md)
- [RESTful API](./doc/conventions-and-standards/restful-api.md)
- [Security](./doc/conventions-and-standards/security.md)
- [Git](./doc/conventions-and-standards/git.md)
- [Application tests](./doc/conventions-and-standards/application-tests.md)

## Design and decision documentation

Documentation for design and decision reasoning is available in the [doc/design-and-decision](doc/design-and-decision)
directory.