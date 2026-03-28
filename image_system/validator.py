from __future__ import annotations

import hashlib
import io

from PIL import Image, UnidentifiedImageError

from .config import Settings
from .models import ValidatedImage


def validate_image_bytes(image_bytes: bytes, settings: Settings) -> ValidatedImage:
    if len(image_bytes) < settings.min_size_bytes:
        raise ValueError(f"image is smaller than {settings.min_size_bytes} bytes")

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.load()
            width, height = image.size
            if width < settings.min_width or height < settings.min_height:
                raise ValueError(f"image resolution {width}x{height} is below minimum")

            image_format = (image.format or "").upper()
            if image_format not in {"JPEG", "PNG"}:
                raise ValueError(f"unsupported image format: {image_format}")

            extension = "jpg" if image_format == "JPEG" else "png"
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("image bytes are invalid or unreadable") from exc

    return ValidatedImage(
        extension=extension,
        width=width,
        height=height,
        size_bytes=len(image_bytes),
        content_hash=hashlib.md5(image_bytes).hexdigest(),
    )
