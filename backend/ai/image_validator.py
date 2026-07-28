from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from backend.app.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    MIN_FACE_IMAGE_HEIGHT,
    MIN_FACE_IMAGE_WIDTH,
)


@dataclass(frozen=True)
class ValidatedImage:
    filename: str
    extension: str
    content: bytes
    width: int
    height: int


class ImageValidationError(ValueError):
    pass


def validate_uploaded_image(filename: str | None, content: bytes) -> ValidatedImage:
    if not filename:
        raise ImageValidationError("Image filename is required")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ImageValidationError(f"Unsupported image type: {filename}")

    if not content:
        raise ImageValidationError(f"Image file is empty: {filename}")

    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError(f"Unreadable image file: {filename}") from exc

    if width < MIN_FACE_IMAGE_WIDTH or height < MIN_FACE_IMAGE_HEIGHT:
        raise ImageValidationError(
            f"Image is too small for registration: {filename}"
        )

    return ValidatedImage(
        filename=filename,
        extension=extension,
        content=content,
        width=width,
        height=height,
    )
