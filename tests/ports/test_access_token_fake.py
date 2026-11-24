from datetime import datetime, timezone

from app.ports.supabase import VerifiedAccessToken
from tests.fakes.access_token import AccessTokenFake
from tests.fakes.sqlite_supabase import SqliteSupabasePort


async def test_registered_label_verifies_as_that_user(
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id="user-7")

    verified = await AccessTokenFake(supabase).verify("token-1")

    assert isinstance(verified, VerifiedAccessToken)
    assert verified.user_id == "user-7"
    assert verified.audience == "authenticated"
    assert verified.created_at == datetime(2026, 1, 1, tzinfo=timezone.utc)


async def test_unknown_or_rejected_label_does_not_verify(
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().reject("token-1")
    verifier = AccessTokenFake(supabase)

    assert await verifier.verify("token-1") is None
    assert await verifier.verify("missing") is None
