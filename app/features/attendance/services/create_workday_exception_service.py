from typing import Annotated

from fastapi import Depends

from app.database import DbSessionManagerDep, WorkdayExceptionRecord
from app.features.attendance.data import SaveWorkdayExceptionWriterDep
from app.features.attendance.entities import WorkdayException
from app.features.attendance.requests import CreateWorkdayExceptionRequest
from app.features.attendance.services import (
    require_mutable_workday_exception,
    workday_exception_today,
)
from app.features.authorization.entities import SpecialPermission
from app.features.authorization.services import RequireSpecialPermissionServiceDep


class CreateWorkdayExceptionService:
    def __init__(
        self,
        db_session_manager: DbSessionManagerDep,
        authorize: RequireSpecialPermissionServiceDep,
        save: SaveWorkdayExceptionWriterDep,
    ) -> None:
        self.__db_session_manager = db_session_manager
        self.__authorize = authorize
        self.__save = save

    async def handle(
        self, user_id: str, request: CreateWorkdayExceptionRequest
    ) -> WorkdayException:
        async with self.__db_session_manager.transaction() as session:
            await self.__authorize.handle(
                session, user_id, SpecialPermission.MANAGE_WORKDAY_EXCEPTIONS
            )
            today = workday_exception_today()
            require_mutable_workday_exception(request.date, today)
            record = WorkdayExceptionRecord(
                type=int(request.type),
                date=request.date,
                time=int(request.time),
                title=request.title,
            )
            return await self.__save.handle(session, record)


CreateWorkdayExceptionServiceDep = Annotated[CreateWorkdayExceptionService, Depends()]
