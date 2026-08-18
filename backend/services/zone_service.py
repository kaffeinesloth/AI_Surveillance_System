import json
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class ZonePoint:
    x: int
    y: int


@dataclass(frozen=True)
class RestrictedZone:
    id: int
    camera_id: int
    name: str
    points: tuple[ZonePoint, ...]
    is_active: bool = True


class ZoneService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_zone(
        self,
        *,
        camera_id: int,
        name: str,
        points: list[dict],
    ) -> dict:
        self._require_camera(camera_id)
        clean_name = self._clean_name(name)
        clean_points = self._clean_points(points)
        cursor = self.connection.execute(
            """
            INSERT INTO zones (camera_id, name, polygon_json)
            VALUES (?, ?, ?)
            """,
            (camera_id, clean_name, json.dumps(clean_points)),
        )
        self.connection.commit()
        zone = self.get_zone(int(cursor.lastrowid))
        if zone is None:
            raise RuntimeError("Zone was created but could not be reloaded")
        return zone

    def list_zones(
        self,
        *,
        camera_id: int | None = None,
        include_inactive: bool = False,
    ) -> list[dict]:
        conditions = []
        parameters: list[object] = []
        if camera_id is not None:
            conditions.append("camera_id = ?")
            parameters.append(camera_id)
        if not include_inactive:
            conditions.append("is_active = 1")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self.connection.execute(
            f"""
            SELECT id, camera_id, name, polygon_json, is_active,
                   created_at, updated_at
            FROM zones
            {where}
            ORDER BY camera_id, name COLLATE NOCASE, id
            """,
            parameters,
        ).fetchall()
        return [self._row_to_zone(row) for row in rows]

    def list_active_restricted_zones(self, camera_id: int) -> list[RestrictedZone]:
        return [
            self._to_restricted_zone(zone)
            for zone in self.list_zones(camera_id=camera_id)
        ]

    def get_zone(self, zone_id: int) -> dict | None:
        row = self.connection.execute(
            """
            SELECT id, camera_id, name, polygon_json, is_active,
                   created_at, updated_at
            FROM zones
            WHERE id = ?
            """,
            (zone_id,),
        ).fetchone()
        return self._row_to_zone(row) if row is not None else None

    def update_zone(self, zone_id: int, changes: dict) -> dict | None:
        current = self.get_zone(zone_id)
        if current is None:
            return None

        updates: dict[str, object] = {}
        if "name" in changes and changes["name"] is not None:
            updates["name"] = self._clean_name(str(changes["name"]))
        if "points" in changes and changes["points"] is not None:
            updates["polygon_json"] = json.dumps(
                self._clean_points(changes["points"])
            )
        if "is_active" in changes and changes["is_active"] is not None:
            updates["is_active"] = int(bool(changes["is_active"]))

        if not updates:
            return current

        assignments = ", ".join(f"{field} = ?" for field in updates)
        self.connection.execute(
            f"""
            UPDATE zones
            SET {assignments}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            [*updates.values(), zone_id],
        )
        self.connection.commit()
        return self.get_zone(zone_id)

    def delete_zone(self, zone_id: int) -> dict | None:
        zone = self.get_zone(zone_id)
        if zone is None:
            return None
        self.connection.execute("DELETE FROM zones WHERE id = ?", (zone_id,))
        self.connection.commit()
        return zone

    def _require_camera(self, camera_id: int) -> None:
        row = self.connection.execute(
            "SELECT id FROM cameras WHERE id = ? AND is_active = 1",
            (camera_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Active camera not found")

    @staticmethod
    def _clean_name(name: str) -> str:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Zone name is required")
        return clean_name

    @staticmethod
    def _clean_points(points: list[dict]) -> list[list[int]]:
        clean_points = []
        for point in points:
            x = int(point["x"])
            y = int(point["y"])
            if x < 0 or y < 0:
                raise ValueError("Zone coordinates must be non-negative")
            clean_points.append([x, y])
        if len(clean_points) != 4:
            raise ValueError("Zone must include exactly four points")
        return clean_points

    @staticmethod
    def _row_to_zone(row: sqlite3.Row) -> dict:
        zone = dict(row)
        raw_points = json.loads(zone.pop("polygon_json"))
        zone["points"] = [
            {"x": int(point[0]), "y": int(point[1])}
            for point in raw_points
        ]
        zone["is_active"] = bool(zone["is_active"])
        return zone

    @staticmethod
    def _to_restricted_zone(zone: dict) -> RestrictedZone:
        return RestrictedZone(
            id=int(zone["id"]),
            camera_id=int(zone["camera_id"]),
            name=str(zone["name"]),
            points=tuple(
                ZonePoint(x=int(point["x"]), y=int(point["y"]))
                for point in zone["points"]
            ),
            is_active=bool(zone["is_active"]),
        )
