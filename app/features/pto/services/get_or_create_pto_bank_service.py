from dataclasses import replace
from datetime import date
from typing import Annotated

from fastapi import Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.profile.data import FindProfileByUserIdReaderDep
from app.features.profile.entities import Profile
from app.features.pto.constants import (
    ANNUAL_DAYS,
    MAX_SENIORITY_DAYS,
    MINUTES_PER_WORK_DAY,
)
from app.features.pto.data import (
    CreatePtoBankWriterDep,
    FindPtoBankByOwnerAndYearReaderDep,
    UpdatePtoBankSeniorityBalanceWriterDep,
)
from app.features.pto.entities import PtoBank


class GetOrCreatePtoBankService:
    def __init__(
        self,
        find_pto_bank_reader: FindPtoBankByOwnerAndYearReaderDep,
        find_profile_reader: FindProfileByUserIdReaderDep,
        create_pto_bank_writer: CreatePtoBankWriterDep,
        update_seniority_balance_writer: UpdatePtoBankSeniorityBalanceWriterDep,
        db_session_manager: DbSessionManagerDep,
    ) -> None:
        self.__find_pto_bank_reader = find_pto_bank_reader
        self.__find_profile_reader = find_profile_reader
        self.__create_pto_bank_writer = create_pto_bank_writer
        self.__update_seniority_balance_writer = update_seniority_balance_writer
        self.__db_session_manager = db_session_manager

    async def handle(self, user_id: str, year: int) -> PtoBank:
        async with self.__db_session_manager.transaction() as db_session:
            current_year = date.today().year
            existing = await self.__find_pto_bank_reader.handle(
                db_session, user_id, year
            )

            if existing is not None:
                if year != current_year:
                    return existing
                return await self.__accrue_seniority_balance(
                    db_session, user_id, existing
                )

            if year != current_year:
                raise AppException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    code="pto_bank_not_found",
                    message=f"PTO bank for year '{year}' not found",
                )

            return await self.__create_current_year_bank(
                db_session, user_id, current_year
            )

    async def __create_current_year_bank(
        self,
        db_session: AsyncSession,
        user_id: str,
        year: int,
    ) -> PtoBank:
        profile = await self.__get_profile(db_session, user_id)
        last_year_bank = await self.__find_pto_bank_reader.handle(
            db_session, user_id, year - 1
        )

        extended_balance = (
            last_year_bank.annual_balance + last_year_bank.seniority_balance
            if last_year_bank is not None
            else 0
        )

        return await self.__create_pto_bank_writer.handle(
            db_session,
            owner_id=user_id,
            year=year,
            annual_balance=ANNUAL_DAYS * MINUTES_PER_WORK_DAY,
            extended_balance=extended_balance,
            seniority_balance=self.__seniority_target(profile, date.today()),
        )

    async def __accrue_seniority_balance(
        self,
        db_session: AsyncSession,
        user_id: str,
        bank: PtoBank,
    ) -> PtoBank:
        profile = await self.__get_profile(db_session, user_id)
        target = self.__seniority_target(profile, date.today())

        if bank.seniority_balance >= target:
            return bank

        await self.__update_seniority_balance_writer.handle(db_session, bank.id, target)
        return replace(bank, seniority_balance=target)

    async def __get_profile(self, db_session: AsyncSession, user_id: str) -> Profile:
        profile = await self.__find_profile_reader.handle(db_session, user_id)
        if profile is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="profile_not_found",
                message=f"Profile for user '{user_id}' not found",
            )
        return profile

    @staticmethod
    def __seniority_target(profile: Profile, today: date) -> int:
        return (
            min(
                GetOrCreatePtoBankService.__full_years(profile.work_start_date, today),
                MAX_SENIORITY_DAYS,
            )
            * MINUTES_PER_WORK_DAY
        )

    @staticmethod
    def __full_years(work_start_date: date, today: date) -> int:
        years = today.year - work_start_date.year
        anniversary_reached = (today.month, today.day) >= (
            work_start_date.month,
            work_start_date.day,
        )
        return years if anniversary_reached else years - 1


GetOrCreatePtoBankServiceDep = Annotated[GetOrCreatePtoBankService, Depends()]
