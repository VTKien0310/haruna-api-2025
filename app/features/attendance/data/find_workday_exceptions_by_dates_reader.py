from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import WorkdayExceptionRecord
from app.features.attendance.entities import WorkdayException


class FindWorkdayExceptionsByDatesReader:
    async def handle(
        self, session: AsyncSession, dates: list[date]
    ) -> list[WorkdayException]:
        result = await session.exec(
            select(WorkdayExceptionRecord).where(WorkdayExceptionRecord.date.in_(dates))
        )
        return [WorkdayException.from_db_record(record) for record in result.all()]


FindWorkdayExceptionsByDatesReaderDep = Annotated[
    FindWorkdayExceptionsByDatesReader, Depends()
]
