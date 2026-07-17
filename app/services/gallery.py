"""Gallery inventory, thumbnail selection, and cached presentation payloads."""

from __future__ import annotations

import copy
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import quote, urlencode

from app.cache import cache_by_signature, file_signature
from app.file_utils import safe_join
from app.gallery_thumbnail_utils import (
    GALLERY_IMAGE_EXTENSIONS,
    get_gallery_thumbnail_path,
)


ThumbnailResolver = Callable[[Path, Path], Path | None]
ThumbnailTokenBuilder = Callable[[Path], str]
FolderMetaLoader = Callable[[Path], dict]

GALLERY_PAYLOAD_CACHE_NAMESPACE = "gallery_payload"


@dataclass(frozen=True)
class ImageSnapshot:
    path: Path
    relative_path: Path
    source_mtime_ns: int
    source_size: int
    thumbnail_signature: tuple[int, int, int] | None


@dataclass(frozen=True)
class AlbumSnapshot:
    relative_path: str
    path: Path
    metadata_signature: tuple[int, int] | None
    images: tuple[ImageSnapshot, ...]
    newest_mtime: float


@dataclass(frozen=True)
class GalleryBuildResult:
    payload: dict
    pending_thumbnails: tuple[Path, ...]


def _thumbnail_signature(upload_dir: Path, image_path: Path) -> tuple[int, int, int] | None:
    thumbnail_path = get_gallery_thumbnail_path(upload_dir, image_path)
    try:
        thumbnail_stat = thumbnail_path.stat()
    except OSError:
        return None
    return (
        thumbnail_stat.st_mtime_ns,
        thumbnail_stat.st_size,
        stat.S_IMODE(thumbnail_stat.st_mode),
    )


def _album_snapshots(
    upload_dir: Path,
    gallery_dirs: Iterable[str],
    *,
    include_thumbnail_state: bool,
) -> tuple[AlbumSnapshot, ...]:
    albums: list[AlbumSnapshot] = []
    for relative_path in gallery_dirs:
        try:
            path = safe_join(upload_dir, relative_path)
            if not path.is_dir():
                continue
            entries = sorted(path.iterdir(), key=lambda item: item.name)
        except (OSError, ValueError):
            continue

        images: list[ImageSnapshot] = []
        newest_mtime = 0.0
        for entry in entries:
            try:
                entry_stat = entry.stat()
            except OSError:
                continue
            newest_mtime = max(newest_mtime, entry_stat.st_mtime)
            if not entry.is_file() or entry.suffix.lower() not in GALLERY_IMAGE_EXTENSIONS:
                continue
            relative_image = entry.relative_to(upload_dir)
            images.append(
                ImageSnapshot(
                    path=entry,
                    relative_path=relative_image,
                    source_mtime_ns=entry_stat.st_mtime_ns,
                    source_size=entry_stat.st_size,
                    thumbnail_signature=(
                        _thumbnail_signature(upload_dir, entry)
                        if include_thumbnail_state and entry.suffix.lower() != ".gif"
                        else None
                    ),
                )
            )
        if not images:
            continue
        albums.append(
            AlbumSnapshot(
                relative_path=relative_path,
                path=path,
                metadata_signature=file_signature(path / "meta.json"),
                images=tuple(images),
                newest_mtime=newest_mtime,
            )
        )
    return tuple(albums)


def _snapshot_signature(albums: tuple[AlbumSnapshot, ...]) -> tuple:
    return tuple(
        (
            album.relative_path,
            album.metadata_signature,
            tuple(
                (
                    image.relative_path.as_posix(),
                    image.source_mtime_ns,
                    image.source_size,
                    image.thumbnail_signature,
                )
                for image in album.images
            ),
        )
        for album in albums
    )


def _image_urls(
    upload_dir: Path,
    image: ImageSnapshot,
    *,
    focused: bool,
    defer_thumbnails: bool,
    ensure_thumbnail: ThumbnailResolver,
    current_thumbnail: ThumbnailResolver,
    thumbnail_token: ThumbnailTokenBuilder,
) -> tuple[str, str, Path | None]:
    original_url = f"/uploads/{quote(image.relative_path.as_posix(), safe='/')}"
    if focused or image.path.suffix.lower() == ".gif":
        return original_url, original_url, None

    if defer_thumbnails:
        thumbnail_path = current_thumbnail(upload_dir, image.path)
    else:
        thumbnail_path = ensure_thumbnail(upload_dir, image.path)
    if thumbnail_path is None:
        return original_url, original_url, image.path if defer_thumbnails else None

    thumbnail_relative = thumbnail_path.relative_to(upload_dir).as_posix()
    thumbnail_url = quote(thumbnail_relative, safe="/")
    token = thumbnail_token(image.path)
    return f"/uploads/{thumbnail_url}?v={token}", original_url, None


def _build_payload(
    upload_dir: Path,
    albums: tuple[AlbumSnapshot, ...],
    *,
    focus: str | None,
    focused: bool,
    defer_thumbnails: bool,
    ensure_thumbnail: ThumbnailResolver,
    current_thumbnail: ThumbnailResolver,
    thumbnail_token: ThumbnailTokenBuilder,
    folder_meta: FolderMetaLoader,
) -> GalleryBuildResult:
    payload_albums: list[dict] = []
    pending: list[Path] = []
    for album in albums:
        image_urls: list[str] = []
        full_image_urls: list[str] = []
        for image in album.images:
            image_url, full_image_url, pending_image = _image_urls(
                upload_dir,
                image,
                focused=focused,
                defer_thumbnails=defer_thumbnails,
                ensure_thumbnail=ensure_thumbnail,
                current_thumbnail=current_thumbnail,
                thumbnail_token=thumbnail_token,
            )
            image_urls.append(image_url)
            full_image_urls.append(full_image_url)
            if pending_image is not None:
                pending.append(pending_image)

        metadata = folder_meta(album.path)
        sort_timestamp = 0.0
        date_string = str(metadata.get("date") or "")
        if date_string:
            try:
                sort_timestamp = datetime.strptime(date_string, "%Y-%m-%d").timestamp()
            except ValueError:
                pass
        if sort_timestamp == 0.0 and album.newest_mtime:
            sort_timestamp = album.newest_mtime
            date_string = datetime.fromtimestamp(sort_timestamp).strftime("%Y-%m-%d")

        payload_albums.append(
            {
                "path_name": album.path.name,
                "rel_path": album.relative_path,
                "focus_url": f"/gallery?{urlencode({'focus': album.relative_path})}",
                "title": metadata.get("title", album.path.name),
                "desc": metadata.get("description", ""),
                "date_str": date_string,
                "author": metadata.get("author", "Yixun Hong"),
                "images": image_urls,
                "full_images": full_image_urls,
                "sort_ts": sort_timestamp,
                "wrapper_class": "carousel-wrapper focused" if focused else "carousel-wrapper",
            }
        )

    payload_albums.sort(key=lambda album: album["sort_ts"], reverse=True)
    return GalleryBuildResult(
        payload={"albums": payload_albums, "is_focused": focused, "focus": focus},
        pending_thumbnails=tuple(pending),
    )


def build_gallery_payload(
    upload_dir: Path,
    gallery_dirs: Iterable[str],
    *,
    focus: str | None,
    defer_thumbnails: bool,
    ensure_thumbnail: ThumbnailResolver,
    current_thumbnail: ThumbnailResolver,
    thumbnail_token: ThumbnailTokenBuilder,
    folder_meta: FolderMetaLoader,
) -> GalleryBuildResult:
    """Build a gallery response and reuse it until source bytes change."""
    resolved_upload_dir = upload_dir.resolve()
    available_dirs = tuple(gallery_dirs)
    focused = bool(focus and focus in available_dirs)
    selected_dirs = (focus,) if focused and focus else (() if focus else available_dirs)
    albums = _album_snapshots(
        resolved_upload_dir,
        selected_dirs,
        include_thumbnail_state=not focused,
    )
    signature = _snapshot_signature(albums)
    cache_key = (
        str(resolved_upload_dir),
        selected_dirs,
        focus or "",
        focused,
        defer_thumbnails,
    )
    result = cache_by_signature(
        cache_key,
        signature,
        lambda: _build_payload(
            resolved_upload_dir,
            albums,
            focus=focus,
            focused=focused,
            defer_thumbnails=defer_thumbnails,
            ensure_thumbnail=ensure_thumbnail,
            current_thumbnail=current_thumbnail,
            thumbnail_token=thumbnail_token,
            folder_meta=folder_meta,
        ),
        namespace=GALLERY_PAYLOAD_CACHE_NAMESPACE,
    )
    return GalleryBuildResult(
        payload=copy.deepcopy(result.payload),
        pending_thumbnails=result.pending_thumbnails,
    )
