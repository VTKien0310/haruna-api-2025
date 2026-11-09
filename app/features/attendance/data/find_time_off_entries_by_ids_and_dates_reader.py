from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import TimeOffEntryRecord
from app.features.attendance.entities import TimeOffEntry


class FindTimeOffEntriesByIdsAndDatesReader:
    async def handle(
        self,
        db_session: AsyncSession,
        entry_ids: list[str],
        days: list[date],
    ) -> list[TimeOffEntry]:
        if not entry_ids or not days:
            return []

        statement = select(TimeOffEntryRecord).where(
            TimeOffEntryRecord.id.in_([UUID(entry_id) for entry_id in entry_ids]),
            TimeOffEntryRecord.date.in_(days),
        )
        result = await db_session.exec(statement)

        return [TimeOffEntry.from_db_record(record) for record in result.all()]


FindTimeOffEntriesByIdsAndDatesReaderDep = Annotated[
    FindTimeOffEntriesByIdsAndDatesReader, Depends()
]
