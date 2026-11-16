from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.data import (
    DeleteWorkdayExceptionWriterDep,
    FindWorkdayExceptionReaderDep,
)
from app.features.attendance.services import (
    require_mutable_workday_exception,
    workday_exception_today,
)
from app.features.authorization.entities import SpecialPermission
from app.features.authorization.services import RequireSpecialPermissionServiceDep


class DeleteWorkdayExceptionService:
    def __init__(
        self,
        db_session_manager: DbSessionManagerDep,
        authorize: RequireSpecialPermissionServiceDep,
        reader: FindWorkdayExceptionReaderDep,
        delete: DeleteWorkdayExceptionWriterDep,
    ) -> None:
        self.__db_session_manager = db_session_manager
        self.__authorize = authorize
        self.__reader = reader
        self.__delete = delete

    async def handle(self, user_id: str, exception_id: UUID) -> None:
        async with self.__db_session_manager.transaction() as session:
            await self.__authorize.handle(
                session, user_id, SpecialPermission.MANAGE_WORKDAY_EXCEPTIONS
            )
            record = await self.__reader.handle(session, exception_id, for_update=True)
            if record is None:
                raise AppException(
                    status_code=404,
                    code="workday_exception_not_found",
                    message="Workday exception not found",
                )
            require_mutable_workday_exception(record.date, workday_exception_today())
            await self.__delete.handle(session, record)


DeleteWorkdayExceptionServiceDep = Annotated[DeleteWorkdayExceptionService, Depends()]
