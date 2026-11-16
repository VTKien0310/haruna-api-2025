from typing import Annotated

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import WorkdayExceptionRecord
from app.features.attendance.entities import WorkdayException


class ListWorkdayExceptionsReader:
    async def handle(self, session: AsyncSession) -> list[WorkdayException]:
        result = await session.exec(
            select(WorkdayExceptionRecord).order_by(
                WorkdayExceptionRecord.date, WorkdayExceptionRecord.id
            )
        )
        return [WorkdayException.from_db_record(record) for record in result.all()]


ListWorkdayExceptionsReaderDep = Annotated[ListWorkdayExceptionsReader, Depends()]
