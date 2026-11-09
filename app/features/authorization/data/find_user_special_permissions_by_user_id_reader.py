from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import UserSpecialPermissionRecord
from app.features.authorization.entities import UserSpecialPermission


class FindUserSpecialPermissionsByUserIdReader:
    async def handle(
        self, db_session: AsyncSession, user_id: str
    ) -> list[UserSpecialPermission]:
        statement = select(UserSpecialPermissionRecord).where(
            UserSpecialPermissionRecord.user_id == UUID(user_id)
        )
        result = await db_session.exec(statement)
        records = result.all()

        return [UserSpecialPermission.from_db_record(record) for record in records]


FindUserSpecialPermissionsByUserIdReaderDep = Annotated[
    FindUserSpecialPermissionsByUserIdReader, Depends()
]
