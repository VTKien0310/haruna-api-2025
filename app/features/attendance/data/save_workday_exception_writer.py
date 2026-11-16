from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import WorkdayExceptionRecord
from app.features.attendance.entities import WorkdayException


class SaveWorkdayExceptionWriter:
    async def handle(
        self, session: AsyncSession, record: WorkdayExceptionRecord
    ) -> WorkdayException:
        session.add(record)
        await session.flush()
        return WorkdayException.from_db_record(record)


SaveWorkdayExceptionWriterDep = Annotated[SaveWorkdayExceptionWriter, Depends()]
