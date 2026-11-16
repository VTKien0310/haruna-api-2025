from uuid import uuid4

from app.database import PtoAffectEntryRecord
from app.features.attendance.entities import WorkdayException
from app.features.pto.entities import PtoAffectEntry
from tests.factories.database_records import TEST_USER_UUID


def test_title_survives_both_pto_factories() -> None:
    record = PtoAffectEntryRecord(owner_id=TEST_USER_UUID, title="Family trip")
    assert PtoAffectEntry.from_db_record(record).title == "Family trip"
    data: dict[str, str | int] = {
        "id": str(record.id),
        "owner_id": str(record.owner_id),
        "entry_id": "",
        "entry_type": "",
        "no_deduction": 0,
        "note": "",
        "title": "Family trip",
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
    assert PtoAffectEntry.from_spb_data(data).title == "Family trip"


def test_workday_exception_title_survives_supabase_factory() -> None:
    data: dict[str, str | int] = {
        "id": str(uuid4()),
        "type": 1,
        "date": "2026-01-01",
        "time": 0,
        "title": "New Year's Day",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    assert WorkdayException.from_spb_data(data).title == "New Year's Day"
