from dataclasses import dataclass


@dataclass(frozen=True)
class SavedFaceImage:
    id: int
    image_path: str
    embedding_path: str | None
    created_at: str
