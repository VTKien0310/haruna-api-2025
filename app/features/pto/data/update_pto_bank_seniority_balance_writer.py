from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoBankRecord


class UpdatePtoBankSeniorityBalanceWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        bank_id: str,
        seniority_balance: int,
    ) -> None:
        record = await db_session.get(PtoBankRecord, UUID(bank_id))
        if record is None:
            return

        record.seniority_balance = seniority_balance
        record.updated_at = datetime.now(timezone.utc)
        await db_session.flush()


UpdatePtoBankSeniorityBalanceWriterDep = Annotated[
    UpdatePtoBankSeniorityBalanceWriter, Depends()
]
