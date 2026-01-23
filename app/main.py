from __future__ import annotations

import os
from pathlib import Path
from typing import List

import secrets
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import markdown
from fastapi.security import HTTPBasic, HTTPBasicCredentials

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = Path(os.getenv("HOMEPAGE_CONTENT_DIR", BASE_DIR / "content")).resolve()
UPLOAD_DIR = Path(os.getenv("HOMEPAGE_UPLOAD_DIR", BASE_DIR / "uploads")).resolve()

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Foreverhyx Homepage", version="0.1.0")

security = HTTPBasic()
UPLOAD_USERNAME = os.getenv("HOMEPAGE_UPLOAD_USER", "admin")
UPLOAD_PASSWORD = os.getenv("HOMEPAGE_UPLOAD_PASS", "changeme")

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


def require_upload_auth(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    is_user = secrets.compare_digest(credentials.username, UPLOAD_USERNAME)
    is_pass = secrets.compare_digest(credentials.password, UPLOAD_PASSWORD)
    if not (is_user and is_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


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


@app.get("/upload", response_class=HTMLResponse)
def upload_page(_: None = Depends(require_upload_auth)) -> str:
    return """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Upload | foreverhyx</title>
  <style>
    :root { color-scheme: light dark; }
    body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 0; background: #0b0b0c; color: #e5e7eb; }
    header { padding: 32px 16px; border-bottom: 1px solid #1f2937; background: #0f1113; }
    main { max-width: 980px; margin: 0 auto; padding: 24px 16px 64px; }
    h1 { font-size: 28px; margin: 0 0 8px; }
    p { color: #9ca3af; margin: 0 0 24px; }
    .panel { background: #111315; border: 1px solid #1f2937; border-radius: 12px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
    .row { display: grid; gap: 16px; grid-template-columns: 1fr; }
    @media (min-width: 860px) { .row { grid-template-columns: 1.2fr 1.8fr; } }
    .drop { border: 1px dashed #374151; border-radius: 12px; padding: 24px; text-align: center; color: #cbd5f5; background: #0f1113; }
    .drop.drag { border-color: #9ca3af; background: #12161a; }
    input[type=file] { display: none; }
    button { background: #f9fafb; color: #0b0b0c; border: none; padding: 10px 16px; border-radius: 10px; cursor: pointer; font-weight: 600; }
    button.secondary { background: transparent; color: #d1d5db; border: 1px solid #374151; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    ul { list-style: none; padding: 0; margin: 0; }
    li { padding: 12px 10px; border-bottom: 1px solid #1f2937; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 320px; }
    .meta { color: #6b7280; font-size: 12px; }
    .toast { position: fixed; right: 16px; bottom: 16px; background: #111315; border: 1px solid #1f2937; padding: 10px 14px; border-radius: 10px; color: #e5e7eb; opacity: 0; transform: translateY(8px); transition: all .2s ease; }
    .toast.show { opacity: 1; transform: translateY(0); }
  </style>
</head>
<body>
  <header>
    <main>
      <h1>Upload Center</h1>
      <p>Minimal, Markdown-inspired styling. Private access only.</p>
    </main>
  </header>
  <main>
    <div class=\"row\">
      <section class=\"panel\">
        <div id=\"drop\" class=\"drop\">
          <p>Drag & drop files here</p>
          <p class=\"meta\">or</p>
          <label>
            <button id=\"pickBtn\" class=\"secondary\">Choose files</button>
            <input id=\"fileInput\" type=\"file\" multiple />
          </label>
        </div>
        <div style=\"display:flex; gap:12px; margin-top:16px;\">
          <button id=\"uploadBtn\" disabled>Upload</button>
          <button id=\"refreshBtn\" class=\"secondary\">Refresh</button>
        </div>
        <div id=\"status\" class=\"meta\" style=\"margin-top:12px;\"></div>
      </section>
      <section class=\"panel\">
        <h2 style=\"margin-top:0;\">Files</h2>
        <ul id=\"fileList\"></ul>
      </section>
    </div>
  </main>
  <div id=\"toast\" class=\"toast\">Copied</div>
  <script>
    const drop = document.getElementById('drop');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const fileList = document.getElementById('fileList');
    const statusEl = document.getElementById('status');
    const toast = document.getElementById('toast');
    let queue = [];

    const fmtSize = (n) => {
      if (n < 1024) return n + ' B';
      if (n < 1024 * 1024) return (n/1024).toFixed(1) + ' KB';
      return (n/1024/1024).toFixed(1) + ' MB';
    };

    const showToast = (msg) => {
      toast.textContent = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 1400);
    };

    const updateQueue = (files) => {
      queue = [...queue, ...files];
      uploadBtn.disabled = queue.length === 0;
      statusEl.textContent = queue.length ? `${queue.length} file(s) ready` : '';
    };

    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('drag'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
    drop.addEventListener('drop', (e) => {
      e.preventDefault();
      drop.classList.remove('drag');
      updateQueue([...e.dataTransfer.files]);
    });

    document.getElementById('pickBtn').addEventListener('click', (e) => {
      e.preventDefault();
      fileInput.click();
    });
    fileInput.addEventListener('change', (e) => updateQueue([...e.target.files]));

    async function fetchFiles() {
      const res = await fetch('/api/files');
      const data = await res.json();
      fileList.innerHTML = '';
      data.files.forEach((f) => {
        const li = document.createElement('li');
        const left = document.createElement('div');
        left.innerHTML = `<div class=\"name\">${f.name}</div><div class=\"meta\">${fmtSize(f.size)}</div>`;
        const btn = document.createElement('button');
        btn.textContent = 'Copy URL';
        btn.className = 'secondary';
        btn.addEventListener('click', async () => {
          await navigator.clipboard.writeText(location.origin + f.url);
          showToast('Copied URL');
        });
        li.appendChild(left);
        li.appendChild(btn);
        fileList.appendChild(li);
      });
    }

    async function uploadAll() {
      if (!queue.length) return;
      uploadBtn.disabled = true;
      statusEl.textContent = 'Uploading...';
      for (const file of queue) {
        const form = new FormData();
        form.append('file', file);
        const res = await fetch('/api/upload', { method: 'POST', body: form });
        if (!res.ok) {
          statusEl.textContent = 'Upload failed';
          return;
        }
      }
      queue = [];
      statusEl.textContent = 'Upload completed';
      await fetchFiles();
    }

    uploadBtn.addEventListener('click', uploadAll);
    refreshBtn.addEventListener('click', fetchFiles);
    fetchFiles();
  </script>
</body>
</html>"""


@app.post("/api/upload")
async def upload_file(_: None = Depends(require_upload_auth), file: UploadFile = File(...)) -> JSONResponse:
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
def list_files(_: None = Depends(require_upload_auth)) -> JSONResponse:
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
