from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps

from backend.ai.face_detector import FaceBox
from backend.app.config import FACE_CROP_PADDING_RATIO, FACE_CROP_SIZE


@dataclass(frozen=True)
class CroppedFaceImage:
    content: bytes
    extension: str
    width: int
    height: int


def crop_face_image(image_content: bytes, face_box: FaceBox) -> CroppedFaceImage:
    with Image.open(BytesIO(image_content)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        left, top, right, bottom = _padded_bounds(face_box, image.width, image.height)
        crop = image.crop((left, top, right, bottom))
        crop = ImageOps.fit(
            crop,
            (FACE_CROP_SIZE, FACE_CROP_SIZE),
            method=Image.Resampling.LANCZOS,
        )

        output = BytesIO()
        crop.save(output, format="JPEG", quality=95)

    return CroppedFaceImage(
        content=output.getvalue(),
        extension=".jpg",
        width=FACE_CROP_SIZE,
        height=FACE_CROP_SIZE,
    )


def _padded_bounds(face_box: FaceBox, image_width: int, image_height: int) -> tuple[int, int, int, int]:
    padding_x = int(face_box.width * FACE_CROP_PADDING_RATIO)
    padding_y = int(face_box.height * FACE_CROP_PADDING_RATIO)

    left = max(face_box.x - padding_x, 0)
    top = max(face_box.y - padding_y, 0)
    right = min(face_box.x + face_box.width + padding_x, image_width)
    bottom = min(face_box.y + face_box.height + padding_y, image_height)

    return left, top, right, bottom
