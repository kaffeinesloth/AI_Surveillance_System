import sqlite3
from dataclasses import dataclass

import numpy as np

from backend.ai.analysis_engine import FrameAnalysisEngine
from backend.ai.face_recognizer import (
    InMemoryFaceGallery,
    InsightFaceTrackRecognizer,
)
from backend.ai.person_tracker import YoloByteTracker
from backend.app.config import resolve_storage_path


@dataclass(frozen=True)
class AnalysisRuntime:
    engine: FrameAnalysisEngine
    member_names: dict[int, str]


def build_analysis_runtime(connection: sqlite3.Connection) -> AnalysisRuntime:
    gallery = InMemoryFaceGallery()
    member_names = {
        int(row["id"]): str(row["name"])
        for row in connection.execute(
            "SELECT id, name FROM people ORDER BY id"
        ).fetchall()
    }

    rows = connection.execute(
        """
        SELECT person_id, embedding_path
        FROM face_embeddings
        WHERE embedding_path IS NOT NULL
        ORDER BY person_id, id
        """
    ).fetchall()
    embeddings: dict[int, list[np.ndarray]] = {}
    for row in rows:
        path = resolve_storage_path(row["embedding_path"])
        try:
            embedding = np.load(path, allow_pickle=False)
            embeddings.setdefault(int(row["person_id"]), []).append(embedding)
        except (OSError, ValueError):
            continue
    gallery.replace(embeddings)

    engine = FrameAnalysisEngine(
        person_tracker=YoloByteTracker(),
        face_recognizer=InsightFaceTrackRecognizer(gallery),
    )
    return AnalysisRuntime(engine=engine, member_names=member_names)
