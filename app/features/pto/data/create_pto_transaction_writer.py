from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoTransactionRecord
from app.features.pto.entities import PtoTransaction, PtoTransactionCause


class CreatePtoTransactionWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        pto_bank_id: str,
        entry_id: str,
        cause: PtoTransactionCause,
        value: int,
        exceed_bank_value: int,
    ) -> PtoTransaction:
        record = PtoTransactionRecord(
            pto_bank_id=UUID(pto_bank_id),
            entry_id=UUID(entry_id),
            cause=cause.value,
            value=value,
            exceed_bank_value=exceed_bank_value,
        )
        db_session.add(record)
        await db_session.flush()

        return PtoTransaction.from_db_record(record)


CreatePtoTransactionWriterDep = Annotated[CreatePtoTransactionWriter, Depends()]
