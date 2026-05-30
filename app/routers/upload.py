import os
import shutil
from pathlib import Path
from typing import List, Any

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse

from app.config import (
    UPLOAD_DIR,
    limiter,
)
from app.utils import (
    safe_join, process_uploaded_image, get_folder_meta, save_folder_meta,
    get_gallery_folders, toggle_gallery_folder
)
from app.auth import require_login

router = APIRouter()

# Upload security constants
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
BLOCKED_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".sh", ".php", ".jsp", ".asp", ".aspx",
    ".py", ".pyc", ".rb", ".pl", ".cgi", ".wsf", ".vbs", ".js", ".jar",
    ".apk", ".ipa", ".deb", ".rpm", ".msi", ".com", ".scr", ".hta",
    ".html", ".htm", ".xml", ".svg", ".svgz",
}


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
    rel_path = target_path.parent.relative_to(UPLOAD_DIR)
    if str(rel_path) == ".":
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
    rel_path = str(target.relative_to(UPLOAD_DIR))
    toggle_gallery_folder(rel_path, enable)
    return JSONResponse({"detail": "Updated"})


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
    gallery_set = set(get_gallery_folders())
    
    try:
        entries = list(target_dir.iterdir())
        entries.sort(key=lambda x: (not x.is_dir(), -x.stat().st_mtime))
        
        for p in entries:
            try:
                rel_path = str(p.relative_to(UPLOAD_DIR))
            except ValueError:
                continue

            if p.is_dir():
                meta = get_folder_meta(p)
                items.append({
                    "name": p.name,
                    "type": "dir",
                    "is_gallery": rel_path in gallery_set,
                    "path": rel_path,
                    "title": meta.get("title", p.name),
                    "description": meta.get("description", ""),
                    "date": meta.get("date", ""),
                    "author": meta.get("author", "Yixun Hong")
                })
            else:
                items.append({
                    "name": p.name,
                    "type": "file",
                    "size": p.stat().st_size,
                    "url": f"/uploads/{rel_path}"
                })
    except Exception as e:
         print(f"Error listing files: {e}")
         return JSONResponse({"files": [], "error": str(e)})
            
    return JSONResponse({"files": items, "current_path": path})


@router.delete("/api/files/{path:path}")
@limiter.limit("30/minute")
def delete_file_api(request: Request, path: str) -> JSONResponse:
    require_login(request)
    target = safe_join(UPLOAD_DIR, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if target.is_dir():
         shutil.rmtree(target)
    else:
         os.remove(target)
    return JSONResponse({"detail": "Deleted"})


@router.get("/api/files/{file_path:path}")
def download_file_api(file_path: str) -> FileResponse:
    target = safe_join(UPLOAD_DIR, file_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)
