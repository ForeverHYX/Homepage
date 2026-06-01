from __future__ import annotations
import json
from pathlib import Path
from typing import List
from app.config import GALLERY_CONFIG_FILE

def get_gallery_folders() -> List[str]:
    if not GALLERY_CONFIG_FILE.exists():
        return []
    try:
        data = json.loads(GALLERY_CONFIG_FILE.read_text())
        return data.get("folders", [])
    except:
        return []

def toggle_gallery_folder(folder_path: str, enable: bool):
    folders = set(get_gallery_folders())
    if enable:
        folders.add(folder_path)
    else:
        folders.discard(folder_path)
    GALLERY_CONFIG_FILE.write_text(json.dumps({"folders": list(folders)}))

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
