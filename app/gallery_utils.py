from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Literal, cast

from app.cache import cache_by_mtime, invalidate, invalidate_namespace
from app.config import GALLERY_CONFIG_FILE


GalleryVisibility = Literal["hidden", "public", "private"]
VISIBLE_GALLERY_STATES = {"public", "private"}

_GALLERY_CONFIG_CACHE_NAMESPACE = "gallery_config"
_GALLERY_META_CACHE_NAMESPACE = "gallery_meta"
_GALLERY_WRITE_LOCK = RLock()


def _read_json_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_gallery_config() -> dict:
    data = cache_by_mtime(
        GALLERY_CONFIG_FILE,
        lambda: _read_json_object(GALLERY_CONFIG_FILE),
        namespace=_GALLERY_CONFIG_CACHE_NAMESPACE,
    )
    return copy.deepcopy(data)


def _atomic_write_json(
    path: Path,
    payload: object,
    *,
    ensure_ascii: bool = True,
    indent: int | None = None,
) -> None:
    """Write JSON beside its destination, then atomically replace it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(
                payload,
                temporary_file,
                ensure_ascii=ensure_ascii,
                indent=indent,
            )
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _normalize_visibility(value: object) -> GalleryVisibility:
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"public", "private"}:
            return cast(GalleryVisibility, lowered)
    return "hidden"


def get_gallery_visibility_map() -> dict[str, GalleryVisibility]:
    data = _load_gallery_config()
    visibility: dict[str, GalleryVisibility] = {}

    # Backward compatibility: legacy configs stored only public folders.
    folders = data.get("folders", [])
    if isinstance(folders, list):
        for folder in folders:
            if isinstance(folder, str) and folder:
                visibility[folder] = "public"

    stored_visibility = data.get("visibility", {})
    if isinstance(stored_visibility, dict):
        for folder, state in stored_visibility.items():
            if isinstance(folder, str) and folder:
                visibility[folder] = _normalize_visibility(state)

    return visibility


def get_gallery_folders(include_private: bool = False) -> list[str]:
    allowed = {"public", "private"} if include_private else {"public"}
    return [
        folder
        for folder, visibility in get_gallery_visibility_map().items()
        if visibility in allowed
    ]


def _invalidate_gallery_dependents(path: Path) -> None:
    invalidate(path)
    # Gallery metadata contributes rendered entries to the merged News feed.
    invalidate_namespace("news")


def set_gallery_folder_visibility(
    folder_path: str,
    visibility: GalleryVisibility,
) -> None:
    visibility = _normalize_visibility(visibility)
    with _GALLERY_WRITE_LOCK:
        states = get_gallery_visibility_map()
        if visibility == "hidden":
            states.pop(folder_path, None)
        else:
            states[folder_path] = visibility

        public_folders = [folder for folder, state in states.items() if state == "public"]
        stored_visibility = {
            folder: state for folder, state in states.items() if state in VISIBLE_GALLERY_STATES
        }
        _atomic_write_json(
            GALLERY_CONFIG_FILE,
            {"folders": public_folders, "visibility": stored_visibility},
            ensure_ascii=False,
            indent=2,
        )
        _invalidate_gallery_dependents(GALLERY_CONFIG_FILE)


def toggle_gallery_folder(folder_path: str, enable: bool) -> None:
    set_gallery_folder_visibility(folder_path, "public" if enable else "hidden")


def get_folder_meta(folder_path: Path) -> dict:
    meta_file = folder_path / "meta.json"
    default = {
        "title": folder_path.name,
        "description": "",
        "date": "",
        "author": "Yixun Hong",
    }
    stored = cache_by_mtime(
        meta_file,
        lambda: _read_json_object(meta_file),
        namespace=_GALLERY_META_CACHE_NAMESPACE,
    )
    return {**default, **copy.deepcopy(stored)}


def save_folder_meta(
    folder_path: Path,
    title: str,
    description: str,
    date: str = "",
    author: str = "Yixun Hong",
) -> None:
    meta_file = folder_path / "meta.json"
    meta = {
        "title": title,
        "description": description,
        "date": date,
        "author": author,
    }
    with _GALLERY_WRITE_LOCK:
        _atomic_write_json(meta_file, meta)
        _invalidate_gallery_dependents(meta_file)
