import io

from PIL import Image

from app.features.media.entities import Media
from app.ports import SupabasePortDep


class CreateMediaThumbnailService:
    def __init__(self, supabase: SupabasePortDep):
        self.__supabase = supabase

    def handle(self, media: Media, width: int, height: int) -> str:
        if self.__check_thumbnail_exists(media, width, height):
            return self.__make_thumbnail_signed_url(media, width, height)

        self.__create_thumbnail(media, width, height)

        return self.__make_thumbnail_signed_url(media, width, height)

    def __create_thumbnail(self, media: Media, width: int, height: int) -> None:
        original_file = self.__download_original_media(media)

        image = Image.open(io.BytesIO(original_file))
        image.thumbnail((width, height), Image.Resampling.LANCZOS)

        # Convert to JPEG and save to bytes
        thumbnail_buffer = io.BytesIO()
        if image.mode in (
            "RGBA",
            "LA",
            "P",
        ):  # If the original file is PNG, convert RGBA to RGB
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(
                image, mask=image.split()[-1] if image.mode == "RGBA" else None
            )
            rgb_image.save(thumbnail_buffer, format="JPEG", quality=75, optimize=True)
        else:
            image.save(thumbnail_buffer, format="JPEG", quality=75, optimize=True)

        thumbnail_buffer.seek(0)

        self.__supabase.storage_resized().upload(
            path=self.__make_thumbnail_path(media, width, height),
            file=thumbnail_buffer.getvalue(),
            file_options={"content-type": "image/jpeg"},
        )

    def __download_original_media(self, media: Media) -> bytes:
        if media.is_video:
            return self.__supabase.storage_thumbnails().download(media.thumbnail_path)

        return self.__supabase.storage_media().download(media.storage_path)

    def __check_thumbnail_exists(self, media: Media, width: int, height: int) -> bool:
        result = self.__supabase.storage_resized().list(
            media.id,
            {
                "limit": 1,
                "offset": 0,
                "sortBy": {"column": "name", "order": "desc"},
                "search": self.__make_thumbnail_name(width, height),
            },
        )
        return len(result) > 0

    @staticmethod
    def __make_thumbnail_name(width: int, height: int) -> str:
        return f"{width}x{height}.jpeg"

    def __make_thumbnail_signed_url(self, media: Media, width: int, height: int) -> str:
        return self.__supabase.storage_resized().create_signed_url(
            self.__make_thumbnail_path(media, width, height), 1800
        )["signedUrl"]

    def __make_thumbnail_path(self, media: Media, width: int, height: int) -> str:
        return f"{media.id}/{self.__make_thumbnail_name(width, height)}"
