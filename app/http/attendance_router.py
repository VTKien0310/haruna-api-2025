from fastapi import APIRouter, status

from app.core import error_response
from app.features.attendance.entities import CheckInEntry
from app.features.attendance.requests import CreateCheckInRequest
from app.features.attendance.services import CreateCheckInServiceDep
from app.features.authentication.guards import (
    AuthenticatedGuardDep,
    CurrentAuthenticatedUserDep,
)

router = APIRouter(
    prefix="/attendance", tags=["attendance"], dependencies=[AuthenticatedGuardDep]
)


@router.post(
    "/check-ins",
    summary="POST /api/attendance/check-ins",
    description=(
        "Record one arrival for the caller and link it to the caller's PTO affect entries.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Body: date is the calendar date of the arrival and time is the local clock time "
        "(HH:MM or HH:MM:SS). Seconds and microseconds are dropped and the time is stored as "
        "HH:MM:00 in the company's local clock. Any calendar date and any clock time are stored.\n\n"
        "Responses:\n"
        "- 200: the stored check-in (id, date, time)\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 409: check_in_already_exists when this caller already has an arrival on that date\n"
        "- 422: validation_error when date or time is missing or unparseable\n"
    ),
    responses={
        status.HTTP_409_CONFLICT: error_response(
            "This caller already has an arrival on that date (check_in_already_exists).",
            "check_in_already_exists",
        ),
    },
)
async def create_check_in(
    request: CreateCheckInRequest,
    user: CurrentAuthenticatedUserDep,
    create_check_in_service: CreateCheckInServiceDep,
) -> CheckInEntry:
    return await create_check_in_service.handle(user.id, request.date, request.time)
