from datetime import date
from uuid import UUID

from app.database import ProfileRecord, PtoBankRecord

TEST_USER_UUID = UUID("11111111-1111-4111-8111-111111111111")
TEST_USER_ID = str(TEST_USER_UUID)
TEST_PROFILE_ID = UUID("22222222-2222-4222-8222-222222222222")
TEST_PTO_BANK_ID = UUID("33333333-3333-4333-8333-333333333333")


def make_profile_record(**overrides: object) -> ProfileRecord:
    values: dict[str, object] = {
        "id": TEST_PROFILE_ID,
        "user_id": TEST_USER_UUID,
        "name": "Haruna",
        "birth_date": date(2000, 1, 1),
        "work_start_date": date(2024, 4, 1),
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    values.update(overrides)
    return ProfileRecord.model_validate(values)


def make_pto_bank_record(**overrides: object) -> PtoBankRecord:
    values: dict[str, object] = {
        "id": TEST_PTO_BANK_ID,
        "owner_id": TEST_USER_UUID,
        "annual_balance": 10,
        "extended_balance": 0,
        "seniority_balance": 1,
        "year": 2026,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    values.update(overrides)
    return PtoBankRecord.model_validate(values)
