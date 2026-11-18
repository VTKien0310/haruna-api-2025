from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import MissCheckInEntryRecord, PtoAffectEntryRecord
from app.features.attendance.entities import MissCheckInEntry
from app.features.pto.entities import PtoAffectEntryType


class FindMissCheckInEntriesByOwnerAndDateRangeReader:
    async def handle(
        self,
        session: AsyncSession,
        owner_id: str,
        start_date: date,
        end_date: date,
    ) -> list[MissCheckInEntry]:
        result = await session.exec(
            select(MissCheckInEntryRecord)
            .join(
                PtoAffectEntryRecord,
                PtoAffectEntryRecord.entry_id == MissCheckInEntryRecord.id,
            )
            .where(
                PtoAffectEntryRecord.owner_id == UUID(owner_id),
                PtoAffectEntryRecord.entry_type
                == PtoAffectEntryType.MISS_CHECK_IN.value,
                MissCheckInEntryRecord.date >= start_date,
                MissCheckInEntryRecord.date <= end_date,
            )
        )
        return [MissCheckInEntry.from_db_record(record) for record in result.all()]


FindMissCheckInEntriesByOwnerAndDateRangeReaderDep = Annotated[
    FindMissCheckInEntriesByOwnerAndDateRangeReader, Depends()
]
