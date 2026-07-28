import sqlite3
from collections.abc import Iterator

from backend.app.config import DATABASE_PATH, ensure_runtime_directories

SCHEMA_VERSION = 2


def get_connection() -> sqlite3.Connection:
    ensure_runtime_directories()
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def db_session() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


def create_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS face_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            embedding_path TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source TEXT NOT NULL,
            location TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS surveillance_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'running'
                CHECK(status IN ('running', 'stopped', 'failed')),
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ended_at TEXT,
            average_fps REAL CHECK(average_fps IS NULL OR average_fps >= 0),
            frames_processed INTEGER NOT NULL DEFAULT 0
                CHECK(frames_processed >= 0),
            error_message TEXT,
            FOREIGN KEY(camera_id) REFERENCES cameras(id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS detection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            camera_id INTEGER NOT NULL,
            member_id INTEGER,
            track_id INTEGER,
            status TEXT NOT NULL
                CHECK(status IN ('known', 'unknown', 'low_quality')),
            confidence REAL CHECK(
                confidence IS NULL OR (confidence >= -1.0 AND confidence <= 1.0)
            ),
            snapshot_path TEXT,
            detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id)
                REFERENCES surveillance_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(camera_id) REFERENCES cameras(id),
            FOREIGN KEY(member_id) REFERENCES people(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            camera_id INTEGER NOT NULL,
            detection_log_id INTEGER,
            member_id INTEGER,
            alert_type TEXT NOT NULL
                CHECK(alert_type IN (
                    'unknown_person',
                    'restricted_area',
                    'loitering'
                )),
            message TEXT NOT NULL,
            confidence REAL CHECK(
                confidence IS NULL OR (confidence >= -1.0 AND confidence <= 1.0)
            ),
            snapshot_path TEXT,
            is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id)
                REFERENCES surveillance_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(camera_id) REFERENCES cameras(id),
            FOREIGN KEY(detection_log_id)
                REFERENCES detection_logs(id) ON DELETE SET NULL,
            FOREIGN KEY(member_id) REFERENCES people(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            polygon_json TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
            UNIQUE(camera_id, name)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_face_embeddings_person
        ON face_embeddings(person_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_camera_started
        ON surveillance_sessions(camera_id, started_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_detection_logs_session_time
        ON detection_logs(session_id, detected_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_detection_logs_camera_time
        ON detection_logs(camera_id, detected_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_alerts_created
        ON alerts(created_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_alerts_camera_created
        ON alerts(camera_id, created_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_alerts_unread
        ON alerts(is_read, created_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_zones_camera
        ON zones(camera_id, is_active)
        """
    )
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.commit()


def init_db() -> None:
    ensure_runtime_directories()
    connection = get_connection()
    try:
        create_schema(connection)
    finally:
        connection.close()
