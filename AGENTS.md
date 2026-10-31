# Haruna API development guide

## General

Haruna API 2025 is the back-end API for HarunaDB, a multipurpose everyday app. The API owns server-side work.

**Stack:** FastAPI, Supabase (auth and object storage), Pydantic + pydantic-settings, Pillow, Python 3.14, uv, Ruff,
Fly.io (Docker).

Prioritize **security, maintainability, and clarity** over cleverness. Follow FastAPI and Python best practices. Prefer
simple, readable, composable solutions, and keep the HTTP layer, features, and external ports separate.

## Architecture

```
app/
├── core/          # Config, bootstrap, error handling, response wrapping
├── features/      # Domain logic organized by feature (auth, media, ...)
│   ├── data/      # Readers (queries) and Writers (commands) via Supabase
│   ├── entities/  # Domain models (dataclasses), enums
│   ├── guards/    # Auth guards (Supabase bearer token)
│   ├── requests/  # Request DTOs (Pydantic BaseModel)
│   └── services/  # Business logic services
├── http/          # FastAPI routers (thin, no business logic)
├── ports/         # External service adapters (Supabase)
├── __init__.py    # App factory (create_app)
└── main.py        # Entrypoint
```

Routers in `http/` only parse requests, delegate to services, and return responses. Domain logic stays in `features/`.

**Buckets:** layout and purpose of each storage bucket are in
[doc/design-and-decision/storage-buckets.md](doc/design-and-decision/storage-buckets.md).

## Conventions

Python style and implementation patterns are in
[doc/conventions-and-standards/coding.md](doc/conventions-and-standards/coding.md). Route rules are in
[doc/conventions-and-standards/restful-api.md](doc/conventions-and-standards/restful-api.md).

Services, readers, and writers are classes with `handle()`. Inject dependencies in `__init__` and store them on `__`
private attributes. Readers run read-only queries through `SupabasePort` and may return `Model | None`. Writers mutate
(insert, update, delete) through `SupabasePort`. Export each class from its package `__init__.py` (services from
`services/__init__.py`). Readers and writers also export a `Dep` alias:

```python
class FindByUserIdReader:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(self, user_id: str) -> User | None:
        ...


FindByUserIdReaderDep = Annotated[FindByUserIdReader, Depends()]
```

Guards are FastAPI dependencies that return the authenticated user. Export aliases for routers:

```python
AuthenticatedGuardDep = Depends(_get_user_from_supabase_token)
CurrentAuthenticatedUserDep = Annotated[User, Depends(_get_user_from_supabase_token)]
```

- Request bodies are Pydantic `BaseModel`s in the feature's `requests/`.
- Domain models that do not map to a DB table are `@dataclass`es in `entities/`, with `@classmethod` factories (for
  example `from_spb_data`) for Supabase rows.
- Every `__init__.py` re-exports its public API (classes, `Dep` aliases). Import from the package `__init__.py`, not
  deep module paths. Do not skip re-exports for new modules.
- Organize by feature. Keep services, readers, and writers lean. Extract shared utilities when reuse is justified. Do
  not over-abstract, duplicate logic, or over-engineer simple features. Add a dependency only with a clear reason.
- Use strong typing on signatures and attributes. Avoid `Any` unless justified. Prefer `__` private methods.
- Match existing style. Be explicit. Comment only when it adds real value. Leave no dead code, commented-out blocks, or
  placeholders unless asked.
- Domain errors use `AppException`. Standard HTTP errors use `HTTPException`. Success responses are wrapped
  automatically by middleware as `{"ok": true, "content": ...}`.

## Supabase vs API

The client calls Supabase or this API. Use Supabase when the client can do the work with the Supabase client. Use this
API when the work must run on the server.

**Supabase:** sign-in and token verification, object storage (upload, download, signed URLs), and simple queries through
the Supabase client.

**API:** complex business logic, media processing (thumbnails and image manipulation), and any logic that must stay off
the client. Client code is inspectable, so that logic does not belong there.

## Security

Follow the security requirements in
[doc/conventions-and-standards/security.md](doc/conventions-and-standards/security.md). In particular:

- Never hardcode secrets, tokens, API keys, or service credentials, and never expose Supabase service credentials in
  responses or logs.
- Load configuration from environment variables via `pydantic-settings` in [`app/core/config.py`](app/core/config.py).
  Do not hardcode a value when an environment variable exists.
- Validate inputs with Pydantic. Respect Supabase bearer-token authentication and authorization.
- Be cautious with file uploads, metadata, and downloads. Do not log or return sensitive user or file data, including in
  error messages.

## Workflow

Activate the virtual environment before any Python command. After creating or editing code, format and lint, then
deactivate. Fix lint issues you introduce. Do not ignore a lint error without a documented reason.

```bash
source .venv/bin/activate
ruff format
ruff check
deactivate
```

A task is done when it follows FastAPI and Python best practices and the patterns above, new modules are exported,
typing has no unjustified `Any`, security has been considered, Ruff has been run, and important assumptions or tradeoffs
are stated.

Make the smallest change that fully solves the problem. Do not change architecture broadly unless asked. Ask before
proceeding when requirements conflict, security boundaries are unclear, a change could affect authentication or
authorization, or the change is risky or irreversible. Suggest practical improvements over speculative refactors.

If details are unclear, prefer, in order: security, simplicity, maintainability, consistency with the existing codebase.
