from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import LeaveWorkEntryRecord
from app.features.attendance.entities import LeaveWorkEntry


class FindLeaveWorkEntriesByIdsAndDateReader:
    async def handle(
        self,
        db_session: AsyncSession,
        entry_ids: list[str],
        day: date,
    ) -> list[LeaveWorkEntry]:
        if not entry_ids:
            return []

        statement = select(LeaveWorkEntryRecord).where(
            LeaveWorkEntryRecord.id.in_([UUID(entry_id) for entry_id in entry_ids]),
            LeaveWorkEntryRecord.date == day,
        )
        result = await db_session.exec(statement)

        return [LeaveWorkEntry.from_db_record(record) for record in result.all()]


FindLeaveWorkEntriesByIdsAndDateReaderDep = Annotated[
    FindLeaveWorkEntriesByIdsAndDateReader, Depends()
]
