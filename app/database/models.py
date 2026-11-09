from datetime import date, datetime, time as dt_time, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Identity,
    Integer,
    MetaData,
    SmallInteger,
    Time,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel

from app.core.config import settings

model_common_metadata = MetaData(schema=settings.DB_SCHEMA or None)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProfileRecord(SQLModel, table=True):
    metadata = model_common_metadata
    __tablename__ = "profiles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, unique=True)
    name: str | None = Field(default=None)
    birth_date: date
    work_start_date: date
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class PtoBankRecord(SQLModel, table=True):
    metadata = model_common_metadata
    __tablename__ = "pto_banks"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "year",
            name="pto_banks_owner_id_year_key",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID
    annual_balance: int
    extended_balance: int
    seniority_balance: int
    original_annual_balance: int = Field(default=0)
    original_extended_balance: int = Field(default=0)
    original_seniority_balance: int = Field(default=0)
    year: int
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CheckInEntryRecord(SQLModel, table=True):
    metadata = model_common_metadata
    __tablename__ = "check_in_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: date
    time: dt_time = Field(sa_column=Column(Time, nullable=False))


class TimeOffEntryRecord(SQLModel, table=True):
    metadata = model_common_metadata
    __tablename__ = "time_off_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: date
    type: int = Field(sa_column=Column(SmallInteger, nullable=False))


class RemoteWorkEntryRecord(SQLModel, table=True):
    metadata = model_common_metadata
    __tablename__ = "remote_work_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: date
    type: int = Field(sa_column=Column(SmallInteger, nullable=False))


class WorkTimeEntryRecord(SQLModel, table=True):
    metadata = model_common_metadata
    __tablename__ = "work_time_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: date
    type: int = Field(sa_column=Column(SmallInteger, nullable=False))
    duration: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    time: int = Field(sa_column=Column(SmallInteger, nullable=False, default=0))


class LeaveWorkEntryRecord(SQLModel, table=True):
    metadata = model_common_metadata
    __tablename__ = "leave_work_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: date
    start: dt_time = Field(sa_column=Column(Time, nullable=False))
    end: dt_time = Field(sa_column=Column(Time, nullable=False))


class PtoAffectEntryRecord(SQLModel, table=True):
    metadata = model_common_metadata
    __tablename__ = "pto_affect_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID
    entry_id: UUID | None = Field(default=None)
    entry_type: str | None = Field(default=None)
    no_deduction: int = Field(
        default=0,
        sa_column=Column(SmallInteger, nullable=False, server_default="0"),
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class UserSpecialPermissionRecord(SQLModel, table=True):
    metadata = model_common_metadata
    __tablename__ = "user_special_permissions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "permission",
            name="user_special_permissions_user_id_permission_key",
        ),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(Integer, Identity(always=False), primary_key=True),
    )
    user_id: UUID
    permission: int = Field(sa_column=Column(SmallInteger, nullable=False))
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
