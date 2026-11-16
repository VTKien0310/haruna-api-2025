from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.data import (
    FindWorkdayExceptionReaderDep,
    SaveWorkdayExceptionWriterDep,
)
from app.features.attendance.entities import WorkdayException
from app.features.attendance.requests import UpdateWorkdayExceptionRequest
from app.features.attendance.services import (
    require_mutable_workday_exception,
    workday_exception_today,
)
from app.features.authorization.entities import SpecialPermission
from app.features.authorization.services import RequireSpecialPermissionServiceDep


class UpdateWorkdayExceptionService:
    def __init__(
        self,
        db_session_manager: DbSessionManagerDep,
        authorize: RequireSpecialPermissionServiceDep,
        reader: FindWorkdayExceptionReaderDep,
        save: SaveWorkdayExceptionWriterDep,
    ) -> None:
        self.__db_session_manager = db_session_manager
        self.__authorize = authorize
        self.__reader = reader
        self.__save = save

    async def handle(
        self, user_id: str, exception_id: UUID, request: UpdateWorkdayExceptionRequest
    ) -> WorkdayException:
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
            today = workday_exception_today()
            require_mutable_workday_exception(record.date, today)
            require_mutable_workday_exception(
                request.date if request.date is not None else record.date, today
            )
            if request.type is not None:
                record.type = int(request.type)
            if request.date is not None:
                record.date = request.date
            if request.time is not None:
                record.time = int(request.time)
            if request.title is not None:
                record.title = request.title
            record.updated_at = datetime.now(timezone.utc)
            return await self.__save.handle(session, record)


UpdateWorkdayExceptionServiceDep = Annotated[UpdateWorkdayExceptionService, Depends()]
