"""Cached site-wide search index assembly."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from app.cache import cache_by_signature, file_signature
from app.config import CONTENT_DIR, GALLERY_CONFIG_FILE, UPLOAD_DIR
from app.daily import (
    DEFAULT_DAILY_CACHE_PATH,
    daily_payload_search_entries,
    load_daily_payload,
)
from app.file_utils import safe_join
from app.gallery_utils import get_folder_meta, get_gallery_folders
from app.markdown_utils import get_publications


SEARCH_CACHE_NAMESPACE = "site_search"
SEARCH_CACHE_KEY = "index"


def _gallery_metadata_signature(folders: tuple[str, ...]) -> tuple:
    signature = []
    for relative_path in folders:
        try:
            album_path = safe_join(Path(UPLOAD_DIR), relative_path)
        except Exception:
            continue
        signature.append((relative_path, file_signature(album_path / "meta.json")))
    return tuple(signature)


def _build_search_entries(folders: tuple[str, ...]) -> tuple[dict, ...]:
    entries: list[dict] = []
    for publication in get_publications():
        entries.append(
            {
                "type": "Publication",
                "title": publication["title"],
                "desc": publication["venue"] or publication["authors"],
                "tags": publication["keywords"],
                "date": "",
                "url": f"/publications#{publication['slug']}",
            }
        )
    entries.extend(daily_payload_search_entries(load_daily_payload()))
    for relative_path in folders:
        try:
            album_path = safe_join(Path(UPLOAD_DIR), relative_path)
            if not album_path.exists():
                continue
            metadata = get_folder_meta(album_path)
        except Exception:
            continue
        entries.append(
            {
                "type": "Album",
                "title": metadata.get("title", album_path.name),
                "desc": metadata.get("description", ""),
                "tags": [],
                "date": metadata.get("date", ""),
                "url": f"/gallery?{urlencode({'focus': relative_path})}",
            }
        )
    return tuple(entries)


def build_search_index() -> list[dict]:
    folders = tuple(get_gallery_folders())
    signature = (
        file_signature(CONTENT_DIR / "content.md"),
        file_signature(DEFAULT_DAILY_CACHE_PATH),
        file_signature(GALLERY_CONFIG_FILE),
        _gallery_metadata_signature(folders),
    )
    entries = cache_by_signature(
        SEARCH_CACHE_KEY,
        signature,
        lambda: _build_search_entries(folders),
        namespace=SEARCH_CACHE_NAMESPACE,
    )
    return list(entries)
