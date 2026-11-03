from typing import Annotated

from fastapi import APIRouter, Path

from app.features.auth.guards import AuthenticatedGuardDep, CurrentAuthenticatedUserDep
from app.features.pto.entities import PtoBank
from app.features.pto.services import GetOrCreatePtoBankServiceDep

router = APIRouter(prefix="/pto", tags=["pto"], dependencies=[AuthenticatedGuardDep])


@router.put("/banks/{year}")
async def put_pto_bank(
    year: Annotated[int, Path(title="Year of the PTO bank to view or create")],
    user: CurrentAuthenticatedUserDep,
    get_or_create_service: GetOrCreatePtoBankServiceDep,
) -> PtoBank:
    return get_or_create_service.handle(user.id, year)
