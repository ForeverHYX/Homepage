from __future__ import annotations

import os
import secrets
import re
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

app = FastAPI(title="Foreverhyx Homepage", version="0.3.0")

# Security
UPLOAD_USERNAME = os.getenv("HOMEPAGE_UPLOAD_USER", "admin")
UPLOAD_PASSWORD = os.getenv("HOMEPAGE_UPLOAD_PASS", "changeme")
SESSION_KEY = "session_token"
VALID_SESSIONS = set()

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# --- Utilities ---

def safe_join(base: Path, target: str) -> Path:
    candidate = (base / target).resolve()
    if base not in candidate.parents and candidate != base:
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate


def render_markdown_file(filename: str) -> str:
    path = CONTENT_DIR / filename
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
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


# --- Template Assets ---

ICON_USER = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>"""
ICON_UPLOAD_CLOUD = """<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>"""
ICON_FILE = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>"""
ICON_TRASH = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>"""
ICON_COPY = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>"""
ICON_MAIL = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>"""
ICON_GITHUB = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>"""
ICON_MAP = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>"""

STYLES = """
    :root { 
        --bg: #f8fafc; --text: #0f172a; --primary: #3b82f6; --primary-hover: #2563eb; 
        --surface: #ffffff; --border: #e2e8f0; --muted: #64748b; 
        --radius: 16px; --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    }
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; }
    
    /* Layout */
    .container { max-width: 1024px; margin: 0 auto; padding: 0 24px; }
    header { background: var(--surface); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 10; margin-bottom: 40px; }
    .nav { display: flex; align-items: center; justify-content: space-between; height: 64px; }
    .brand { font-weight: 800; font-size: 20px; text-decoration: none; color: var(--text); display: flex; align-items: center; gap: 8px; }
    
    .main-grid { display: grid; gap: 40px; grid-template-columns: 1fr; }
    @media (min-width: 800px) { .main-grid { grid-template-columns: 280px 1fr; } }
    
    /* Sidebar */
    .sidebar { display: flex; flex-direction: column; gap: 24px; }
    .profile-card { background: var(--surface); padding: 32px 24px; border-radius: var(--radius); border: 1px solid var(--border); box-shadow: var(--shadow); text-align: center; }
    .avatar { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; margin-bottom: 16px; border: 4px solid #eff6ff; }
    .contact-links { display: flex; justify-content: center; gap: 16px; margin: 20px 0; }
    .contact-icon { color: var(--muted); transition: all .2s; padding: 8px; border-radius: 8px; background: #f1f5f9; display: inline-flex; }
    .contact-icon:hover { color: var(--primary); background: #eff6ff; transform: translateY(-2px); }
    .location { display: flex; items-align: center; justify-content: center; gap: 6px; color: var(--muted); font-size: 14px; margin-top: 16px; }

    /* Content Area */
    .content-area { background: var(--surface); padding: 40px; border-radius: var(--radius); border: 1px solid var(--border); box-shadow: var(--shadow); min-height: 500px; }
    .prose { max-width: 100%; line-height: 1.75; }
    .prose h1 { font-size: 2.25rem; font-weight: 800; letter-spacing: -0.025em; margin-bottom: 1.5rem; color: #1e293b; border-bottom: 2px solid #eff6ff; padding-bottom: 16px; }
    .prose h2 { font-size: 1.5rem; font-weight: 700; margin-top: 2.5rem; margin-bottom: 1rem; color: #1e293b; }
    .prose p { margin-bottom: 1.25rem; color: #334155; font-size: 16px; }
    .prose a { color: var(--primary); text-decoration: none; font-weight: 500; border-bottom: 1px solid transparent; transition: border .2s; }
    .prose a:hover { border-bottom-color: var(--primary); }
    .prose li { margin-bottom: 0.5rem; color: #334155; }
    
    /* Upload UI */
    .upload-grid { display: grid; gap: 32px; grid-template-columns: 1fr; margin-top: 32px; }
    @media (min-width: 860px) { .upload-grid { grid-template-columns: 320px 1fr; } }
    
    .drop-zone { border: 2px dashed var(--border); border-radius: var(--radius); padding: 40px 24px; text-align: center; transition: all .2s; cursor: pointer; background: #f8fafc; position: relative; overflow: hidden; }
    .drop-zone:hover, .drop-zone.drag { border-color: var(--primary); background: #eff6ff; }
    .drop-zone input { position: absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor: pointer; }
    
    .file-item { display: flex; align-items: center; justify-content: space-between; padding: 16px; background: white; border-radius: 12px; border: 1px solid var(--border); transition: all .2s; margin-bottom: 12px; }
    .file-item:hover { border-color: #cbd5e1; transform: translateY(-1px); box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05); }
    .file-preview { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: var(--muted); flex-shrink: 0; }
    
    /* Components */
    .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 20px; border-radius: 10px; font-weight: 600; cursor: pointer; transition: all .2s; font-size: 14px; text-decoration: none; border: none; }
    .btn-primary { background: var(--primary); color: white; width: 100%; }
    .btn-primary:hover { background: var(--primary-hover); transform: translateY(-1px); }
    .btn-primary:active { transform: translateY(0); }
    .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
    
    .action-btn { background: transparent; border: none; padding: 8px; border-radius: 8px; cursor: pointer; color: var(--muted); transition: all .2s; display: inline-flex; }
    .action-btn:hover { background: #f1f5f9; color: var(--text); }
    .action-btn.danger:hover { background: #fee2e2; color: #ef4444; }
    
    .toast { position: fixed; bottom: 32px; right: 32px; background: #1e293b; color: white; padding: 14px 24px; border-radius: 12px; font-weight: 500; box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1); opacity: 0; transform: translateY(20px); transition: all .3s; pointer-events: none; z-index: 100; }
    .toast.show { opacity: 1; transform: translateY(0); }
"""

TEMPLATE_BASE = """<!doctype html>
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
        <span>foreverhyx</span>
      </a>
      <div style="display:flex; gap:20px; font-weight:500;">
        <a href="/" style="text-decoration:none; color:var(--text);">Home</a>
        <a href="/upload" style="text-decoration:none; color:var(--text);">Upload</a>
      </div>
    </div>
  </header>
  {content}
  <script>{script}</script>
</body>
</html>"""


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    # Read Markdown contents
    nav_html = render_markdown_file("nav.md")
    content_html = render_markdown_file("content.md")
    # Parse about.md manually to extract location and avatar logic roughly
    # In a real app we might use frontmatter, but here we regex or simple parsing
    about_text = (CONTENT_DIR / "about.md").read_text(encoding="utf-8") if (CONTENT_DIR / "about.md").exists() else ""
    
    # Simple extraction for demo purposes (you can edit about.md to change these)
    # Looking for lines like "- [Email](...)"
    
    email_link = "#"
    github_link = "#"
    location = "Earth"
    
    if "mailto:" in about_text:
        match = re.search(r'\((mailto:[^)]+)\)', about_text)
        if match: email_link = match.group(1)
        
    if "github.com" in about_text:
        match = re.search(r'\((https://github[^)]+)\)', about_text)
        if match: github_link = match.group(1)
        
    if "Location" in about_text:
        # Get the line after "## Location"
        parts = about_text.split("## Location")
        if len(parts) > 1:
            location = parts[1].strip().split("\n")[0]

    avatar_url = "/uploads/avatar.png"

    page_content = f"""
    <div class="container main-grid">
      <aside class="sidebar">
        <div class="profile-card">
          <img src="{avatar_url}" class="avatar" alt="Avatar" onerror="this.src='https://ui-avatars.com/api/?name=F&background=3b82f6&color=fff&size=128'" />
          <h2 style="margin:0; font-size:24px;">Foreverhyx</h2>
          <p style="color:var(--muted); margin:8px 0 0;">Full Stack Developer</p>
          
          <div class="contact-links">
            <a href="{email_link}" class="contact-icon" title="Email">{ICON_MAIL}</a>
            <a href="{github_link}" class="contact-icon" target="_blank" title="GitHub">{ICON_GITHUB}</a>
          </div>
          
          <div class="location">
            {ICON_MAP} <span>{location}</span>
          </div>
        </div>
      </aside>
      
      <main class="content-area">
        <div class="prose">
          {content_html}
        </div>
      </main>
    </div>
    """
    return TEMPLATE_BASE.format(title="Home | foreverhyx", styles=STYLES, content=page_content, script="")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> Any:
    if get_current_user(request):
        return RedirectResponse("/upload")
    
    content = f"""
    <div class="container" style="display:flex; justify-content:center; padding-top:80px;">
      <div style="background:white; padding:40px; border-radius:16px; width:100%; max-width:400px; border:1px solid var(--border); box-shadow:var(--shadow);">
        <h1 style="margin:0 0 8px;">Welcome Back</h1>
        <p style="color:var(--muted); margin:0 0 32px;">Sign in to manage your files</p>
        <form action="/login" method="post">
          <div style="margin-bottom:20px;">
            <label style="display:block; margin-bottom:8px; font-weight:500;">Username</label>
            <input name="username" required autofocus style="width:100%; padding:12px; border:1px solid var(--border); border-radius:8px; font-size:16px;" />
          </div>
          <div style="margin-bottom:32px;">
            <label style="display:block; margin-bottom:8px; font-weight:500;">Password</label>
            <input type="password" name="password" required style="width:100%; padding:12px; border:1px solid var(--border); border-radius:8px; font-size:16px;" />
          </div>
          <button type="submit" class="btn btn-primary">Sign In</button>
        </form>
      </div>
    </div>
    """
    return TEMPLATE_BASE.format(title="Login | foreverhyx", styles=STYLES, content=content, script="")


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
        <div style="background:white; padding:24px; border-radius:16px; border:1px solid var(--border); position:sticky; top:100px;">
          <h2 style="margin-top:0; font-size:18px;">Upload Manager</h2>
          <div id="drop" class="drop-zone">
            <div style="color:var(--primary); margin-bottom:16px;">{ICON_UPLOAD_CLOUD}</div>
            <p style="margin:0; font-weight:600; color:var(--text);">Click or Drag files</p>
            <p style="font-size:13px; color:var(--muted); margin:4px 0 0;">Up to 100MB per file</p>
            <input id="fileInput" type="file" multiple />
          </div>
          <div id="queue-status" style="margin-top:16px; font-size:14px; text-align:center; color:var(--muted);"></div>
          <button id="uploadBtn" class="btn btn-primary" style="margin-top:16px;" disabled>Start Upload</button>
        </div>
      </section>
      
      <section>
        <div style="background:white; padding:32px; border-radius:16px; border:1px solid var(--border); min-height:400px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px;">
            <h2 style="margin:0; font-size:20px;">Your Files</h2>
            <button id="refreshBtn" class="action-btn">Refresh</button>
          </div>
          <div id="fileList"></div>
          <div id="emptyState" style="text-align:center; padding:60px 0; color:var(--muted); display:none;">
            <div style="opacity:0.5; margin-bottom:16px;">{ICON_FILE}</div>
            No files uploaded yet
          </div>
        </div>
      </section>
    </div>
    <div id="toast" class="toast">Action Completed</div>
    """

    script = f"""
      const drop = document.getElementById('drop');
      const fileInput = document.getElementById('fileInput');
      const uploadBtn = document.getElementById('uploadBtn');
      const queueEl = document.getElementById('queue-status');
      const fileList = document.getElementById('fileList');
      const toast = document.getElementById('toast');
      let queue = [];

      function getIcon(filename) {{
        const ext = filename.split('.').pop().toLowerCase();
        if (['jpg','jpeg','png','gif','webp'].includes(ext)) return 'img';
        return 'file';
      }}

      function showToast(msg) {{
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
      }}

      function updateQueue(files) {{
        queue = [...queue, ...files];
        uploadBtn.disabled = queue.length === 0;
        queueEl.textContent = queue.length ? `${{queue.length}} file(s) ready` : '';
      }}

      drop.addEventListener('dragover', (e) => {{ e.preventDefault(); drop.classList.add('drag'); }});
      drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
      drop.addEventListener('drop', (e) => {{
        e.preventDefault();
        drop.classList.remove('drag');
        updateQueue([...e.dataTransfer.files]);
      }});
      fileInput.addEventListener('change', (e) => updateQueue([...e.target.files]));

      async function fetchFiles() {{
         const res = await fetch('/api/files');
         if (res.status === 401) return location.href = '/login';
         const data = await res.json();
         
         fileList.innerHTML = '';
         if (data.files.length === 0) {{
           document.getElementById('emptyState').style.display = 'block';
           return;
         }}
         document.getElementById('emptyState').style.display = 'none';

         data.files.forEach(f => {{
           const isImg = getIcon(f.name) === 'img';
           const bg = isImg ? `url(${{f.url}})` : 'none';
           const iconHtml = isImg ? '' : `{ICON_FILE}`;
           
           const div = document.createElement('div');
           div.className = 'file-item';
           div.innerHTML = `
             <div style="display:flex; align-items:center; gap:16px; overflow:hidden;">
               <div class="file-preview" style="background-image:${{bg}}; background-size:cover; background-position:center;">
                 ${{iconHtml}}
               </div>
               <div style="min-width:0;">
                 <div style="font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${{f.name}}</div>
                 <div style="font-size:12px; color:var(--muted);">${{(f.size/1024).toFixed(1)}} KB</div>
               </div>
             </div>
             <div style="display:flex; gap:4px;">
                <a href="${{f.url}}" target="_blank" class="action-btn" title="Open">{ICON_FILE}</a>
                <button class="action-btn" onclick="copyUrl('${{f.url}}')" title="Copy Link">{ICON_COPY}</button>
                <button class="action-btn danger" onclick="deleteFile('${{f.name}}')" title="Delete">{ICON_TRASH}</button>
             </div>
           `;
           fileList.appendChild(div);
         }});
      }}

      window.copyUrl = async (url) => {{
        await navigator.clipboard.writeText(location.origin + url);
        showToast('Link copied');
      }};

      window.deleteFile = async (name) => {{
        if (!confirm('Permanent delete?')) return;
        const res = await fetch(`/api/files/${{name}}`, {{ method:'DELETE' }});
        if (res.ok) {{ showToast('Deleted'); fetchFiles(); }}
      }};

      uploadBtn.addEventListener('click', async () => {{
        uploadBtn.textContent = 'Uploading...';
        uploadBtn.disabled = true;
        for (const f of queue) {{
          const form = new FormData();
          form.append('file', f);
          await fetch('/api/upload', {{ method:'POST', body:form }});
        }}
        queue = [];
        uploadBtn.textContent = 'Start Upload';
        queueEl.textContent = '';
        fetchFiles();
        showToast('Upload Complete');
      }});

      document.getElementById('refreshBtn').addEventListener('click', fetchFiles);
      fetchFiles();
    """
    return TEMPLATE_BASE.format(title="Upload | foreverhyx", styles=STYLES, content=content, script=script)


@app.post("/api/upload")
async def upload_file_api(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    require_login(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    
    # Simple safe filename
    safe_name = Path(file.filename).name
    target_path = safe_join(UPLOAD_DIR, safe_name)

    with target_path.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024 * 5) # 5MB chunks
            if not chunk:
                break
            f.write(chunk)

    return JSONResponse({"filename": safe_name, "url": f"/uploads/{safe_name}"})


@app.get("/api/files")
def list_files_api(request: Request) -> JSONResponse:
    require_login(request)
    items: List[dict] = []
    # reverse sort by modificaton time usually better for uploads
    files = sorted(UPLOAD_DIR.iterdir(), key=os.path.getmtime, reverse=True)
    for path in files:
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
