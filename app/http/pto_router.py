from typing import Annotated

from fastapi import APIRouter, Path, status

from app.core import error_response
from app.features.authentication.guards import (
    AuthenticatedGuardDep,
    CurrentAuthenticatedUserDep,
)
from app.features.pto.entities import PtoBank
from app.features.pto.services import GetOrCreatePtoBankServiceDep

router = APIRouter(prefix="/pto", tags=["pto"], dependencies=[AuthenticatedGuardDep])


@router.put(
    "/banks/{year}",
    summary="PUT /api/pto/banks/{year}",
    description=(
        "Return the caller's PTO bank for the given year, creating the current-year bank when it is missing.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Path: year is the calendar year of the bank. Balances (annual_balance, extended_balance, "
        "seniority_balance) are stored in minutes. One work day is 480 minutes.\n\n"
        "Responses:\n"
        "- 200: the PTO bank\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 404: pto_bank_not_found when a past year has no bank; profile_not_found when the user has no profile\n"
        "- 422: validation_error when year is not an integer\n"
    ),
    responses={
        status.HTTP_404_NOT_FOUND: error_response(
            "A past year has no bank (pto_bank_not_found), or the user has no profile (profile_not_found).",
            "pto_bank_not_found",
            "profile_not_found",
        ),
    },
)
async def put_pto_bank(
    year: Annotated[
        int,
        Path(description="Calendar year of the PTO bank to view or create"),
    ],
    user: CurrentAuthenticatedUserDep,
    get_or_create_service: GetOrCreatePtoBankServiceDep,
) -> PtoBank:
    return await get_or_create_service.handle(user.id, year)
