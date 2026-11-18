from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoAffectEntryRecord, TimeOffEntryRecord
from app.features.attendance.entities import TimeOffEntry
from app.features.pto.data import LockPtoOwnerWriter
from app.features.pto.entities import PtoAffectEntry, PtoAffectEntryType


class FindOwnedTimeOffEntryReader:
    async def handle(
        self, db_session: AsyncSession, owner_id: str, entry_id: UUID
    ) -> tuple[TimeOffEntry, PtoAffectEntry] | None:
        await LockPtoOwnerWriter().handle(db_session, owner_id)
        result = await db_session.exec(
            select(TimeOffEntryRecord, PtoAffectEntryRecord)
            .join(
                PtoAffectEntryRecord,
                PtoAffectEntryRecord.entry_id == TimeOffEntryRecord.id,
            )
            .where(
                TimeOffEntryRecord.id == entry_id,
                PtoAffectEntryRecord.owner_id == UUID(owner_id),
                PtoAffectEntryRecord.entry_type == PtoAffectEntryType.TIME_OFF.value,
            )
            .with_for_update()
        )
        row = result.first()
        if row is None:
            return None
        return TimeOffEntry.from_db_record(row[0]), PtoAffectEntry.from_db_record(
            row[1]
        )


FindOwnedTimeOffEntryReaderDep = Annotated[FindOwnedTimeOffEntryReader, Depends()]
