from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, MetaData, UniqueConstraint
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
    year: int
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
