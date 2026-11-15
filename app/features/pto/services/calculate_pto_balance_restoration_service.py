from dataclasses import replace
from typing import Annotated

from fastapi import Depends

from app.features.pto.entities import PtoBank


class CalculatePtoBalanceRestorationService:
    def handle(self, bank: PtoBank, restoration_minutes: int) -> tuple[PtoBank, int]:
        remaining = restoration_minutes
        annual = min(
            remaining, max(bank.original_annual_balance - bank.annual_balance, 0)
        )
        remaining -= annual
        seniority = min(
            remaining,
            max(bank.original_seniority_balance - bank.seniority_balance, 0),
        )
        remaining -= seniority
        extended = min(
            remaining,
            max(bank.original_extended_balance - bank.extended_balance, 0),
        )
        remaining -= extended
        restored_bank = replace(
            bank,
            extended_balance=bank.extended_balance + extended,
            seniority_balance=bank.seniority_balance + seniority,
            annual_balance=bank.annual_balance + annual,
        )
        return restored_bank, remaining


CalculatePtoBalanceRestorationServiceDep = Annotated[
    CalculatePtoBalanceRestorationService, Depends()
]
