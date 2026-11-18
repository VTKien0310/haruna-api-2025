from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import WorkdayExceptionRecord


class FindWorkdayExceptionReader:
    async def handle(
        self, session: AsyncSession, exception_id: UUID, *, for_update: bool = False
    ) -> WorkdayExceptionRecord | None:
        statement = select(WorkdayExceptionRecord).where(
            WorkdayExceptionRecord.id == exception_id
        )
        if for_update:
            statement = statement.with_for_update()
        return (await session.exec(statement)).first()


FindWorkdayExceptionReaderDep = Annotated[FindWorkdayExceptionReader, Depends()]
