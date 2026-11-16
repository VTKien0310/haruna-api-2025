from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.features.authorization.data import FindUserSpecialPermissionsByUserIdReaderDep
from app.features.authorization.entities import SpecialPermission


class RequireSpecialPermissionService:
    def __init__(
        self, find_permissions: FindUserSpecialPermissionsByUserIdReaderDep
    ) -> None:
        self.__find_permissions = find_permissions

    async def handle(
        self, session: AsyncSession, user_id: str, permission: SpecialPermission
    ) -> None:
        permissions = await self.__find_permissions.handle(session, user_id)
        if not any(item.permission == permission for item in permissions):
            raise HTTPException(
                status_code=403, detail="Required permission is missing"
            )


RequireSpecialPermissionServiceDep = Annotated[
    RequireSpecialPermissionService, Depends()
]
