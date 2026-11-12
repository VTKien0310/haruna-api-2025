from fastapi import APIRouter, status

from app.core import error_response
from app.features.attendance.entities import (
    CheckInEntry,
    LeaveWorkEntry,
    RemoteWorkEntry,
    TimeOffEntry,
    WorkTimeEntry,
)
from app.features.attendance.requests import (
    CreateCheckInRequest,
    CreateLeaveWorkRequest,
    CreateRemoteWorkRequest,
    CreateTimeOffRequest,
    CreateWorkTimeRequest,
)
from app.features.attendance.services import (
    CreateCheckInServiceDep,
    CreateLeaveWorkServiceDep,
    CreateRemoteWorkServiceDep,
    CreateTimeOffServiceDep,
    CreateWorkTimeServiceDep,
)
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
        "HH:MM:00 in the company's local clock. Any calendar date and any clock time are stored. "
        "no_deduction is optional: 0 applies the normal PTO deduction rule and 1 marks an "
        "exception that skips deduction; it defaults to 0. note is optional and is stored "
        "on the linked PTO affect entry; an omitted or null note is stored as an empty "
        "string.\n\n"
        "Responses:\n"
        "- 200: the stored check-in (id, date, time)\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 409: check_in_already_exists when this caller already has an arrival on that date\n"
        "- 422: validation_error when date or time is missing or unparseable, no_deduction "
        "is not 0 or 1, or note is not a string\n"
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
    return await create_check_in_service.handle(
        user.id, request.date, request.time, request.no_deduction, request.note
    )


@router.post(
    "/time-offs",
    summary="POST /api/attendance/time-offs",
    description=(
        "Record one or more full days off, or one morning or afternoon off, for the caller.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Body: start_date is required; end_date is optional, inclusive, and defaults to "
        "start_date. A multi-date range must use type 0 (full day); type 1 is morning "
        "and type 2 is afternoon. Ranges include weekends and are limited to 366 dates. "
        "no_deduction is optional: 0 applies the normal PTO deduction rule and 1 marks an "
        "exception that skips deduction; it defaults to 0 and applies to every date in the "
        "range. note is optional and is stored on every linked PTO affect entry; an "
        "omitted or null note is stored as an empty string.\n\n"
        "Responses:\n"
        "- 200: the created time-off entries, one per date\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 409: time_off_already_exists when this caller already has a conflicting "
        "time-off entry on a date in the range\n"
        "- 422: validation_error when dates are invalid, the range exceeds 366 dates, "
        "a multi-date range is not full day, type is not 0, 1, or 2, no_deduction is "
        "not 0 or 1, or note is not a string\n"
    ),
    responses={
        status.HTTP_409_CONFLICT: error_response(
            "This caller already has a conflicting time-off entry on the date "
            "(time_off_already_exists).",
            "time_off_already_exists",
        ),
    },
)
async def create_time_off(
    request: CreateTimeOffRequest,
    user: CurrentAuthenticatedUserDep,
    create_time_off_service: CreateTimeOffServiceDep,
) -> list[TimeOffEntry]:
    return await create_time_off_service.handle(
        user.id,
        request.start_date,
        request.end_date,
        request.type,
        request.no_deduction,
        request.note,
    )


@router.post(
    "/remote-works",
    summary="POST /api/attendance/remote-works",
    description=(
        "Record remote work for the caller for a full day, morning, or afternoon.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Body: date is the calendar date and type is 0 for full day, 1 for morning, or "
        "2 for afternoon. Full-day remote work conflicts with either shift; morning "
        "and afternoon remote work can coexist. Records of another kind on the same "
        "date do not conflict. Its PTO affect entry always uses no_deduction 1 because "
        "remote work never deducts PTO. note is optional and is stored on that PTO affect "
        "entry; an omitted or null note is stored as an empty string.\n\n"
        "Responses:\n"
        "- 200: the stored remote-work entry (id, date, type)\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 409: remote_work_already_exists when this caller already has a conflicting "
        "remote-work entry on that date\n"
        "- 422: validation_error when date is invalid, type is not 0, 1, or 2, or note "
        "is not a string\n"
    ),
    responses={
        status.HTTP_409_CONFLICT: error_response(
            "This caller already has a conflicting remote-work entry on that date "
            "(remote_work_already_exists).",
            "remote_work_already_exists",
        ),
    },
)
async def create_remote_work(
    request: CreateRemoteWorkRequest,
    user: CurrentAuthenticatedUserDep,
    create_remote_work_service: CreateRemoteWorkServiceDep,
) -> RemoteWorkEntry:
    return await create_remote_work_service.handle(
        user.id, request.date, request.type, request.note
    )


@router.post(
    "/work-times",
    summary="POST /api/attendance/work-times",
    description=(
        "Record late coverage or an early departure for one shift of the caller's day.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Body: date is the calendar date; time is 0 for morning or 1 for afternoon; "
        "type is 0 for late coverage or 1 for leaving work early; duration is the "
        "drift in minutes from 1 through 240. A type can be recorded once per shift. "
        "Late and early entries can coexist only when their combined duration is less "
        "than 240 minutes. Different shifts do not conflict. no_deduction is optional: "
        "0 applies the normal PTO deduction rule and 1 marks an exception that skips "
        "deduction; it defaults to 0. note is optional and is stored on the linked PTO "
        "affect entry; an omitted or null note is stored as an empty string.\n\n"
        "Responses:\n"
        "- 200: the stored work-time entry (id, date, time, type, duration)\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 409: work_time_already_exists for the same type in the same shift, or "
        "work_time_overlaps when durations cover the whole shift\n"
        "- 422: validation_error when date is invalid, time is not 0 or 1, type is not "
        "0 or 1, duration is outside 1–240, no_deduction is not 0 or 1, or note is not "
        "a string\n"
    ),
    responses={
        status.HTTP_409_CONFLICT: error_response(
            "The caller already has this work-time type in the shift "
            "(work_time_already_exists), or the combined duration covers the whole "
            "shift (work_time_overlaps).",
            "work_time_already_exists",
            "work_time_overlaps",
        ),
    },
)
async def create_work_time(
    request: CreateWorkTimeRequest,
    user: CurrentAuthenticatedUserDep,
    create_work_time_service: CreateWorkTimeServiceDep,
) -> WorkTimeEntry:
    return await create_work_time_service.handle(
        user.id,
        request.date,
        request.time,
        request.type,
        request.duration,
        request.no_deduction,
        request.note,
    )


@router.post(
    "/leave-works",
    summary="POST /api/attendance/leave-works",
    description=(
        "Record a temporary absence interval for the caller on one date.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Body: date is the calendar date; start and end are local clock times. Seconds "
        "and microseconds are dropped, and start must be before end after dropping "
        "seconds. Intervals that only touch are allowed; overlapping intervals are not. "
        "no_deduction is optional: 0 applies the normal PTO deduction rule and 1 marks an "
        "exception that skips deduction; it defaults to 0. note is optional and is stored "
        "on the linked PTO affect entry; an omitted or null note is stored as an empty "
        "string.\n\n"
        "Responses:\n"
        "- 200: the stored leave-work entry (id, date, start, end)\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 409: leave_work_overlaps when this caller already has an overlapping "
        "leave-work interval on that date\n"
        "- 422: validation_error when date or times are invalid, start is not before end, "
        "no_deduction is not 0 or 1, or note is not a string\n"
    ),
    responses={
        status.HTTP_409_CONFLICT: error_response(
            "This caller already has an overlapping leave-work interval on that date "
            "(leave_work_overlaps).",
            "leave_work_overlaps",
        ),
    },
)
async def create_leave_work(
    request: CreateLeaveWorkRequest,
    user: CurrentAuthenticatedUserDep,
    create_leave_work_service: CreateLeaveWorkServiceDep,
) -> LeaveWorkEntry:
    return await create_leave_work_service.handle(
        user.id,
        request.date,
        request.start,
        request.end,
        request.no_deduction,
        request.note,
    )
