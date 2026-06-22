from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Literal
from app.config import GALLERY_CONFIG_FILE

GalleryVisibility = Literal["hidden", "public", "private"]
VISIBLE_GALLERY_STATES = {"public", "private"}


def _load_gallery_config() -> dict:
    if not GALLERY_CONFIG_FILE.exists():
        return {}
    try:
        data = json.loads(GALLERY_CONFIG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _normalize_visibility(value: object) -> GalleryVisibility:
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"public", "private"}:
            return lowered  # type: ignore[return-value]
    return "hidden"


def get_gallery_visibility_map() -> Dict[str, GalleryVisibility]:
    data = _load_gallery_config()
    visibility: Dict[str, GalleryVisibility] = {}

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


def get_gallery_folders(include_private: bool = False) -> List[str]:
    allowed = {"public", "private"} if include_private else {"public"}
    return [
        folder
        for folder, visibility in get_gallery_visibility_map().items()
        if visibility in allowed
    ]


def set_gallery_folder_visibility(folder_path: str, visibility: GalleryVisibility) -> None:
    visibility = _normalize_visibility(visibility)
    states = get_gallery_visibility_map()
    if visibility == "hidden":
        states.pop(folder_path, None)
    else:
        states[folder_path] = visibility

    public_folders = [folder for folder, state in states.items() if state == "public"]
    stored_visibility = {
        folder: state
        for folder, state in states.items()
        if state in VISIBLE_GALLERY_STATES
    }
    GALLERY_CONFIG_FILE.write_text(
        json.dumps(
            {"folders": public_folders, "visibility": stored_visibility},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

def toggle_gallery_folder(folder_path: str, enable: bool):
    set_gallery_folder_visibility(folder_path, "public" if enable else "hidden")

def get_folder_meta(folder_path: Path) -> dict:
    meta_file = folder_path / "meta.json"
    default = {"title": folder_path.name, "description": "", "date": "", "author": "Yixun Hong"}
    if meta_file.exists():
        try:
            stored = json.loads(meta_file.read_text())
            return {**default, **stored}
        except:
            pass
    return default

def save_folder_meta(folder_path: Path, title: str, description: str, date: str = "", author: str = "Yixun Hong"):
    meta = {"title": title, "description": description, "date": date, "author": author}
    (folder_path / "meta.json").write_text(json.dumps(meta))
