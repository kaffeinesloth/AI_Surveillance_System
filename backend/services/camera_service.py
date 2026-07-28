import sqlite3


class CameraService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_camera(
        self,
        *,
        name: str,
        source: str,
        location: str | None,
    ) -> dict:
        clean_name = name.strip()
        clean_source = source.strip()
        clean_location = self._clean_optional(location)
        if not clean_name:
            raise ValueError("Camera name is required")
        if not clean_source:
            raise ValueError("Camera source is required")

        cursor = self.connection.execute(
            """
            INSERT INTO cameras (name, source, location)
            VALUES (?, ?, ?)
            """,
            (clean_name, clean_source, clean_location),
        )
        self.connection.commit()
        camera = self.get_camera(int(cursor.lastrowid))
        if camera is None:
            raise RuntimeError("Camera was created but could not be reloaded")
        return camera

    def list_cameras(self, *, include_inactive: bool = False) -> list[dict]:
        if include_inactive:
            rows = self.connection.execute(
                """
                SELECT id, name, source, location, is_active, created_at, updated_at
                FROM cameras
                ORDER BY is_active DESC, created_at DESC, id DESC
                """
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT id, name, source, location, is_active, created_at, updated_at
                FROM cameras
                WHERE is_active = 1
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [self._row_to_camera(row) for row in rows]

    def get_camera(self, camera_id: int) -> dict | None:
        row = self.connection.execute(
            """
            SELECT id, name, source, location, is_active, created_at, updated_at
            FROM cameras
            WHERE id = ?
            """,
            (camera_id,),
        ).fetchone()
        return self._row_to_camera(row) if row is not None else None

    def update_camera(
        self,
        camera_id: int,
        changes: dict,
    ) -> dict | None:
        current = self.get_camera(camera_id)
        if current is None:
            return None

        allowed_fields = {"name", "source", "location", "is_active"}
        updates: dict[str, object] = {}
        for field, value in changes.items():
            if field not in allowed_fields:
                continue
            if field in {"name", "source"} and value is not None:
                clean_value = str(value).strip()
                if not clean_value:
                    raise ValueError(f"Camera {field} is required")
                updates[field] = clean_value
            elif field == "location":
                updates[field] = self._clean_optional(value)
            elif field == "is_active" and value is not None:
                updates[field] = int(bool(value))

        if not updates:
            return current

        assignments = ", ".join(f"{field} = ?" for field in updates)
        values = [*updates.values(), camera_id]
        self.connection.execute(
            f"""
            UPDATE cameras
            SET {assignments}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )
        self.connection.commit()
        return self.get_camera(camera_id)

    def deactivate_camera(self, camera_id: int) -> dict | None:
        camera = self.get_camera(camera_id)
        if camera is None:
            return None
        if camera["is_active"]:
            self.connection.execute(
                """
                UPDATE cameras
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (camera_id,),
            )
            self.connection.commit()
        return self.get_camera(camera_id)

    @staticmethod
    def _row_to_camera(row: sqlite3.Row) -> dict:
        camera = dict(row)
        camera["is_active"] = bool(camera["is_active"])
        return camera

    @staticmethod
    def _clean_optional(value: object | None) -> str | None:
        if value is None:
            return None
        clean_value = str(value).strip()
        return clean_value or None
