from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoTransactionRecord
from app.features.pto.entities import PtoTransaction


class FindPtoTransactionsByEntryReader:
    async def handle(
        self, db_session: AsyncSession, entry_id: str
    ) -> list[PtoTransaction]:
        result = await db_session.exec(
            select(PtoTransactionRecord).where(
                PtoTransactionRecord.entry_id == UUID(entry_id)
            )
        )
        return [PtoTransaction.from_db_record(row) for row in result.all()]


FindPtoTransactionsByEntryReaderDep = Annotated[
    FindPtoTransactionsByEntryReader, Depends()
]
