from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import ProfileRecord
from app.features.profile.entities import Profile


class FindProfileByUserIdReader:
    async def handle(self, db_session: AsyncSession, user_id: str) -> Profile | None:
        statement = (
            select(ProfileRecord).where(ProfileRecord.user_id == UUID(user_id)).limit(1)
        )
        result = await db_session.exec(statement)
        record = result.first()

        return Profile.from_db_record(record) if record is not None else None


FindProfileByUserIdReaderDep = Annotated[FindProfileByUserIdReader, Depends()]
