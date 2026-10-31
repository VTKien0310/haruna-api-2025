# **CODING CONVENTIONS AND STANDARDS**

# **Python**

- Code format:

| Format                                     | Lint                                 | Note                           |
|:-------------------------------------------|:-------------------------------------|:-------------------------------|
| [PEP 8](https://peps.python.org/pep-0008/) | [Ruff](https://docs.astral.sh/ruff/) | `ruff format` and `ruff check` |

- Must run `ruff format` and `ruff check` inside `.venv` after Python changes
- Must use snake_case for modules, functions, variables, and methods; PascalCase for classes; and
  SCREAMING_SNAKE_CASE for settings fields that mirror environment variables. _Ex: `SUPABASE_URL`, `AI_API_KEY` in
  `app/core/config.py`_
- Must name files after their role:
  `*_service.py`, `*_reader.py`, `*_writer.py`, `*_request.py`, `*_entity.py`, `*_guard.py`, `*_router.py`
- Must use strong typing on function signatures and attributes. Avoid `Any` unless there is a clear reason
- Must use `"` for strings. `ruff format` enforces this
- Must prefix private instance attributes and methods with `__` (_ex: `self.__supabase`, `__create_thumbnail`_) and
  module-private functions with `_` (_ex: `_get_user_from_supabase_token`, `_get_supabase_client`_)

# **Conventions**

- Must keep the HTTP, feature, port, and core layers separate:
    - `app/http/` — thin routers: parse the request, delegate, and return a plain value. Register each `APIRouter`
      in `router_registry` (`app/http/__init__.py`). `bootstrap_application` mounts them under `settings.API_PREFIX`
      (`/api`)
    - `app/features/` — domain logic, one package per feature (`auth`, `media`, `translation`), using `data/`,
      `entities/`, `guards/`, `requests/`, and `services/` as needed
    - `app/ports/` — adapters for external services (`SupabasePort`, `AiApiPort`)
    - `app/core/` — settings, bootstrap, `AppException`, response wrapping, and shared HTTP clients
- Must implement services, readers, and writers as classes with `handle()`. Inject dependencies in `__init__` and
  export a `*Dep = Annotated[T, Depends()]` alias. _Ex: `FindMediaByIdReader`_
- Must implement guards as private FastAPI dependencies. Export `AuthenticatedGuardDep` and
  `CurrentAuthenticatedUserDep`. Protected routers set `dependencies=[AuthenticatedGuardDep]`
- Must use Pydantic `BaseModel` request DTOs with `Field` constraints. _Ex: `CreateThumbnailRequest`,
  `TranslateRequest`_
- Must use `@dataclass` for domain models, with a factory such as `from_spb_data` or `from_spb_auth`. _Ex: `Media`,
  `User`, `TranslationHistory`_. Keep related enums beside the model. _Ex: `MediaType`, `AiRequestRole`_
- Must re-export public names from each package `__init__.py` (`from .module import Name as Name`) and import
  from the package rather than a deep module path
- Must use lowercase path segments under `/api`. Path parameters use snake_case. A multi-word segment uses `-`. _Ex:
  `/medias/{media_id}/thumbnails`, `/translation/translate`_
- Must give variables, functions, and classes easy-to-understand names. A long but clear name is better than a
  short but ambiguous one
- Must document application setup, environment configuration, and dependencies in the project README
- Should prefer a conditional expression over `if`/`else` for short, simple logic. _Ex: `value if condition else other`_
- Should prefer guard clauses that return or raise early over deeply nested `if` blocks. _Ex: language checks in
  `TranslateService.handle`_
- Must raise `AppException(status_code, code, message)` for domain failures. Handlers in `app/core/error.py` and
  `_WrapResponseMiddleware` wrap the result. Success is `{"ok": true, "content": ...}`. Failure is
  `{"ok": false, "content": {"error": ...}}`. Routers return the inner value and do not wrap it themselves
