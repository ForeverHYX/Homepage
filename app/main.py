from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import List, Optional, Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import markdown

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = Path(os.getenv("HOMEPAGE_CONTENT_DIR", BASE_DIR / "content")).resolve()
UPLOAD_DIR = Path(os.getenv("HOMEPAGE_UPLOAD_DIR", BASE_DIR / "uploads")).resolve()

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Foreverhyx Homepage", version="0.2.0")

# Security defaults (safe for git, overriden by env vars in prod)
UPLOAD_USERNAME = os.getenv("HOMEPAGE_UPLOAD_USER", "admin")
UPLOAD_PASSWORD = os.getenv("HOMEPAGE_UPLOAD_PASS", "changeme")
SESSION_KEY = "session_token"

# Simple in-memory session store (suitable for single-instance, single-user)
VALID_SESSIONS = set()

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# --- Utilities ---

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


# --- Auth Logic ---

def get_current_user(request: Request) -> bool:
    token = request.cookies.get(SESSION_KEY)
    if token and token in VALID_SESSIONS:
        return True
    return False


def require_login(request: Request) -> None:
    if not get_current_user(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# --- Templates & Assets ---

ICON_USER = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>"""
ICON_UPLOAD = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>"""
ICON_FILE = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>"""
ICON_TRASH = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>"""
ICON_COPY = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>"""

STYLES = """
    :root { 
        --bg: #f8fafc; --text: #0f172a; --primary: #3b82f6; --primary-hover: #2563eb; 
        --surface: #ffffff; --border: #e2e8f0; --muted: #64748b; 
        --radius: 12px; --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; }
    header { background: var(--surface); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 10; }
    .container { max-width: 1024px; margin: 0 auto; padding: 0 20px; }
    .nav { display: flex; align-items: center; justify-content: space-between; height: 64px; }
    .brand { font-weight: 700; font-size: 18px; text-decoration: none; color: var(--text); display: flex; align-items: center; gap: 8px; }
    .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 8px 16px; border-radius: 8px; font-weight: 500; cursor: pointer; transition: all .2s; font-size: 14px; text-decoration: none; border: 1px solid transparent; }
    .btn-primary { background: var(--primary); color: white; }
    .btn-primary:hover { background: var(--primary-hover); transform: translateY(-1px); }
    .btn-ghost { background: transparent; color: var(--muted); }
    .btn-ghost:hover { background: #f1f5f9; color: #334155; }
    .btn-danger { color: #ef4444; background: #fee2e2; }
    .btn-danger:hover { background: #fecaca; }
    .card { background: var(--surface); border-radius: var(--radius); border: 1px solid var(--border); padding: 24px; box-shadow: var(--shadow); }
    
    /* Typography for Markdown (Home) */
    .prose { max-width: 720px; margin: 40px auto; line-height: 1.75; }
    .prose h1 { font-size: 2.25rem; font-weight: 800; letter-spacing: -0.025em; margin-bottom: 2rem; color: #1e293b; }
    .prose h2 { font-size: 1.5rem; font-weight: 700; margin-top: 2.5rem; margin-bottom: 1rem; color: #1e293b; }
    .prose h3 { font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 0.75rem; color: #334155; }
    .prose p { margin-bottom: 1.25rem; color: #334155; }
    .prose a { color: var(--primary); text-decoration: none; font-weight: 500; border-bottom: 1px solid transparent; transition: border .2s; }
    .prose a:hover { border-bottom-color: var(--primary); }
    .prose ul, .prose ol { margin-bottom: 1.25rem; padding-left: 1.5rem; color: #334155; }
    .prose li { margin-bottom: 0.5rem; }
    .prose code { background: #f1f5f9; padding: 0.2rem 0.4rem; border-radius: 0.25rem; font-size: 0.875em; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: #0f172a; }
    .prose pre { background: #1e293b; color: #e2e8f0; padding: 1rem; border-radius: 8px; overflow-x: auto; margin: 1.5rem 0; }
    .prose pre code { background: transparent; padding: 0; color: inherit; }
    .prose blockquote { border-left: 4px solid var(--primary); padding-left: 1rem; color: var(--muted); font-style: italic; margin: 1.5rem 0; }
    
    /* Upload UI Specifics */
    .upload-grid { display: grid; gap: 24px; grid-template-columns: 1fr; margin-top: 32px; }
    @media (min-width: 768px) { .upload-grid { grid-template-columns: 320px 1fr; } }
    .drop-zone { border: 2px dashed var(--border); border-radius: var(--radius); padding: 40px 24px; text-align: center; transition: all .2s; cursor: pointer; background: #f8fafc; }
    .drop-zone:hover, .drop-zone.drag { border-color: var(--primary); background: #eff6ff; }
    .file-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }
    .file-item { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #f8fafc; border-radius: 8px; border: 1px solid var(--border); transition: all .2s; }
    .file-item:hover { border-color: #cbd5e1; transform: translateX(2px); }
    .file-info { display: flex; align-items: center; gap: 12px; overflow: hidden; }
    .file-name { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .file-meta { font-size: 12px; color: var(--muted); }
    .actions { display: flex; gap: 8px; }
    .toast { position: fixed; bottom: 24px; right: 24px; background: #1e293b; color: white; padding: 12px 20px; border-radius: 8px; font-weight: 500; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1); opacity: 0; transform: translateY(10px); transition: all .3s; pointer-events: none; }
    .toast.show { opacity: 1; transform: translateY(0); }
    
    /* Login Page */
    .login-box { max-width: 400px; margin: 80px auto; }
    .form-group { margin-bottom: 20px; }
    .form-label { display: block; margin-bottom: 8px; font-weight: 500; font-size: 14px; }
    .form-input { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 16px; background: var(--surface); box-sizing: border-box; transition: border .2s; }
    .form-input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
"""

TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>{styles}</style>
</head>
<body>
  <header>
    <div class="container nav">
      <a href="/" class="brand">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        foreverhyx
      </a>
      <div style="display:flex; gap:16px;">
        <a href="/upload" class="btn btn-ghost">Upload</a>
      </div>
    </div>
  </header>
  {content}
  <footer style="margin-top: 64px; border-top: 1px solid var(--border); padding: 48px 0; background: white;">
    <div class="container" style="text-align: center; color: var(--muted);">
      <p>&copy; 2026 Foreverhyx. Powered by FastAPI.</p>
    </div>
  </footer>
</body>
</html>"""


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html_body = render_markdown(CONTENT_DIR / "index.md")
    content = f"""<div class="container prose">{html_body}</div>"""
    return TEMPLATE.format(title="foreverhyx.top", styles=STYLES, content=content)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> Any:
    if get_current_user(request):
        return RedirectResponse("/upload")
    
    content = f"""
    <div class="container">
      <div class="card login-box">
        <h1 style="margin: 0 0 8px;">Welcome Back</h1>
        <p style="color: var(--muted); margin: 0 0 24px;">Please sign in to access the upload center.</p>
        <form action="/login" method="post">
          <div class="form-group">
            <label class="form-label">Username</label>
            <input name="username" class="form-input" required autofocus />
          </div>
          <div class="form-group">
            <label class="form-label">Password</label>
            <input type="password" name="password" class="form-input" required />
          </div>
          <button type="submit" class="btn btn-primary" style="width: 100%;">Sign In</button>
        </form>
      </div>
    </div>
    """
    return TEMPLATE.format(title="Login | foreverhyx", styles=STYLES, content=content)


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)) -> Any:
    if (
        secrets.compare_digest(username, UPLOAD_USERNAME) and 
        secrets.compare_digest(password, UPLOAD_PASSWORD)
    ):
        token = secrets.token_urlsafe(32)
        VALID_SESSIONS.add(token)
        response = RedirectResponse(url="/upload", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key=SESSION_KEY, value=token, httponly=True, max_age=86400)
        return response
    
    return HTMLResponse(
        content="<script>alert('Invalid credentials'); history.back();</script>", 
        status_code=status.HTTP_401_UNAUTHORIZED
    )


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request) -> Any:
    if not get_current_user(request):
        return RedirectResponse("/login")

    content = f"""
    <div class="container upload-grid">
      <section>
        <div class="card" style="position: sticky; top: 88px;">
          <h2 style="margin-top:0; font-size:18px;">Upload Files</h2>
          <div id="drop" class="drop-zone">
            <div style="color: var(--primary); margin-bottom: 12px;">{ICON_UPLOAD}</div>
            <p style="margin:0; font-weight:500;">Click or Drag files</p>
            <p style="font-size:12px; color:var(--muted); margin:4px 0 0;">Max 100MB per file</p>
            <input id="fileInput" type="file" multiple />
          </div>
          <div id="queue" style="margin-top: 16px; font-size: 14px; color: var(--muted);"></div>
          <button id="uploadBtn" class="btn btn-primary" style="width: 100%; margin-top: 16px;" disabled>Start Upload</button>
        </div>
      </section>
      
      <section>
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px;">
            <h2 style="margin:0; font-size:18px;">Your Files</h2>
            <button id="refreshBtn" class="btn btn-ghost" style="padding:4px 8px; font-size:12px;">Refresh</button>
          </div>
          <ul id="fileList" class="file-list"></ul>
          <div id="emptyState" style="text-align: center; padding: 40px; color: var(--muted); display: none;">
            No files uploaded yet.
          </div>
        </div>
      </section>
    </div>

    <div id="toast" class="toast">Action Completed</div>

    <script>
      const drop = document.getElementById('drop');
      const fileInput = document.getElementById('fileInput');
      const uploadBtn = document.getElementById('uploadBtn');
      const queueEl = document.getElementById('queue');
      const fileList = document.getElementById('fileList');
      const toast = document.getElementById('toast');
      let queue = [];

      const showToast = (msg) => {{
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
      }};

      const fmtSize = (n) => {{
        if (n < 1024) return n + ' B';
        if (n < 1024 * 1024) return (n/1024).toFixed(1) + ' KB';
        return (n/1024/1024).toFixed(1) + ' MB';
      }};

      const updateQueue = (files) => {{
        queue = [...queue, ...files];
        uploadBtn.disabled = queue.length === 0;
        queueEl.textContent = queue.length ? `${{queue.length}} file(s) selected` : '';
      }};

      // Drag & Drop
      drop.addEventListener('click', () => fileInput.click());
      drop.addEventListener('dragover', (e) => {{ e.preventDefault(); drop.classList.add('drag'); }});
      drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
      drop.addEventListener('drop', (e) => {{
        e.preventDefault();
        drop.classList.remove('drag');
        updateQueue([...e.dataTransfer.files]);
      }});
      fileInput.addEventListener('change', (e) => updateQueue([...e.target.files]));

      // File List
      async function fetchFiles() {{
        const res = await fetch('/api/files');
        if (res.status === 401) {{ location.href = '/login'; return; }}
        const data = await res.json();
        
        fileList.innerHTML = '';
        if (data.files.length === 0) {{
          document.getElementById('emptyState').style.display = 'block';
          return;
        }}
        document.getElementById('emptyState').style.display = 'none';

        data.files.forEach(f => {{
          const li = document.createElement('li');
          li.className = 'file-item';
          li.innerHTML = `
            <div class="file-info">
              <div style="color:var(--primary);">${ICON_FILE}</div>
              <div style="min-width:0;">
                <div class="file-name">${{f.name}}</div>
                <div class="file-meta">${{fmtSize(f.size)}}</div>
              </div>
            </div>
            <div class="actions">
              <button class="btn btn-ghost" title="Copy URL" onclick="copyUrl('${{f.url}}')">
                ${ICON_COPY}
              </button>
              <button class="btn btn-ghost btn-danger" title="Delete" onclick="deleteFile('${{f.name}}')">
                ${ICON_TRASH}
              </button>
            </div>
          `;
          fileList.appendChild(li);
        }});
      }}

      // Actions
      window.copyUrl = async (url) => {{
        await navigator.clipboard.writeText(location.origin + url);
        showToast('Link copied to clipboard');
      }};

      window.deleteFile = async (filename) => {{
        if (!confirm(`Delete ${{filename}}?`)) return;
        const res = await fetch(`/api/files/${{filename}}`, {{ method: 'DELETE' }});
        if (res.ok) {{
          showToast('File deleted');
          fetchFiles();
        }} else {{
          alert('Delete failed');
        }}
      }};

      uploadBtn.addEventListener('click', async () => {{
        if (!queue.length) return;
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading...';
        
        for (const file of queue) {{
          const form = new FormData();
          form.append('file', file);
          await fetch('/api/upload', {{ method: 'POST', body: form }});
        }}
        
        queue = [];
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Start Upload';
        queueEl.textContent = '';
        showToast('All files uploaded');
        fetchFiles();
      }});

      document.getElementById('refreshBtn').addEventListener('click', fetchFiles);
      fetchFiles();
    </script>
    """
    return TEMPLATE.format(title="Upload | foreverhyx", styles=STYLES, content=content)


@app.post("/api/upload")
async def upload_file_api(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    require_login(request)
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
def list_files_api(request: Request) -> JSONResponse:
    require_login(request)
    items: List[dict] = []
    for path in sorted(UPLOAD_DIR.iterdir()):
        if path.is_file():
            items.append({"name": path.name, "size": path.stat().st_size, "url": f"/uploads/{path.name}"})
    return JSONResponse({"files": items})


@app.delete("/api/files/{filename}")
def delete_file_api(request: Request, filename: str) -> JSONResponse:
    require_login(request)
    target = safe_join(UPLOAD_DIR, filename)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(target)
    return JSONResponse({"detail": "Deleted"})


@app.get("/api/files/{file_path:path}")
def download_file_api(file_path: str) -> FileResponse:
    target = safe_join(UPLOAD_DIR, file_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)
