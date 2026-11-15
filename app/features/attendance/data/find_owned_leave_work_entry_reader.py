from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import LeaveWorkEntryRecord, PtoAffectEntryRecord
from app.features.attendance.entities import LeaveWorkEntry
from app.features.pto.data import LockPtoOwnerWriter
from app.features.pto.entities import PtoAffectEntry, PtoAffectEntryType


class FindOwnedLeaveWorkEntryReader:
    async def handle(
        self, db_session: AsyncSession, owner_id: str, entry_id: UUID
    ) -> tuple[LeaveWorkEntry, PtoAffectEntry] | None:
        await LockPtoOwnerWriter().handle(db_session, owner_id)
        result = await db_session.exec(
            select(LeaveWorkEntryRecord, PtoAffectEntryRecord)
            .join(
                PtoAffectEntryRecord,
                PtoAffectEntryRecord.entry_id == LeaveWorkEntryRecord.id,
            )
            .where(
                LeaveWorkEntryRecord.id == entry_id,
                PtoAffectEntryRecord.owner_id == UUID(owner_id),
                PtoAffectEntryRecord.entry_type == PtoAffectEntryType.LEAVE_WORK.value,
            )
            .with_for_update()
        )
        row = result.first()
        if row is None:
            return None
        return LeaveWorkEntry.from_db_record(row[0]), PtoAffectEntry.from_db_record(
            row[1]
        )


FindOwnedLeaveWorkEntryReaderDep = Annotated[FindOwnedLeaveWorkEntryReader, Depends()]
