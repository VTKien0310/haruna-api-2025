# Pattern Reference — Complete Examples

Complete, working file examples for each pattern. Use these when refactoring code.

---

## Service — full example

`app/features/authentication/services/get_user_key_service.py`

```python
from typing import Annotated
from fastapi import Depends, HTTPException, status
from app.database import DbSessionManagerDep
from app.features.authentication.data import FindByUserIdReaderDep
from app.database import Key


class GetUserKeyService:
    def __init__(
            self,
            db_session_manager: DbSessionManagerDep,
            find_by_user_id_reader: FindByUserIdReaderDep,
    ):
        self.__db_session_manager = db_session_manager
        self.__find_by_user_id_reader = find_by_user_id_reader

    async def handle(self, user_id: str) -> Key:
        async with self.__db_session_manager.session() as db_session:
            key = await self.__find_by_user_id_reader.handle(db_session, user_id)

        if key is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot find key for user with ID {user_id}",
            )

        return key


GetUserKeyServiceDep = Annotated[GetUserKeyService, Depends()]
```

`app/features/authentication/services/__init__.py`

```python
from .get_user_key_service import GetUserKeyService as GetUserKeyService
from .get_user_key_service import GetUserKeyServiceDep as GetUserKeyServiceDep

from .refresh_user_key_service import RefreshUserKeyService as RefreshUserKeyService
from .refresh_user_key_service import RefreshUserKeyServiceDep as RefreshUserKeyServiceDep
```

---

## Reader — full example

`app/features/authentication/data/find_by_user_id_reader.py`

```python
from typing import Annotated
from fastapi import Depends
from sqlmodel import select
from app.database import Key
from sqlmodel.ext.asyncio.session import AsyncSession


class FindByUserIdReader:
    @classmethod
    async def handle(cls, db_session: AsyncSession, user_id: str) -> Key | None:
        statement = select(Key).where(Key.user_id == user_id).limit(1)
        result = await db_session.exec(statement)

        return result.first()


FindByUserIdReaderDep = Annotated[FindByUserIdReader, Depends()]
```

`app/features/authentication/data/__init__.py`

```python
from .find_by_user_id_reader import FindByUserIdReader as FindByUserIdReader
from .find_by_user_id_reader import FindByUserIdReaderDep as FindByUserIdReaderDep

from .update_key_writer import UpdateKeyWriter as UpdateKeyWriter
from .update_key_writer import UpdateKeyWriterDep as UpdateKeyWriterDep
```

---

## Writer — full example

`app/features/authentication/data/update_key_writer.py`

```python
from typing import Annotated
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import Key
from datetime import datetime, timezone


class UpdateKeyWriter:
    @classmethod
    async def handle(cls, db_session: AsyncSession, key: Key) -> Key:
        key.updated_at = datetime.now(timezone.utc)

        db_session.add(key)
        await db_session.commit()
        await db_session.refresh(key)

        return key


UpdateKeyWriterDep = Annotated[UpdateKeyWriter, Depends()]
```

Writer that relies on an outer transaction (no commit — caller owns the transaction):

```python
class CreateItemWriter:
    @classmethod
    async def handle(cls, db_session: AsyncSession, item: Item) -> Item:
        db_session.add(item)
        await db_session.flush()   # assigns DB-generated fields without committing
        await db_session.refresh(item)
        return item

CreateItemWriterDep = Annotated[CreateItemWriter, Depends()]
```

When using `db_session_manager.transaction()`, the `async with` block commits on exit and rolls back on exception — the writer should only `flush()`.

---

## Guard — full example

`app/features/authentication/guards/spb_authenticated_guard.py`

```python
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.features.authentication.entities import User, UserFactory
from app.ports.supabase import SupabasePortDep

security = HTTPBearer()


async def _get_user_from_spb_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    supabase: SupabasePortDep,
) -> User:
    token = credentials.credentials

    try:
        spb_response = supabase.auth().get_user(token)
        if spb_response is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return UserFactory.user_from_spb_auth(spb_response.user)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


AuthenticatedGuardDep = Depends(_get_user_from_spb_token)
CurrentAuthenticatedUserDep = Annotated[User, Depends(_get_user_from_spb_token)]
```

`app/features/authentication/guards/__init__.py`

```python
from .spb_authenticated_guard import AuthenticatedGuardDep as AuthenticatedGuardDep
from .spb_authenticated_guard import CurrentAuthenticatedUserDep as CurrentAuthenticatedUserDep

from .jwt_secret_guard import SecretJwtGuardDep as SecretJwtGuardDep
```

---

## Router — full example

`app/http/item_router.py`

```python
from fastapi import APIRouter
from app.features.authentication.guards import (
    CurrentAuthenticatedUserDep,
    AuthenticatedGuardDep,
    SecretJwtGuardDep,
)
from app.features.item.entities import Item
from app.features.item.requests import ItemRequest, ItemDeleteMultipleRequest
from app.features.item.services import (
    GenerateUploadUrlServiceDep,
    ListItemInCollectionServiceDep,
    GenerateViewUrlServiceDep,
    DeleteMultipleItemsServiceDep,
)

router = APIRouter(
    prefix="/items",
    tags=["item"],
    dependencies=[AuthenticatedGuardDep, SecretJwtGuardDep],
)


@router.post("/upload-url")
async def generate_upload_url(
    request: ItemRequest,
    current_user: CurrentAuthenticatedUserDep,
    generate_upload_url_service: GenerateUploadUrlServiceDep,
):
    signed_url = await generate_upload_url_service.handle(
        current_user, request.item, request.collection
    )
    return {
        "url": signed_url["signedUrl"],
        "path": signed_url["path"],
        "token": signed_url["token"],
    }


@router.get("")
def list_items(
    current_user: CurrentAuthenticatedUserDep,
    list_service: ListItemInCollectionServiceDep,
) -> list[Item]:
    return list_service.handle(current_user)
```

Registering in the app factory:

```python
# app/__init__.py
from app.http.item_router import router as item_router
from app.http.key_router import router as key_router

router_registry = [item_router, key_router]

app = bootstrap_application(router_registry, lifespan_handler)
```

---

## Entity — Pydantic domain model

`app/features/authentication/entities/user_entity.py`

```python
from pydantic import BaseModel


class User(BaseModel):
    id: str
    email: str
```

`app/features/authentication/entities/user_factory.py`

```python
from .user_entity import User


class UserFactory:
    @staticmethod
    def user_from_spb_auth(spb_user) -> User:
        return User(id=spb_user.id, email=spb_user.email)
```

`app/features/authentication/entities/__init__.py`

```python
from .user_entity import User as User
from .user_factory import UserFactory as UserFactory
```

---

## Entity — SQLModel DB table model

DB table models live in `app/database/models.py` (not in features):

```python
from uuid import uuid4
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime, Index
from .metadata import model_common_metadata


class Collection(SQLModel, table=True):
    metadata = model_common_metadata

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(sa_column=Column(nullable=False))
    name: str = Field(sa_column=Column(nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    __table_args__ = (Index("ix_collection_user_id", "user_id"),)
```

Key rules:
- `metadata = model_common_metadata` — required for Alembic to detect the model
- UUID primary keys via `default_factory`
- Timezone-aware datetimes: `Column(DateTime(timezone=True))`
- Add explicit indexes for query-critical columns

---

## Request DTO

```python
# app/features/item/requests/item_request.py
from pydantic import BaseModel


class ItemRequest(BaseModel):
    item: str
    collection: str


# app/features/item/requests/__init__.py
from .item_request import ItemRequest as ItemRequest
```

---

## AppException

```python
from app.core.error import AppException
from fastapi import status

# Domain error with a semantic code
raise AppException(
    status_code=status.HTTP_404_NOT_FOUND,
    code="item_not_found",
    message=f"Item with ID {item_id} not found",
)

# Conflict
raise AppException(
    status_code=status.HTTP_409_CONFLICT,
    code="collection_already_exists",
    message=f"Collection '{name}' already exists for user {user_id}",
)
```

Response shape (applied automatically by middleware):
```json
{
  "error": {
    "code": "item_not_found",
    "message": "Item with ID abc not found",
    "path": "/api/items/abc"
  }
}
```

---

## DB Session Manager usage

```python
# Read-only: session() — no transaction, auto-closed
async with self.__db_session_manager.session() as db_session:
    result = await self.__reader.handle(db_session, user_id)

# Write: transaction() — begins and commits automatically; rolls back on exception
async with self.__db_session_manager.transaction() as db_session:
    item = await self.__writer.handle(db_session, new_item)
```

`DbSessionManagerDep` is imported from `app.database` and injected via `Depends()` in the service constructor.
