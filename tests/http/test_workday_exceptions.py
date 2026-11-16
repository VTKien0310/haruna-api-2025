from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import create_app
from app.database import (
    DbSessionManager,
    UserSpecialPermissionRecord,
    WorkdayExceptionRecord,
)
from app.features.attendance.services import workday_exception_today
from tests.factories.database_records import TEST_USER_ID, TEST_USER_UUID
from tests.fakes.sqlite_supabase import SqliteSupabasePort

BASE = "/api/attendance/workday-exceptions"
HEADERS = {"Authorization": "Bearer token-1"}


def payload(day: date | None = None) -> dict[str, str | int]:
    return {
        "date": (day or workday_exception_today()).isoformat(),
        "type": 1,
        "time": 0,
        "title": "Holiday",
    }


@pytest.fixture
async def manager(
    db_session_manager: DbSessionManager, supabase: SqliteSupabasePort
) -> DbSessionManager:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    async with db_session_manager.transaction() as session:
        session.add(UserSpecialPermissionRecord(user_id=TEST_USER_UUID, permission=0))
    return db_session_manager


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("POST", "", payload()),
        ("GET", "", None),
        ("GET", f"/{uuid4()}", None),
        ("PATCH", f"/{uuid4()}", {"title": "Changed"}),
        ("DELETE", f"/{uuid4()}", None),
    ],
)
async def test_access_is_required(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
    method: str,
    suffix: str,
    body: dict | None,
) -> None:
    assert db_client.request(method, BASE + suffix, json=body).status_code == 401
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    response = db_client.request(method, BASE + suffix, json=body, headers=HEADERS)
    assert response.status_code == 403
    assert response.json()["content"]["error"]["code"] == "forbidden"


async def test_crud_and_overlaps(
    db_client: TestClient, manager: DbSessionManager
) -> None:
    first = db_client.post(BASE, json=payload(), headers=HEADERS)
    assert first.status_code == 201
    original = first.json()["content"]
    path = f"{BASE}/{original['id']}"
    UUID(original["id"])
    stored = db_client.get(path, headers=HEADERS).json()["content"]
    # SQLite drops timezone information on reload; PostgreSQL retains it.
    assert stored == {
        key: value.removesuffix("Z") if key.endswith("_at") else value
        for key, value in original.items()
    }
    original = stored
    assert db_client.post(BASE, json=payload(), headers=HEADERS).status_code == 201
    listing = db_client.get(BASE, headers=HEADERS).json()["content"]
    assert len(listing) == 2
    assert listing == sorted(listing, key=lambda item: (item["date"], item["id"]))
    response = db_client.patch(path, json={"title": " New title "}, headers=HEADERS)
    assert response.status_code == 200
    changed = response.json()["content"]
    assert changed["title"] == "New title"
    for field in ["id", "created_at", "date", "time", "type"]:
        assert changed[field] == original[field]
    assert changed["updated_at"] != original["updated_at"]
    tomorrow = workday_exception_today() + timedelta(days=1)
    assert (
        db_client.patch(
            path,
            json={"date": tomorrow.isoformat(), "type": 0, "time": 2},
            headers=HEADERS,
        ).status_code
        == 200
    )
    deleted = db_client.delete(path, headers=HEADERS)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert db_client.get(path, headers=HEADERS).status_code == 404


async def test_past_records_are_readable_and_immutable(
    db_client: TestClient, manager: DbSessionManager
) -> None:
    yesterday = workday_exception_today() - timedelta(days=1)
    async with manager.transaction() as session:
        record = WorkdayExceptionRecord(date=yesterday, type=1, time=0, title="Past")
        session.add(record)
        await session.flush()
        exception_id = record.id
    path = f"{BASE}/{exception_id}"
    assert db_client.get(path, headers=HEADERS).status_code == 200
    assert len(db_client.get(BASE, headers=HEADERS).json()["content"]) == 1
    attempts = [
        db_client.post(BASE, json=payload(yesterday), headers=HEADERS),
        db_client.patch(path, json={"title": "Changed"}, headers=HEADERS),
        db_client.patch(
            path, json={"date": workday_exception_today().isoformat()}, headers=HEADERS
        ),
        db_client.delete(path, headers=HEADERS),
    ]
    for response in attempts:
        assert response.status_code == 409
        assert (
            response.json()["content"]["error"]["code"]
            == "past_workday_exception_immutable"
        )
    async with manager.session() as session:
        records = (await session.exec(select(WorkdayExceptionRecord))).scalars().all()
        assert len(records) == 1
        assert records[0].title == "Past"
        assert records[0].date == yesterday


async def test_cannot_move_current_exception_into_past(
    db_client: TestClient, manager: DbSessionManager
) -> None:
    original = db_client.post(BASE, json=payload(), headers=HEADERS).json()["content"]
    path = f"{BASE}/{original['id']}"
    original = db_client.get(path, headers=HEADERS).json()["content"]
    response = db_client.patch(
        path,
        json={"date": (workday_exception_today() - timedelta(days=1)).isoformat()},
        headers=HEADERS,
    )
    assert response.status_code == 409
    assert db_client.get(path, headers=HEADERS).json()["content"] == original


@pytest.mark.parametrize(
    "changes",
    [
        {"type": 4},
        {"time": -1},
        {"date": "invalid"},
        {"title": "  "},
        {"title": None},
        {"id": str(uuid4())},
    ],
)
async def test_invalid_bodies(
    db_client: TestClient, manager: DbSessionManager, changes: dict
) -> None:
    assert (
        db_client.post(BASE, json=payload() | changes, headers=HEADERS).status_code
        == 422
    )
    assert (
        db_client.patch(f"{BASE}/{uuid4()}", json=changes, headers=HEADERS).status_code
        == 422
    )


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_missing_and_invalid_ids(
    db_client: TestClient, manager: DbSessionManager, method: str
) -> None:
    body = {"title": "Changed"} if method == "PATCH" else None
    response = db_client.request(
        method, f"{BASE}/{uuid4()}", json=body, headers=HEADERS
    )
    assert response.status_code == 404
    assert response.json()["content"]["error"]["code"] == "workday_exception_not_found"
    assert (
        db_client.request(
            method, f"{BASE}/bad-id", json=body, headers=HEADERS
        ).status_code
        == 422
    )


async def test_empty_patch(db_client: TestClient, manager: DbSessionManager) -> None:
    assert (
        db_client.patch(f"{BASE}/{uuid4()}", json={}, headers=HEADERS).status_code
        == 422
    )


def test_vietnam_today(monkeypatch: pytest.MonkeyPatch) -> None:
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(
        "app.features.attendance.services.workday_exception_rules.datetime",
        FrozenDatetime,
    )
    assert workday_exception_today() == date(2026, 11, 16)


def test_openapi_contract() -> None:
    schema = create_app().openapi()
    for path, methods in [
        (BASE, ["post", "get"]),
        (BASE + "/{exception_id}", ["get", "patch", "delete"]),
    ]:
        for method in methods:
            operation = schema["paths"][path][method]
            assert operation["security"]
            assert "403" in operation["responses"]
            for status, response in operation["responses"].items():
                if status == "204":
                    assert "content" not in response
                elif "application/json" in response.get("content", {}):
                    assert set(
                        response["content"]["application/json"]["schema"]["properties"]
                    ) == {"ok", "content"}
    assert "HTTPValidationError" not in schema["components"]["schemas"]
