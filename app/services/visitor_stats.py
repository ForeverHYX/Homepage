"""Small, privacy-conscious visitor counter and location aggregation service.

Raw IP addresses stay on the server in a local SQLite database. The public
summary endpoint only exposes rounded, weighted coordinates so the browser can
render a heat map without leaking visitor addresses.
"""

from __future__ import annotations

import ipaddress
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

import httpx

from app.config import BASE_DIR


STATS_DB = Path(
    os.getenv("HOMEPAGE_STATS_DB", BASE_DIR / "data" / "visitor-stats.sqlite3")
).resolve()
GEOLOCATION_URL = os.getenv("HOMEPAGE_GEOLOCATION_URL", "http://ip-api.com/json").rstrip("/")
_DB_LOCK = Lock()
_GEO_FIELDS = "status,message,country,city,lat,lon"


def _connection() -> sqlite3.Connection:
    STATS_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(STATS_DB, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _DB_LOCK, _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                country TEXT,
                city TEXT,
                geo_attempted_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_visits_ip ON visits(ip)")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_visits_geo ON visits(geo_attempted_at, latitude)"
        )


def _normalise_ip(value: str | None) -> str:
    if not value:
        return ""
    candidate = value.strip().strip("[]")
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return ""


def record_visit(ip: str | None) -> None:
    """Record one successful public HTML view."""
    normalised = _normalise_ip(ip)
    if not normalised:
        return
    parsed = ipaddress.ip_address(normalised)
    if parsed.is_private or parsed.is_loopback or parsed.is_reserved or parsed.is_unspecified:
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _DB_LOCK, _connection() as connection:
        connection.execute(
            "INSERT INTO visits (ip, created_at) VALUES (?, ?)",
            (normalised, now),
        )


def _geolocate(ip: str) -> dict[str, Any] | None:
    try:
        response = httpx.get(
            f"{GEOLOCATION_URL}/{ip}",
            params={"fields": _GEO_FIELDS},
            timeout=2.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return None
    try:
        latitude = float(payload["lat"])
        longitude = float(payload["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return {
        "latitude": round(latitude, 1),
        "longitude": round(longitude, 1),
        "country": str(payload.get("country") or ""),
        "city": str(payload.get("city") or ""),
    }


def _resolve_pending(limit: int = 8) -> None:
    """Best-effort geolocation for a few new addresses when the map opens."""
    with _DB_LOCK, _connection() as connection:
        rows = connection.execute(
            """
            SELECT ip FROM visits
            WHERE latitude IS NULL AND geo_attempted_at IS NULL
            GROUP BY ip ORDER BY MIN(id) LIMIT ?
            """,
            (limit,),
        ).fetchall()
        if not rows:
            return
        attempted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for row in rows:
            ip = row["ip"]
            result = _geolocate(ip)
            if result:
                connection.execute(
                    """
                    UPDATE visits SET latitude = ?, longitude = ?, country = ?, city = ?,
                        geo_attempted_at = ? WHERE ip = ?
                    """,
                    (
                        result["latitude"],
                        result["longitude"],
                        result["country"],
                        result["city"],
                        attempted_at,
                        ip,
                    ),
                )
            else:
                connection.execute(
                    "UPDATE visits SET geo_attempted_at = ? WHERE ip = ?",
                    (attempted_at, ip),
                )


def get_summary() -> dict[str, Any]:
    """Return the public counter and aggregated map points."""
    init_db()
    _resolve_pending()
    with _DB_LOCK, _connection() as connection:
        total = int(connection.execute("SELECT COUNT(*) FROM visits").fetchone()[0])
        rows = connection.execute(
            """
            SELECT latitude, longitude, SUM(1) AS weight,
                   GROUP_CONCAT(DISTINCT country) AS countries,
                   GROUP_CONCAT(DISTINCT city) AS cities
            FROM visits WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            GROUP BY latitude, longitude ORDER BY weight DESC
            LIMIT 500
            """
        ).fetchall()
    points = [
        {
            "lat": float(row["latitude"]),
            "lon": float(row["longitude"]),
            "weight": int(row["weight"]),
            "label": ", ".join(
                value
                for value in (row["cities"], row["countries"])
                if value
            ),
        }
        for row in rows
    ]
    return {
        "total_views": total,
        "points": points,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


init_db()
