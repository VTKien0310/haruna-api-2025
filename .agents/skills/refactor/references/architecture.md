# Architecture Reference

## Directory structure

```
app/
├── __init__.py              # App factory: create_app(), router_registry, lifespan
├── main.py                  # Entrypoint: uvicorn runner
├── core/
│   ├── config.py            # pydantic-settings: Settings class, global `settings` instance
│   ├── bootstrap.py         # bootstrap_application(): wires FastAPI, middleware, routes
│   ├── error.py             # AppException, HTTPException handler, validation handler
│   └── response.py          # _WrapResponseMiddleware: wraps all JSON as {"ok": bool, "content": ...}
├── database/
│   ├── models.py            # All SQLModel table=True models (single file)
│   ├── session.py           # DbSessionManager, DbSessionManagerDep
│   ├── env.py               # Alembic env: constructs URL from settings, sets target_metadata
│   ├── versions/            # Alembic migration scripts
│   └── script.py.mako       # Template for new migrations
├── features/
│   └── <domain>/            # One directory per bounded domain (authentication, item, ...)
│       ├── data/
│       │   ├── __init__.py
│       │   ├── find_<entity>_reader.py
│       │   └── <verb>_<entity>_writer.py
│       ├── entities/
│       │   ├── __init__.py
│       │   ├── <entity>_entity.py
│       │   └── <entity>_factory.py
│       ├── guards/
│       │   ├── __init__.py
│       │   └── <name>_guard.py
│       ├── requests/
│       │   ├── __init__.py
│       │   └── <verb>_<entity>_request.py
│       └── services/
│           ├── __init__.py
│           └── <verb>_<entity>_service.py
├── http/
│   ├── <domain>_router.py   # One router file per domain
│   └── request/             # Shared request parsing utilities (e.g. list params)
└── ports/
    ├── <service>.py         # Adapter wrapping an external service
    └── __init__.py
```

---

## Layer responsibilities

### `core/`

Application-wide infrastructure. Not domain-specific.

- **`config.py`**: `pydantic-settings` `Settings` class reads environment variables. All secrets come from here — no
  hardcoded values. A module-level `settings` singleton is instantiated once and imported everywhere.
- **`bootstrap.py`**: `bootstrap_application(router_registry, lifespan_handler)` creates and wires the FastAPI app: CORS
  middleware, error handlers, response middleware, and all routers.
- **`error.py`**: `AppException(status_code, code, message)` extends `HTTPException` with a semantic `code` field.
  Exception handlers convert to `{"error": {"code", "message", "path"}}` JSON. Use `AppException` for domain errors,
  `HTTPException` for standard HTTP errors.
- **`response.py`**: `_WrapResponseMiddleware` intercepts every JSON response and rewraps it as
  `{"ok": true, "content": <original_body>}` (or `{"ok": false, "error": ...}` for errors). Routers return plain
  dicts/models; wrapping is automatic.

### `database/`

All database concerns in one place.

- **`models.py`**: Every SQLModel `table=True` model lives here. Must set `metadata = model_common_metadata` for Alembic
  to detect it.
- **`session.py`**: `DbSessionManager` holds the async engine and session factory. Two context managers:
    - `.session()` — auto-closed session, no transaction (for reads)
    - `.transaction()` — begins, commits on exit, rolls back on exception (for writes)
- **`env.py`** + **`versions/`**: Alembic config. Run `alembic revision --autogenerate -m "..."` after changing models,
  then `alembic upgrade head`.

### `features/<domain>/`

All domain logic, organized by bounded context. A domain is a cohesive area of the business (e.g., `authentication`,
`item`, `billing`).

- **`data/`**: CQRS readers and writers. Readers query; writers mutate. Both use
  `@classmethod handle(cls, db_session, ...)`. No FastAPI-specific code except the `Dep` alias.
- **`entities/`**: Domain models that cross layer boundaries. Pydantic `BaseModel` for in-memory representations.
  SQLModel `table=True` models go in `database/models.py`, not here. Factories transform external data into domain
  models.
- **`guards/`**: FastAPI dependency functions. Private (`_` prefix). Export only `*GuardDep = Depends(fn)` and
  `Current*Dep = Annotated[T, Depends(fn)]`.
- **`requests/`**: Request body DTOs. Pure Pydantic `BaseModel`. No logic.
- **`services/`**: Business logic classes. Each service orchestrates one use case: reads data, applies logic, writes
  results, calls ports, raises `AppException` on domain errors.

### `http/`

FastAPI router definitions only. No business logic.

- One `APIRouter` per domain, in its own file
- Route handlers: inject dependencies, delegate to services, return results
- Register routers in `app/__init__.py` via `router_registry`

### `ports/`

Adapters for external services (Supabase, Telegram, Stripe, etc.).

- Wrap third-party SDKs behind a project-local API
- Injected into services as dependencies via `*PortDep = Annotated[Port, Depends()]`

---

## Request data flow

```
HTTP Request
  │
  ▼
http/<domain>_router.py
  │  FastAPI resolves dependencies:
  │  - Guard (auth) from guards/
  │  - Service instance from services/
  │  - Current user from guard
  │
  ▼
features/<domain>/services/<verb>_<entity>_service.py
  │  .handle(...) orchestrates:
  │  - Opens db_session_manager.session() or .transaction()
  │  - Calls reader(s) via FindXReader.handle(db_session, ...)
  │  - Calls writer(s) via UpdateXWriter.handle(db_session, ...)
  │  - Calls port(s) for external side effects
  │  - Raises AppException on domain errors
  │
  ▼
features/<domain>/data/<verb>_<entity>_reader/writer.py
  │  @classmethod handle(cls, db_session, ...)
  │  Uses SQLModel select(), db_session.exec(), .add(), .commit(), etc.
  │
  ▼
database/models.py  →  PostgreSQL
  │
  ▼
HTTP Response
  │  Response body returned from router handler
  │  _WrapResponseMiddleware wraps as: {"ok": true, "content": <body>}
  │  Error handlers wrap as: {"ok": false, "error": {"code", "message", "path"}}
```

---

## Dependency injection wiring

FastAPI resolves `Depends()` transitively at request time. No manual wiring needed.

```python
# Service declares its dependencies in __init__:
class MyService:
    def __init__(self, db: DbSessionManagerDep, reader: FindXReaderDep): ...


MyServiceDep = Annotated[MyService, Depends()]


# Router uses the service:
@router.post("/")
async def endpoint(service: MyServiceDep, user: CurrentUserDep):
    return await service.handle(user.id)
```

FastAPI sees `MyServiceDep`, instantiates `MyService`, sees it needs `DbSessionManagerDep` and `FindXReaderDep`,
resolves those first. All transitive dependencies are resolved automatically.

---

## Global response interface

Every JSON response is automatically wrapped:

Success:

```json
{
  "ok": true,
  "content": <your_return_value>
}
```

Error (AppException or HTTPException):

```json
{
  "ok": false,
  "error": {
    "code": "...",
    "message": "...",
    "path": "/api/..."
  }
}
```

Validation error (422):

```json
{
  "ok": false,
  "error": {
    "code": "validation_error",
    "message": "...",
    "details": [
      ...
    ],
    "path": "..."
  }
}
```

Routers do not need to manually wrap responses — the middleware handles it.

---

## Alembic migration workflow

```bash
source .venv/bin/activate

# After modifying any SQLModel table model in app/database/models.py:
alembic revision --autogenerate -m "add item table"

# Review the generated file in app/database/versions/ before applying

# Apply pending migrations:
alembic upgrade head

# Check status:
alembic current
alembic history

deactivate
```

Key rule: all SQLModel `table=True` models must set `metadata = model_common_metadata` (imported from
`app/database/models.py`) for Alembic autogenerate to detect them.
