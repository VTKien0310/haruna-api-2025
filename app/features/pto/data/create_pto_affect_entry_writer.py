from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoAffectEntryRecord
from app.features.pto.entities import PtoAffectEntry, PtoAffectEntryType


class CreatePtoAffectEntryWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        owner_id: str,
        entry_id: str,
        entry_type: PtoAffectEntryType,
    ) -> PtoAffectEntry:
        record = PtoAffectEntryRecord(
            owner_id=UUID(owner_id),
            entry_id=UUID(entry_id),
            entry_type=entry_type.value,
        )
        db_session.add(record)
        await db_session.flush()

        return PtoAffectEntry.from_db_record(record)


CreatePtoAffectEntryWriterDep = Annotated[CreatePtoAffectEntryWriter, Depends()]
