from __future__ import annotations

import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import markdown

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = Path(os.getenv("HOMEPAGE_CONTENT_DIR", BASE_DIR / "content")).resolve()
UPLOAD_DIR = Path(os.getenv("HOMEPAGE_UPLOAD_DIR", BASE_DIR / "uploads")).resolve()

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Foreverhyx Homepage", version="0.1.0")

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


def safe_join(base: Path, target: str) -> Path:
    candidate = (base / target).resolve()
    if base not in candidate.parents and candidate != base:
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate


def render_markdown(md_path: Path) -> str:
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="Markdown not found")
    text = md_path.read_text(encoding="utf-8")
    return markdown.markdown(text, extensions=["fenced_code", "tables", "toc"])


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html_body = render_markdown(CONTENT_DIR / "index.md")
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>foreverhyx</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; }}
    header {{ padding: 32px 16px; border-bottom: 1px solid #e5e7eb; }}
    main {{ max-width: 860px; margin: 0 auto; padding: 24px 16px 64px; line-height: 1.7; }}
    h1, h2, h3 {{ line-height: 1.25; }}
    pre {{ background: #0f172a; color: #e2e8f0; padding: 16px; border-radius: 8px; overflow-x: auto; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace; }}
    a {{ color: #3b82f6; }}
    footer {{ padding: 24px 16px; text-align: center; color: #6b7280; border-top: 1px solid #e5e7eb; }}
  </style>
</head>
<body>
  <header>
    <main>
      <h1>foreverhyx.top</h1>
      <p>基于 Markdown 的个人主页</p>
    </main>
  </header>
  <main>
    {html_body}
  </main>
  <footer>
    <small>Powered by FastAPI + Markdown</small>
  </footer>
</body>
</html>"""


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    safe_name = Path(file.filename).name
    target_path = safe_join(UPLOAD_DIR, safe_name)

    with target_path.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    return JSONResponse({"filename": safe_name, "url": f"/uploads/{safe_name}"})


@app.get("/api/files")
def list_files() -> JSONResponse:
    items: List[dict] = []
    for path in sorted(UPLOAD_DIR.iterdir()):
        if path.is_file():
            items.append({"name": path.name, "size": path.stat().st_size, "url": f"/uploads/{path.name}"})
    return JSONResponse({"files": items})


@app.get("/api/files/{file_path:path}")
def download_file(file_path: str) -> FileResponse:
    target = safe_join(UPLOAD_DIR, file_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)
