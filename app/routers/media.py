"""Public, authenticated, and token-shared access to uploaded files."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.auth import get_current_user
from app.services.media import (
    PRIVATE_MEDIA_CACHE_CONTROL,
    PUBLIC_MEDIA_CACHE_CONTROL,
    SHARED_MEDIA_CACHE_CONTROL,
    is_public_upload,
    resolve_upload_file,
    uploaded_file_response,
)
from app.services.share_links import resolve_share_token


router = APIRouter()


@router.api_route(
    "/uploads/{file_path:path}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
    name="uploaded_media",
)
def uploaded_media(request: Request, file_path: str) -> Response:
    target, relative_path = resolve_upload_file(file_path)
    is_public = is_public_upload(relative_path)
    if not is_public and not get_current_user(request):
        # Do not disclose whether a private path exists.
        raise HTTPException(status_code=404, detail="File not found")
    return uploaded_file_response(
        target,
        relative_path,
        cache_control=(PUBLIC_MEDIA_CACHE_CONTROL if is_public else PRIVATE_MEDIA_CACHE_CONTROL),
        noindex=not is_public,
    )


@router.api_route(
    "/share/{token}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
    name="shared_file",
)
def shared_file(token: str) -> Response:
    relative_path = resolve_share_token(token)
    if relative_path is None:
        raise HTTPException(status_code=404, detail="Shared file not found")
    target, normalized_path = resolve_upload_file(relative_path)
    return uploaded_file_response(
        target,
        normalized_path,
        cache_control=SHARED_MEDIA_CACHE_CONTROL,
        noindex=True,
    )
