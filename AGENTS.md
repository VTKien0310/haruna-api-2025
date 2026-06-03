# AGENTS.md

## About

Haruna API 2025 is the back-end API for the HarunaDB project — a multipurpose application for everyday use that
provides:

- Images and videos storage
- Translation for English and Japanese
- Web bookmarks management

This API provides server-side functionality to support the project's needs, including media processing (thumbnail
generation) and authentication via Supabase.

The application's namesake is derived from the
battleship [Haruna](https://en.wikipedia.org/wiki/Japanese_battleship_Haruna).

### Tech Stack

- **Backend framework:** FastAPI
- **Auth & storage:** Supabase (authentication, object storage)
- **Data validation:** Pydantic + pydantic-settings
- **Image processing:** Pillow
- **Python version:** 3.14
- **Package manager:** uv
- **Linter/Formatter:** Ruff
- **Deployment:** Fly.io (Docker)

## Core Principles

- Prioritize **security, maintainability, and clarity** over cleverness
- Follow **FastAPI best practices**
- Follow **Python best practices**
- Prefer **simple, readable, composable solutions**
- Respect the separation of responsibilities between the HTTP layer, features, and external ports

## Virtual Environment

- **Always** activate the virtual environment before running any Python command:
  ```bash
  source .venv/bin/activate
  ```
- When finished running Python commands, deactivate:
  ```bash
  deactivate
  ```

## Architecture

```
app/
├── core/          # Config, bootstrap, error handling, response wrapping
├── features/      # Domain logic organized by feature (auth, media, ...)
│   ├── data/      # Readers (database operations via Supabase)
│   ├── entities/  # Domain models (dataclasses), enums
│   ├── guards/    # Auth guards (Supabase bearer token)
│   ├── requests/  # Request DTOs (Pydantic BaseModel)
│   └── services/  # Business logic services
├── http/          # FastAPI routers (thin, no business logic)
├── ports/         # External service adapters (Supabase)
├── __init__.py    # App factory (create_app)
└── main.py        # Entrypoint
```

### Layers

- **`http/`** — Thin routers. Parse requests, delegate to services, return responses. No business logic.
- **`features/`** — All domain logic. Organized by feature. Each feature has `data/`, `entities/`, `guards/`,
  `requests/`, `services/`.
- **`ports/`** — Adapters for external services (Supabase client).
- **`core/`** — Application-wide config (`pydantic-settings`), bootstrap wiring, error/response middleware.

### Supabase Buckets

- `medias` — Original media files (images/videos)
- `thumbnails` — Video thumbnails
- `resized` — Resized/generated thumbnails

## Coding Standards

### Services

- Services are **classes** with a `handle()` method containing business logic
- Inject dependencies via `__init__`, use private attributes with double-underscore prefix
- Export the class from the feature's `services/__init__.py`:
  ```python
  class MyService:
      def __init__(self, dependency: SomeDep):
          self.__dependency = dependency

      def handle(self, ...) -> ResultType:
          ...
  ```

### Data Access (Readers)

- Database operations are organized as **reader** classes in each feature's `data/` directory
- Use instance methods with `handle()` that query via `SupabasePort`
- Export the class and a `Dep` alias:
  ```python
  class FindByUserIdReader:
      def __init__(self, supabase: SupabasePortDep) -> None:
          self.__supabase = supabase

      def handle(self, user_id: str) -> User | None:
          ...

  FindByUserIdReaderDep = Annotated[FindByUserIdReader, Depends()]
  ```

### Guards

- Guards are **FastAPI dependency functions** that return authenticated user objects
- Export `Depends(...)` aliases for use as router dependencies:
  ```python
  AuthenticatedGuardDep = Depends(_get_user_from_supabase_token)
  CurrentAuthenticatedUserDep = Annotated[User, Depends(_get_user_from_supabase_token)]
  ```

### Request DTOs

- Use **Pydantic BaseModel** classes for request bodies
- Place in the feature's `requests/` directory

### Entities

- Use **`@dataclass`** for domain models that do not map to a DB table
- Include `@classmethod` factory methods (e.g., `from_spb_data`) for Supabase data conversion
- Place in the feature's `entities/` directory

### Exports

- Every `__init__.py` should re-export the public API of its module (classes, `Dep` aliases)
- Keep imports clean by importing from package-level `__init__.py` rather than deep module paths

### General

- Use **strong typing** everywhere. Annotate function signatures and class attributes
- Avoid `Any` unless there is a clear and justified reason
- Prefer **private methods** with double-underscore prefix (`__method`)
- Keep services and readers lean. Extract reusable logic into shared utilities when justified
- Keep code concise, readable, and easy to reason about
- Avoid duplication; extract reusable pieces when justified
- Do not over-abstract prematurely
- Match the existing codebase style and conventions when editing existing files
- Prefer explicitness over hidden behavior
- Add comments only when they provide real value
- Do not leave dead code, commented-out blocks, or placeholder implementations unless explicitly requested

## Supabase Usage

Use **Supabase** for:

- User authentication (sign-in, token verification)
- Object storage (file upload, download, signed URLs)
- Data storage (via Supabase client for simple queries)

Use **API logic** for:

- Complex business logic
- Media processing (thumbnails, image manipulation)
- Any logic that needs to be protected from client-side access

## Security Requirements

- **Never** hardcode secrets, tokens, API keys, or service credentials
- **Never** expose Supabase service credentials in responses or logs
- All configuration comes from environment variables via `pydantic-settings` (`app/core/config.py`)
- Assume all client code is inspectable by end users
- Validate inputs rigorously using Pydantic models
- Be cautious with file uploads, metadata handling, and download flows
- Respect authentication and authorization boundaries (Supabase bearer token)
- Avoid logging sensitive user or file data

## Code Quality

After creating or editing code, always run:

```bash
source .venv/bin/activate
ruff format
ruff check
deactivate
```

Rules:

- Fix any lint issues introduced by your changes
- Do not ignore lint errors without a documented reason

## Definition of Done

A task is only considered complete when all of the following are true:

- The implementation follows FastAPI and Python best practices
- Services use the class + `handle()` pattern
- Data access uses reader classes with `handle()` method
- New modules are properly exported via `__init__.py`
- Code is strongly typed with no unjustified `Any`
- Security implications have been considered
- `ruff format` and `ruff check` have been run after the changes
- Any important assumptions or tradeoffs are clearly communicated

## Agent Behavior Expectations

- Make the smallest reasonable change that fully solves the problem
- Do not make broad architectural changes unless explicitly requested
- Ask for clarification if:
    - Requirements conflict
    - Security boundaries are unclear
    - A change could affect authentication or authorization rules
- When suggesting improvements, prefer practical recommendations over speculative refactors

## Preferred Implementation Patterns

- Feature-based module organization
- Services with `handle()` method
- Readers with `handle()` method + `*Dep = Annotated[T, Depends()]`
- Guards as FastAPI dependency functions
- Pydantic BaseModel for request DTOs
- `@dataclass` for domain entities
- Consistent error responses via `AppException`
- Use the global response wrapper (`{"ok": true, "content": ...}`) — applied automatically via middleware

## Avoid

- Business logic in HTTP routers (routers should be thin)
- Hardcoded configuration values when environment variables are available
- Unstructured error responses (use `AppException` for domain errors, `HTTPException` for standard HTTP errors)
- Leaking sensitive data into logs, responses, or error messages
- Overengineering simple features
- Introducing dependencies without clear justification
- Skipping `__init__.py` re-exports for new modules

## If Unsure

If implementation details are unclear, prefer:

1. security
2. simplicity
3. maintainability
4. consistency with the existing codebase

When in doubt, ask for clarification before making risky or irreversible changes.
