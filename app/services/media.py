"""Authorization policy and efficient responses for mutable uploaded media."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

from app.config import (
    PUBLIC_UPLOAD_FILES,
    PUBLIC_UPLOAD_PREFIXES,
    UPLOAD_DIR,
    USE_X_ACCEL_REDIRECT,
)
from app.file_utils import safe_join
from app.gallery_utils import get_gallery_visibility_map
from app.gallery_thumbnail_utils import THUMBNAIL_DIR_NAME


PUBLIC_MEDIA_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=3600"
PRIVATE_MEDIA_CACHE_CONTROL = "private, no-store"
SHARED_MEDIA_CACHE_CONTROL = "public, max-age=300"
_INTERNAL_UPLOAD_PREFIX = "/_homepage_uploads/"


def resolve_upload_file(file_path: str) -> tuple[Path, str]:
    clean_path = file_path.strip().lstrip("/")
    if not clean_path:
        raise HTTPException(status_code=404, detail="File not found")
    target = safe_join(Path(UPLOAD_DIR), clean_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    relative_path = target.resolve().relative_to(Path(UPLOAD_DIR).resolve()).as_posix()
    return target, relative_path


def _is_within(relative_path: str, folder: str) -> bool:
    normalized = folder.strip().strip("/")
    return bool(normalized) and (
        relative_path == normalized or relative_path.startswith(f"{normalized}/")
    )


def _gallery_visibility(relative_path: str) -> str | None:
    matches = [
        (folder.strip().strip("/"), state)
        for folder, state in get_gallery_visibility_map().items()
        if _is_within(relative_path, folder)
    ]
    if not matches:
        return None
    # A nested private/hidden album must override a public parent album.
    return max(matches, key=lambda item: len(item[0]))[1]


def is_public_upload(relative_path: str) -> bool:
    """Return whether a path is part of the intentionally public site."""

    if relative_path in PUBLIC_UPLOAD_FILES:
        return True
    if any(relative_path.startswith(prefix) for prefix in PUBLIC_UPLOAD_PREFIXES):
        return True

    visibility = _gallery_visibility(relative_path)
    if visibility is not None:
        return visibility == "public"

    thumbnail_prefix = f"{THUMBNAIL_DIR_NAME}/"
    if relative_path.startswith(thumbnail_prefix):
        source_relative = relative_path[len(thumbnail_prefix) :]
        return _gallery_visibility(source_relative) == "public"
    return False


def uploaded_file_response(
    target: Path,
    relative_path: str,
    *,
    cache_control: str,
    download: bool = False,
    noindex: bool = False,
) -> Response:
    """Serve locally in development or delegate bytes to Nginx in production."""

    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    headers = {
        "Cache-Control": cache_control,
        "X-Content-Type-Options": "nosniff",
    }
    if noindex:
        headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    if download:
        encoded_name = quote(target.name, safe="")
        headers["Content-Disposition"] = f"attachment; filename*=utf-8''{encoded_name}"

    if USE_X_ACCEL_REDIRECT:
        headers["X-Accel-Redirect"] = f"{_INTERNAL_UPLOAD_PREFIX}{quote(relative_path, safe='/')}"
        return Response(content=b"", media_type=media_type, headers=headers)

    return FileResponse(
        target,
        media_type=media_type,
        filename=target.name if download else None,
        headers=headers,
    )
