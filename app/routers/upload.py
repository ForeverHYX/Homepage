import mimetypes
import shutil
from pathlib import Path
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from app.config import (
    UPLOAD_DIR,
    limiter,
)
from app.utils import (
    safe_join, process_uploaded_image, get_folder_meta, save_folder_meta,
    get_gallery_visibility_map, set_gallery_folder_visibility, toggle_gallery_folder
)
from app.auth import require_login
from app.gallery_thumbnail_utils import THUMBNAIL_DIR_NAME, get_gallery_thumbnail_path

router = APIRouter()

# Upload security constants
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
BLOCKED_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".sh", ".php", ".jsp", ".asp", ".aspx",
    ".py", ".pyc", ".rb", ".pl", ".cgi", ".wsf", ".vbs", ".js", ".jar",
    ".apk", ".ipa", ".deb", ".rpm", ".msi", ".com", ".scr", ".hta",
    ".html", ".htm", ".xml", ".svg", ".svgz",
}

FILE_KIND_EXTENSIONS = {
    "image": {".avif", ".bmp", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".webp"},
    "pdf": {".pdf"},
    "document": {".doc", ".docx", ".odt", ".pages", ".rtf"},
    "spreadsheet": {".csv", ".numbers", ".ods", ".xls", ".xlsx"},
    "presentation": {".key", ".odp", ".ppt", ".pptx"},
    "archive": {".7z", ".bz2", ".gz", ".rar", ".tar", ".tgz", ".xz", ".zip"},
    "audio": {".aac", ".flac", ".m4a", ".mp3", ".oga", ".ogg", ".wav"},
    "video": {".m4v", ".mov", ".mp4", ".mpeg", ".mpg", ".ogv", ".webm"},
    "code": {".c", ".cpp", ".css", ".go", ".h", ".hpp", ".java", ".js", ".json", ".md", ".rs", ".sh", ".toml", ".ts", ".yaml", ".yml"},
    "text": {".log", ".tex", ".txt"},
}

PREVIEWABLE_KINDS = {"image", "pdf", "audio", "video", "code", "text"}
PREVIEWABLE_SPREADSHEET_EXTENSIONS = {".csv"}


def _relative_upload_path(path: Path) -> str:
    return str(path.resolve().relative_to(Path(UPLOAD_DIR).resolve()))


def _upload_url(relative_path: str) -> str:
    return f"/uploads/{quote(relative_path, safe='/')}"


def _download_url(relative_path: str) -> str:
    return f"/api/files/{quote(relative_path, safe='/')}?download=true"


def _file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    for kind, extensions in FILE_KIND_EXTENSIONS.items():
        if suffix in extensions:
            return kind
    return "file"


def _file_payload(path: Path) -> dict:
    relative_path = _relative_upload_path(path)
    kind = _file_kind(path)
    is_previewable = kind in PREVIEWABLE_KINDS or path.suffix.lower() in PREVIEWABLE_SPREADSHEET_EXTENSIONS
    return {
        "name": path.name,
        "type": "file",
        "path": relative_path,
        "size": path.stat().st_size,
        "url": _upload_url(relative_path),
        "download_url": _download_url(relative_path),
        "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "file_kind": kind,
        "is_image": kind == "image",
        "is_previewable": is_previewable,
    }


def _resolve_upload_item(path: str) -> Path:
    clean_path = path.strip().lstrip("/")
    if not clean_path or clean_path == ".":
        raise HTTPException(status_code=400, detail="A file or folder path is required")
    target = safe_join(UPLOAD_DIR, clean_path)
    if target.resolve() == Path(UPLOAD_DIR).resolve():
        raise HTTPException(status_code=400, detail="The upload root cannot be modified")
    if not target.exists():
        raise HTTPException(status_code=404, detail="File or folder not found")
    return target


def _validate_new_name(new_name: str) -> str:
    clean_name = new_name.strip()
    if (
        not clean_name
        or clean_name in {".", ".."}
        or Path(clean_name).name != clean_name
        or "/" in clean_name
        or "\\" in clean_name
        or "\x00" in clean_name
    ):
        raise HTTPException(status_code=400, detail="Invalid file name")
    if Path(clean_name).suffix.lower() in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")
    return clean_name


def _prune_empty_thumbnail_parents(path: Path) -> None:
    thumbnail_root = (Path(UPLOAD_DIR) / THUMBNAIL_DIR_NAME).resolve()
    parent = path.parent
    while parent != thumbnail_root:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def _remove_thumbnail_for_file(path: Path) -> None:
    thumbnail_path = get_gallery_thumbnail_path(Path(UPLOAD_DIR).resolve(), path)
    thumbnail_path.unlink(missing_ok=True)
    _prune_empty_thumbnail_parents(thumbnail_path)


def _remove_gallery_entries(relative_path: str) -> None:
    prefix = f"{relative_path}/"
    for gallery_path in list(get_gallery_visibility_map()):
        if gallery_path == relative_path or gallery_path.startswith(prefix):
            set_gallery_folder_visibility(gallery_path, "hidden")


def _delete_upload_item(path: str) -> str:
    target = _resolve_upload_item(path)
    relative_path = _relative_upload_path(target)

    if target.is_dir():
        thumbnail_dir = Path(UPLOAD_DIR) / THUMBNAIL_DIR_NAME / relative_path
        shutil.rmtree(target)
        shutil.rmtree(thumbnail_dir, ignore_errors=True)
        _remove_gallery_entries(relative_path)
    else:
        target.unlink()
        _remove_thumbnail_for_file(target)

    return relative_path


@router.post("/api/upload")
@limiter.limit("30/minute")
async def upload_file_api(request: Request, file: UploadFile = File(...), path: str = Form("")) -> JSONResponse:
    require_login(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    # Extension blacklist check
    ext = Path(file.filename).suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")

    # Size guard (nginx should also enforce client_max_body_size)
    total_written = 0

    # Resolve path
    target_dir = UPLOAD_DIR
    if path:
        target_dir = safe_join(UPLOAD_DIR, path)
        if not target_dir.exists():
             target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename).name
    target_path = safe_join(target_dir, safe_name)

    with target_path.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024 * 5)  # 5MB chunks
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > MAX_UPLOAD_SIZE:
                f.close()
                target_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large")
            f.write(chunk)

    # Process Image (JPG -> WebP)
    final_name = process_uploaded_image(target_path)
    
    # Return relative URL
    rel_path = _relative_upload_path(target_path.parent)
    if rel_path == ".":
        url = f"/uploads/{final_name}"
    else:
        url = f"/uploads/{rel_path}/{final_name}"

    return JSONResponse({"filename": final_name, "url": url})


@router.post("/api/folder")
@limiter.limit("20/minute")
def create_folder_api(request: Request, name: str = Form(...), path: str = Form("")) -> JSONResponse:
    require_login(request)
    target_dir = UPLOAD_DIR
    if path:
        target_dir = safe_join(UPLOAD_DIR, path)
    
    final_path = safe_join(target_dir, name)
    try:
        final_path.mkdir(exist_ok=True)
    except Exception as e:
         raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse({"detail": "Created"})


@router.post("/api/folder/meta")
@limiter.limit("30/minute")
def update_folder_meta(request: Request, path: str = Form(...), title: str = Form(...), description: str = Form(...), date: str = Form(""), author: str = Form("Yixun Hong")) -> JSONResponse:
    require_login(request)
    target = safe_join(UPLOAD_DIR, path)
    if not target.exists() or not target.is_dir():
         raise HTTPException(status_code=404, detail="Folder not found")
    
    save_folder_meta(target, title, description, date, author)
    return JSONResponse({"detail": "Updated"})


@router.post("/api/gallery/toggle")
@limiter.limit("30/minute")
def toggle_gallery_api(request: Request, path: str = Form(...), enable: bool = Form(...)) -> JSONResponse:
    require_login(request)
    # Validate path exists
    target = safe_join(UPLOAD_DIR, path)
    if not target.exists() or not target.is_dir():
         raise HTTPException(status_code=404, detail="Folder not found")
    
    # Store relative path by normalized string
    rel_path = _relative_upload_path(target)
    toggle_gallery_folder(rel_path, enable)
    return JSONResponse({"detail": "Updated"})


@router.post("/api/gallery/visibility")
@limiter.limit("30/minute")
def update_gallery_visibility_api(
    request: Request,
    path: str = Form(...),
    visibility: str = Form(...),
) -> JSONResponse:
    require_login(request)
    target = safe_join(UPLOAD_DIR, path)
    if not target.exists() or not target.is_dir():
         raise HTTPException(status_code=404, detail="Folder not found")

    normalized = visibility.lower()
    if normalized not in {"hidden", "public", "private"}:
         raise HTTPException(status_code=400, detail="Invalid gallery visibility")

    rel_path = _relative_upload_path(target)
    set_gallery_folder_visibility(rel_path, normalized)  # type: ignore[arg-type]
    return JSONResponse({"detail": "Updated", "visibility": normalized})


@router.get("/api/files")
@limiter.limit("60/minute")
def list_files_api(request: Request, path: str = "") -> JSONResponse:
    require_login(request)
    
    # Secure Path Handling
    if not path or path == "/" or path == ".":
        target_dir = UPLOAD_DIR
        path = ""
    else:
        # Strip leading slashes to avoid absolute path issues
        clean_path = path.lstrip("/")
        target_dir = safe_join(UPLOAD_DIR, clean_path)
    
    if not target_dir.exists():
         # Fallback to root or return empty?
         # Check if it was a file browse attempt?
         raise HTTPException(status_code=404, detail="Path not found")

    items: List[dict] = []
    gallery_visibility = get_gallery_visibility_map()
    
    try:
        entries = list(target_dir.iterdir())
        entries.sort(key=lambda x: (not x.is_dir(), -x.stat().st_mtime))
        
        for p in entries:
            if p.name == THUMBNAIL_DIR_NAME or p.name.startswith("."):
                continue
            try:
                rel_path = _relative_upload_path(p)
            except ValueError:
                continue

            if p.is_dir():
                meta = get_folder_meta(p)
                visibility = gallery_visibility.get(rel_path, "hidden")
                items.append({
                    "name": p.name,
                    "type": "dir",
                    "is_gallery": visibility in {"public", "private"},
                    "gallery_visibility": visibility,
                    "path": rel_path,
                    "title": meta.get("title", p.name),
                    "description": meta.get("description", ""),
                    "desc": meta.get("description", ""),
                    "date": meta.get("date", ""),
                    "author": meta.get("author", "Yixun Hong")
                })
            else:
                items.append(_file_payload(p))
    except Exception as e:
         print(f"Error listing files: {e}")
         return JSONResponse({"files": [], "error": str(e)})
            
    return JSONResponse({"files": items, "current_path": path})


@router.post("/api/files/delete")
@limiter.limit("30/minute")
def delete_file_api(request: Request, path: str = Form(...)) -> JSONResponse:
    require_login(request)
    deleted_path = _delete_upload_item(path)
    return JSONResponse({"detail": "Deleted", "path": deleted_path})


@router.delete("/api/files/{path:path}")
@limiter.limit("30/minute")
def delete_file_legacy_api(request: Request, path: str) -> JSONResponse:
    """Compatibility route for older clients; new clients send paths in form data."""
    require_login(request)
    deleted_path = _delete_upload_item(path)
    return JSONResponse({"detail": "Deleted", "path": deleted_path})


@router.post("/api/files/rename")
@limiter.limit("30/minute")
def rename_file_api(
    request: Request,
    path: str = Form(...),
    new_name: str = Form(...),
) -> JSONResponse:
    require_login(request)
    target = _resolve_upload_item(path)
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Only files can be renamed")

    clean_name = _validate_new_name(new_name)
    destination = target.with_name(clean_name)
    if destination == target:
        return JSONResponse({"detail": "Unchanged", **_file_payload(target)})
    if destination.exists():
        raise HTTPException(status_code=409, detail="A file with that name already exists")

    old_thumbnail = get_gallery_thumbnail_path(Path(UPLOAD_DIR).resolve(), target)
    target.rename(destination)
    old_thumbnail.unlink(missing_ok=True)
    _prune_empty_thumbnail_parents(old_thumbnail)

    return JSONResponse({"detail": "Renamed", **_file_payload(destination)})


@router.get("/api/files/{file_path:path}")
def download_file_api(file_path: str, download: bool = False) -> FileResponse:
    target = safe_join(UPLOAD_DIR, file_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target, filename=target.name if download else None)
