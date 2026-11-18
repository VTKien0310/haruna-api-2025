import io

from PIL import Image

from app.features.media.entities import Media, MediaType
from app.features.media.services import CreateMediaThumbnailService
from tests.fakes.sqlite_supabase import SqliteSupabasePort


def test_create_thumbnail_uploads_a_resized_image(supabase: SqliteSupabasePort) -> None:
    original = _jpeg(width=40, height=20)
    media = Media(
        id="media-1",
        name="photo.jpg",
        type=MediaType.IMAGE,
        storage_path="media-1/photo.jpg",
        thumbnail_path=None,
    )
    supabase.storage_media().upload(media.storage_path, original)
    service = CreateMediaThumbnailService(supabase)

    url = service.handle(media, 16, 8)

    assert url == "https://storage.invalid/resized/media-1/16x8.jpeg?expires=1800"
    resized = Image.open(
        io.BytesIO(supabase.storage_resized().download("media-1/16x8.jpeg"))
    )
    assert resized.size == (16, 8)
    supabase.storage_media().upload(media.storage_path, b"not-an-image")
    assert service.handle(media, 16, 8) == url


def _jpeg(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buffer, format="JPEG")
    return buffer.getvalue()
