from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoAffectEntryRecord, RemoteWorkEntryRecord
from app.features.attendance.entities import RemoteWorkEntry
from app.features.pto.data import LockPtoOwnerWriter
from app.features.pto.entities import PtoAffectEntry, PtoAffectEntryType


class FindOwnedRemoteWorkEntryReader:
    async def handle(
        self, db_session: AsyncSession, owner_id: str, entry_id: UUID
    ) -> tuple[RemoteWorkEntry, PtoAffectEntry] | None:
        await LockPtoOwnerWriter().handle(db_session, owner_id)
        result = await db_session.exec(
            select(RemoteWorkEntryRecord, PtoAffectEntryRecord)
            .join(
                PtoAffectEntryRecord,
                PtoAffectEntryRecord.entry_id == RemoteWorkEntryRecord.id,
            )
            .where(
                RemoteWorkEntryRecord.id == entry_id,
                PtoAffectEntryRecord.owner_id == UUID(owner_id),
                PtoAffectEntryRecord.entry_type == PtoAffectEntryType.REMOTE_WORK.value,
            )
            .with_for_update()
        )
        row = result.first()
        if row is None:
            return None
        return RemoteWorkEntry.from_db_record(row[0]), PtoAffectEntry.from_db_record(
            row[1]
        )


FindOwnedRemoteWorkEntryReaderDep = Annotated[FindOwnedRemoteWorkEntryReader, Depends()]
