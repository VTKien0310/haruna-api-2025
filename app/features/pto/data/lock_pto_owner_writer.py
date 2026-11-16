from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


class LockPtoOwnerWriter:
    async def handle(self, db_session: AsyncSession, owner_id: str) -> None:
        # One transaction lock covers missing banks and attendance conflict checks too.
        if db_session.get_bind().dialect.name == "postgresql":
            await db_session.exec(
                select(
                    func.pg_advisory_xact_lock(
                        func.hashtextextended(str(UUID(owner_id)), 0)
                    )
                )
            )


LockPtoOwnerWriterDep = Annotated[LockPtoOwnerWriter, Depends()]
