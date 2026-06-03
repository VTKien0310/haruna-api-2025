---
name: refactor
description:
  Refactor FastAPI Python code into a layered architecture: thin HTTP routers, feature-organized domain logic, CQRS readers/writers with @classmethod handle(), services with class+handle()+Dep pattern, Pydantic request DTOs and domain entities, SQLModel DB models, FastAPI dependency-injection guards, strong typing throughout, and ruff-clean code. Use when asked to refactor, restructure, reorganize, or modernize FastAPI code. Invoke with a file path, directory path, or feature name as the argument.
compatibility: Python 3.10+, FastAPI, SQLModel or SQLAlchemy, Pydantic, ruff
disable-model-invocation: true
allowed-tools: Read Glob Grep Edit Write Bash(ruff *)
---

# What I Do

Refactor FastAPI Python code into a predefined layered architecture.

# When to Use Me

Trigger when the user says any of: refactor code, restructure code, reorganize code, modernize code.

# FastAPI Refactor Procedure

Refactor `$ARGUMENTS` to the layered FastAPI architecture below. If no argument is given, ask the user what to refactor.

## Step 1 — Read and classify

1. Read the target file(s) fully
2. List what each piece of code does and what layer it belongs to:
    - **HTTP**: routing, request parsing, response shaping — no business logic
    - **Service**: orchestrates a single use case — calls readers, writers, external ports
    - **Reader**: single read query against the DB (CQRS query side)
    - **Writer**: single write command against the DB (CQRS command side)
    - **Guard**: FastAPI dependency function that authenticates/authorizes and returns a domain model
    - **Request DTO**: Pydantic BaseModel for validated request bodies
    - **Entity**: domain model (Pydantic BaseModel) or DB table model (SQLModel table=True)
    - **Port**: adapter wrapping an external service (Supabase, Stripe, email, etc.)
    - **Core**: app-wide config, bootstrap wiring, error handlers, response middleware
3. Note what is wrong: business logic in routers, missing Dep aliases, missing `__init__.py` re-exports, weak typing,
   mixed concerns

## Step 2 — Plan the target layout

New or refactored FastAPI features belong under:

```
app/
├── core/              # pydantic-settings config, FastAPI bootstrap, error handlers, response middleware
├── database/          # SQLModel table models, async session manager, Alembic migrations
├── features/
│   └── <domain>/
│       ├── data/      # Readers (queries) and Writers (commands)
│       ├── entities/  # Domain models (Pydantic) and DB table models (SQLModel table=True)
│       ├── guards/    # Auth/authz FastAPI dependency functions
│       ├── requests/  # Request body DTOs (Pydantic BaseModel)
│       └── services/  # Business logic classes with handle()
├── http/              # APIRouter definitions — thin, no business logic
└── ports/             # External service adapters
```

For each new file, decide which subdirectory it belongs in before editing.

## Step 3 — Apply patterns

### Service

```python
from typing import Annotated
from fastapi import Depends


class CreateItemService:
    def __init__(
            self,
            db_session_manager: DbSessionManagerDep,
            find_reader: FindItemReaderDep,
    ) -> None:
        self.__db_session_manager = db_session_manager
        self.__find_reader = find_reader

    async def handle(self, user_id: str, name: str) -> Item:
        async with self.__db_session_manager.session() as db_session:
            existing = await self.__find_reader.handle(db_session, user_id)
        if existing:
            raise AppException(status_code=409, code="item_exists", message="Item already exists")
        # ... business logic ...
        return item


CreateItemServiceDep = Annotated[CreateItemService, Depends()]
```

- One service per use case; name = `<Verb><Noun>Service`
- Dependencies injected through `__init__`, stored as `self.__<name>` (double underscore = private)
- Use `db_session_manager.session()` for reads, `.transaction()` for writes that need rollback
- Export class + Dep from `services/__init__.py`

### Reader (CQRS query)

```python
from typing import Annotated
from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


class FindItemByIdReader:
    @classmethod
    async def handle(cls, db_session: AsyncSession, item_id: str) -> Item | None:
        result = await db_session.exec(select(Item).where(Item.id == item_id).limit(1))
        return result.first()


FindItemByIdReaderDep = Annotated[FindItemByIdReader, Depends()]
```

- `@classmethod` — no instance state
- Receives `AsyncSession` as parameter — caller manages the session context
- Export from `data/__init__.py`

### Writer (CQRS command)

```python
from typing import Annotated
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession


class UpdateItemWriter:
    @classmethod
    async def handle(cls, db_session: AsyncSession, item: Item) -> Item:
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        return item


UpdateItemWriterDep = Annotated[UpdateItemWriter, Depends()]
```

- Caller provides the session; writer commits if appropriate for the pattern
- Export from `data/__init__.py`

### Guard

```python
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_security = HTTPBearer()


async def _get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(_security)],
        some_port: SomePortDep,
) -> User:
    try:
        user = some_port.verify(credentials.credentials)
        return UserFactory.from_external(user)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


AuthGuardDep = Depends(_get_current_user)
CurrentUserDep = Annotated[User, Depends(_get_current_user)]
```

- Private function prefixed with `_`; export only the Dep aliases
- `AuthGuardDep` used in `router = APIRouter(dependencies=[AuthGuardDep])`
- `CurrentUserDep` used as a route parameter when you need the user object
- Export from `guards/__init__.py`

### Request DTO

```python
from pydantic import BaseModel


class CreateItemRequest(BaseModel):
    name: str
    collection_id: str
```

- Pure Pydantic — no logic
- Export from `requests/__init__.py`

### Entity (domain model)

```python
from pydantic import BaseModel


class Item(BaseModel):
    id: str
    name: str
    user_id: str
```

### Entity (DB table model)

```python
from uuid import uuid4
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime


class Item(SQLModel, table=True):
    metadata = model_common_metadata  # required for Alembic autogenerate
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(index=True)
    name: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
```

- DB table models go in `app/database/models.py`, not in `features/`
- Must set `metadata = model_common_metadata`

### HTTP Router (thin)

```python
from fastapi import APIRouter
from app.features.item.guards import AuthGuardDep, CurrentUserDep
from app.features.item.requests import CreateItemRequest
from app.features.item.services import CreateItemServiceDep

router = APIRouter(prefix="/items", tags=["item"], dependencies=[AuthGuardDep])


@router.post("")
async def create_item(
        request: CreateItemRequest,
        current_user: CurrentUserDep,
        service: CreateItemServiceDep,
):
    return await service.handle(current_user.id, request.name)
```

- No business logic — delegate everything to services
- Register the router in the app factory's `router_registry`

### AppException (domain errors)

```python
from app.core.error import AppException
from fastapi import status

raise AppException(
    status_code=status.HTTP_404_NOT_FOUND,
    code="item_not_found",
    message=f"Item {item_id} not found",
)
```

- Use `AppException` for domain errors (custom code + message)
- Use `HTTPException` only for standard protocol errors

### `__init__.py` re-exports

```python
# features/item/services/__init__.py
from .create_item_service import CreateItemService as CreateItemService
from .create_item_service import CreateItemServiceDep as CreateItemServiceDep
```

- Every public class and Dep alias must be re-exported from the package `__init__.py`
- Enables clean imports: `from app.features.item.services import CreateItemServiceDep`

## Step 4 — Naming conventions

| Component | File name                   | Class / symbol                                |
|-----------|-----------------------------|-----------------------------------------------|
| Service   | `create_item_service.py`    | `CreateItemService`, `CreateItemServiceDep`   |
| Reader    | `find_item_by_id_reader.py` | `FindItemByIdReader`, `FindItemByIdReaderDep` |
| Writer    | `update_item_writer.py`     | `UpdateItemWriter`, `UpdateItemWriterDep`     |
| Guard     | `auth_guard.py`             | `AuthGuardDep`, `CurrentUserDep`              |
| Request   | `create_item_request.py`    | `CreateItemRequest`                           |
| Entity    | `item_entity.py`            | `Item`, `ItemFactory`                         |
| Router    | `item_router.py`            | `router`                                      |

## Step 5 — Strong typing

- Annotate all function parameters and return types
- No bare `dict` or `list` — use `dict[str, str]`, `list[Item]`, etc.
- Avoid `Any` — if unavoidable, add a comment explaining why
- Use `T | None` instead of `Optional[T]` (Python 3.10+)
- Use `Annotated[T, Depends(...)]` for all FastAPI dependency aliases

## Step 6 — Format and verify

After all edits:

```bash
source .venv/bin/activate
ruff format
ruff check
deactivate
```

Fix every lint issue before reporting done. Do not silence errors without justification.

## Definition of done

- [ ] Routers are thin — no business logic, only parse + delegate + return
- [ ] Services use class + `handle()` + `*Dep = Annotated[T, Depends()]`
- [ ] DB operations are readers/writers with `@classmethod handle(cls, db_session, ...)`
- [ ] Guards are private dependency functions with exported Dep aliases
- [ ] Request bodies are Pydantic BaseModel in `requests/`
- [ ] Domain models are Pydantic BaseModel in `entities/`
- [ ] DB table models are SQLModel `table=True` with `metadata = model_common_metadata`
- [ ] All public symbols re-exported from `__init__.py`
- [ ] Strong typing throughout — no unjustified `Any`, all returns and params annotated
- [ ] `ruff format && ruff check` passes

## Supporting references

- Full working code examples (complete files, factory patterns, complex
  queries): [references/patterns.md](references/patterns.md)
- Architecture overview, data flow, core module roles, DB session
  manager: [references/architecture.md](references/architecture.md)
