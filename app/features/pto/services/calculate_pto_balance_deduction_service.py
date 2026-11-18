from dataclasses import replace
from typing import Annotated

from fastapi import Depends

from app.features.pto.entities import PtoBank


class CalculatePtoBalanceDeductionService:
    def handle(self, bank: PtoBank, deduction_minutes: int) -> tuple[PtoBank, int]:
        remaining = deduction_minutes

        extended_balance = max(bank.extended_balance - remaining, 0)
        remaining -= bank.extended_balance - extended_balance

        seniority_balance = max(bank.seniority_balance - remaining, 0)
        remaining -= bank.seniority_balance - seniority_balance

        annual_balance = max(bank.annual_balance - remaining, 0)
        remaining -= bank.annual_balance - annual_balance

        deducted_bank = replace(
            bank,
            extended_balance=extended_balance,
            seniority_balance=seniority_balance,
            annual_balance=annual_balance,
        )
        return deducted_bank, remaining


CalculatePtoBalanceDeductionServiceDep = Annotated[
    CalculatePtoBalanceDeductionService, Depends()
]
