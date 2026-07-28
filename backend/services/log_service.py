import sqlite3

from backend.app.models import DetectionStatus


class LogService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_logs(
        self,
        *,
        status: DetectionStatus | None = None,
        camera_id: int | None = None,
        session_id: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conditions = []
        parameters: list[object] = []
        if status is not None:
            conditions.append("d.status = ?")
            parameters.append(status.value)
        if camera_id is not None:
            conditions.append("d.camera_id = ?")
            parameters.append(camera_id)
        if session_id is not None:
            conditions.append("d.session_id = ?")
            parameters.append(session_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        parameters.append(limit)
        rows = self.connection.execute(
            f"""
            SELECT
                d.id,
                d.session_id,
                d.camera_id,
                d.member_id,
                d.track_id,
                d.status,
                d.confidence,
                d.snapshot_path,
                d.detected_at,
                p.name AS member_name,
                c.name AS camera_name
            FROM detection_logs d
            JOIN cameras c ON c.id = d.camera_id
            LEFT JOIN people p ON p.id = d.member_id
            {where}
            ORDER BY d.detected_at DESC, d.id DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        return [dict(row) for row in rows]

    def latest_log(self) -> dict | None:
        logs = self.list_logs(limit=1)
        return logs[0] if logs else None
