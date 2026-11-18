from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import WorkdayExceptionRecord


class DeleteWorkdayExceptionWriter:
    async def handle(
        self, session: AsyncSession, record: WorkdayExceptionRecord
    ) -> None:
        await session.delete(record)
        await session.flush()


DeleteWorkdayExceptionWriterDep = Annotated[DeleteWorkdayExceptionWriter, Depends()]
