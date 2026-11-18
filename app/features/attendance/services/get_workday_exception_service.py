from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.data import FindWorkdayExceptionReaderDep
from app.features.attendance.entities import WorkdayException
from app.features.authorization.entities import SpecialPermission
from app.features.authorization.services import RequireSpecialPermissionServiceDep


class GetWorkdayExceptionService:
    def __init__(
        self,
        db_session_manager: DbSessionManagerDep,
        authorize: RequireSpecialPermissionServiceDep,
        reader: FindWorkdayExceptionReaderDep,
    ) -> None:
        self.__db_session_manager = db_session_manager
        self.__authorize = authorize
        self.__reader = reader

    async def handle(self, user_id: str, exception_id: UUID) -> WorkdayException:
        async with self.__db_session_manager.session() as session:
            await self.__authorize.handle(
                session, user_id, SpecialPermission.MANAGE_WORKDAY_EXCEPTIONS
            )
            record = await self.__reader.handle(session, exception_id)
            if record is None:
                raise AppException(
                    status_code=404,
                    code="workday_exception_not_found",
                    message="Workday exception not found",
                )
            return WorkdayException.from_db_record(record)


GetWorkdayExceptionServiceDep = Annotated[GetWorkdayExceptionService, Depends()]
