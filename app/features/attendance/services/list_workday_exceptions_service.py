from typing import Annotated

from fastapi import Depends

from app.database import DbSessionManagerDep
from app.features.attendance.data import ListWorkdayExceptionsReaderDep
from app.features.attendance.entities import WorkdayException
from app.features.authorization.entities import SpecialPermission
from app.features.authorization.services import RequireSpecialPermissionServiceDep


class ListWorkdayExceptionsService:
    def __init__(
        self,
        db_session_manager: DbSessionManagerDep,
        authorize: RequireSpecialPermissionServiceDep,
        reader: ListWorkdayExceptionsReaderDep,
    ) -> None:
        self.__db_session_manager = db_session_manager
        self.__authorize = authorize
        self.__reader = reader

    async def handle(self, user_id: str) -> list[WorkdayException]:
        async with self.__db_session_manager.session() as session:
            await self.__authorize.handle(
                session, user_id, SpecialPermission.MANAGE_WORKDAY_EXCEPTIONS
            )
            return await self.__reader.handle(session)


ListWorkdayExceptionsServiceDep = Annotated[ListWorkdayExceptionsService, Depends()]
