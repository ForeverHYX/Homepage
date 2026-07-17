"""Content-fingerprinted URLs for static and uploaded assets."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from app.config import BASE_DIR, UPLOAD_DIR


ASSET_MANIFEST_PATH = BASE_DIR / "static" / "asset-manifest.json"


@lru_cache(maxsize=1)
def _asset_manifest() -> dict[str, str]:
    try:
        payload = json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in payload.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def asset_url(path: str) -> str:
    """Return the build fingerprint for one file below ``static/``.

    The readable fallback keeps development usable before the first build.
    Production deployments run the asset builder and therefore receive a new
    URL whenever bytes change, making long immutable browser caching safe.
    """
    normalized = path.removeprefix("/static/").lstrip("/")
    return _asset_manifest().get(normalized, f"/static/{quote(normalized, safe='/')}")


def upload_url(path: str) -> str:
    """Return a conservatively versioned URL for a mutable uploaded file."""
    normalized = path.removeprefix("/uploads/").lstrip("/")
    file_path = Path(UPLOAD_DIR) / normalized
    encoded = quote(normalized, safe="/")
    try:
        stat_result = file_path.stat()
    except OSError:
        return f"/uploads/{encoded}"
    return f"/uploads/{encoded}?v={stat_result.st_mtime_ns:x}-{stat_result.st_size:x}"
