import sqlite3


class AlertService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_alerts(
        self,
        *,
        is_read: bool | None = None,
        camera_id: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conditions = []
        parameters: list[object] = []
        if is_read is not None:
            conditions.append("a.is_read = ?")
            parameters.append(int(is_read))
        if camera_id is not None:
            conditions.append("a.camera_id = ?")
            parameters.append(camera_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        parameters.append(limit)
        rows = self.connection.execute(
            f"""
            SELECT
                a.id,
                a.session_id,
                a.camera_id,
                a.detection_log_id,
                a.member_id,
                a.alert_type,
                a.message,
                a.confidence,
                a.snapshot_path,
                a.is_read,
                a.created_at,
                p.name AS member_name,
                c.name AS camera_name
            FROM alerts a
            JOIN cameras c ON c.id = a.camera_id
            LEFT JOIN people p ON p.id = a.member_id
            {where}
            ORDER BY a.created_at DESC, a.id DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        return [self._to_alert(row) for row in rows]

    def get_alert(self, alert_id: int) -> dict | None:
        row = self.connection.execute(
            """
            SELECT
                a.id,
                a.session_id,
                a.camera_id,
                a.detection_log_id,
                a.member_id,
                a.alert_type,
                a.message,
                a.confidence,
                a.snapshot_path,
                a.is_read,
                a.created_at,
                p.name AS member_name,
                c.name AS camera_name
            FROM alerts a
            JOIN cameras c ON c.id = a.camera_id
            LEFT JOIN people p ON p.id = a.member_id
            WHERE a.id = ?
            """,
            (alert_id,),
        ).fetchone()
        return self._to_alert(row) if row is not None else None

    def latest_alert(self) -> dict | None:
        alerts = self.list_alerts(limit=1)
        return alerts[0] if alerts else None

    def update_read_status(
        self,
        alert_id: int,
        *,
        is_read: bool,
    ) -> dict | None:
        if self.get_alert(alert_id) is None:
            return None
        self.connection.execute(
            "UPDATE alerts SET is_read = ? WHERE id = ?",
            (int(is_read), alert_id),
        )
        self.connection.commit()
        return self.get_alert(alert_id)

    @staticmethod
    def _to_alert(row: sqlite3.Row) -> dict:
        alert = dict(row)
        alert["is_read"] = bool(alert["is_read"])
        alert["snapshot_url"] = (
            f"/alerts/{alert['id']}/snapshot"
            if alert["snapshot_path"]
            else None
        )
        return alert
