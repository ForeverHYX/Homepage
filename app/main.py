from __future__ import annotations

import os
import secrets
import re
from pathlib import Path
from typing import List, Tuple, Optional, Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import markdown

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = Path(os.getenv("HOMEPAGE_CONTENT_DIR", BASE_DIR / "content")).resolve()
UPLOAD_DIR = Path(os.getenv("HOMEPAGE_UPLOAD_DIR", BASE_DIR / "uploads")).resolve()

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Yixun Hong's Homepage", version="0.4.0")

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


def parse_markdown_sections(filename: str) -> List[Tuple[str, str]]:
    """
    Parses a markdown file into sections based on H1 headers (# Header).
    Returns a list of (Title, HTML_Content) tuples.
    """
    path = CONTENT_DIR / filename
    if not path.exists():
        return []
    
    text = path.read_text(encoding="utf-8")
    sections = []
    current_title = ""
    current_lines = []
    
    def flush():
        if current_title or current_lines:
            raw_body = "\n".join(current_lines)
            html_body = markdown.markdown(raw_body, extensions=["fenced_code", "tables", "toc"])
            sections.append((current_title, html_body))

    for line in text.splitlines():
        if line.strip().startswith("# "):
            flush()
            current_title = line.strip()[2:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    
    # Filter out empty sections
    return [s for s in sections if s[0] or s[1]]

def get_about_info() -> dict:
    """Parses about.md for structured info."""
    default = {
        "email": "#", "github": "#", "location": "Earth", 
        "name": "Yixun Hong", "role": "Student / Researcher"
    }
    path = CONTENT_DIR / "about.md"
    if not path.exists():
        return default
    
    text = path.read_text(encoding="utf-8")
    info = default.copy()
    
    # Simple regex extraction
    if match := re.search(r'\((mailto:[^)]+)\)', text): info["email"] = match.group(1)
    if match := re.search(r'\((https://github[^)]+)\)', text): info["github"] = match.group(1)
    
    if "## Location" in text:
        parts = text.split("## Location")
        if len(parts) > 1:
            info["location"] = parts[1].strip().split("\n")[0]
            
    # Allow overriding name/role via comments or specific syntax if needed, 
    # but for now we keep them hardcoded or minimal as requested.
    
    return info


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
        --bg: #f8fafc; --text: #334155; --primary: #3b82f6; --primary-hover: #2563eb; 
        --surface: #ffffff; --border: #e2e8f0; --muted: #64748b; 
        --radius: 12px; --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
    }
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; line-height: 1.6; }
    
    /* Layout */
    .container { max-width: 1080px; margin: 0 auto; padding: 0 24px; }
    header { background: var(--surface); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 10; margin-bottom: 40px; box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05); }
    .nav { display: flex; align-items: center; justify-content: space-between; height: 64px; }
    .brand { font-weight: 700; font-size: 18px; text-decoration: none; color: #0f172a; display: flex; align-items: center; gap: 8px; }
    
    .main-grid { display: grid; gap: 48px; grid-template-columns: 1fr; align-items: start; }
    @media (min-width: 800px) { .main-grid { grid-template-columns: 260px 1fr; } }
    
    /* Sidebar */
    .sidebar { display: flex; flex-direction: column; gap: 24px; position: sticky; top: 100px; }
    
    /* Common Card Style */
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }

    .profile-card { padding: 32px 24px; text-align: center; }
    .avatar { width: 140px; height: 140px; border-radius: 50%; object-fit: cover; margin-bottom: 20px; box-shadow: var(--shadow); }
    
    .news-card { padding: 24px; }
    .news-title { font-size: 18px; font-weight: 700; color: #0f172a; margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px; }
    .news-list { list-style: none; padding: 0; margin: 0; }
    .news-item { font-size: 14px; color: var(--muted); margin-bottom: 12px; border-bottom: 1px dashed var(--border); padding-bottom: 12px; }
    .news-item:last-child { border: none; margin: 0; padding: 0; }

    .profile-name { margin: 0; font-size: 22px; font-weight: 700; color: #0f172a; letter-spacing: -0.01em; }
    .profile-role { color: var(--muted); margin: 6px 0 0; font-size: 15px; font-weight: 400; }
    
    .contact-links { display: flex; justify-content: center; gap: 12px; margin: 24px 0; }
    .contact-icon { color: var(--muted); transition: all .2s; padding: 8px; border-radius: 50%; background: #f1f5f9; display: inline-flex; width: 36px; height: 36px; align-items: center; justify-content: center; }
    .contact-icon:hover { color: var(--primary); background: #e0f2fe; }
    
    .location { display: flex; align-items: flex-start; justify-content: center; gap: 8px; color: var(--muted); font-size: 14px; margin-top: 20px; text-align: left; line-height: 1.4; padding: 0 10px; }
    .location svg { flex-shrink: 0; margin-top: 2px; }

    /* Content Area */
    .content-area { display: flex; flex-direction: column; gap: 40px; padding: 40px; }
    
    .cv-section { animation: fadeIn 0.5s ease-out; }
    .section-title { font-size: 1.5rem; font-weight: 700; color: #0f172a; margin: 0 0 1.5rem 0; padding-left: 1rem; border-left: 5px solid var(--primary); letter-spacing: -0.02em; }
    
    /* Typography inside sections */
    .prose { font-size: 15px; color: #475569; }
    .prose p { margin-bottom: 1rem; }
    .prose ul { padding-left: 1.25rem; margin-bottom: 1rem; }
    .prose li { margin-bottom: 0.5rem; }
    .prose strong { color: #0f172a; font-weight: 600; }
    .prose em { color: var(--muted); font-style: italic; }
    
    .prose h1, .prose h2, .prose h3 { margin-top: 0; } 
    /* Hide the original H1 if we rendered it as section-title, but markdown parser keeps standard tags usually. 
       Our parser extracts H1 as title, so content starts with H2 or P usually. */
    .prose h2 { font-size: 1.1rem; font-weight: 600; color: #334155; margin-top: 1.5rem; margin-bottom: 0.75rem; }
    .prose a { color: var(--primary); text-decoration: none; font-weight: 500; transition: color .2s; }
    .prose a:hover { color: var(--primary-hover); text-decoration: underline; }

    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

    /* Upload UI (Keep mostly same but clean up) */
    .upload-grid { display: grid; gap: 32px; grid-template-columns: 1fr; margin-top: 32px; }
    @media (min-width: 860px) { .upload-grid { grid-template-columns: 320px 1fr; } }
    
    .drop-zone { border: 2px dashed var(--border); border-radius: var(--radius); padding: 40px 24px; text-align: center; transition: all .2s; cursor: pointer; background: white; position: relative; overflow: hidden; }
    .drop-zone:hover, .drop-zone.drag { border-color: var(--primary); background: #f8fafc; }
    .drop-zone input { position: absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor: pointer; }
    
    .file-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; background: white; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 8px; }
    .file-preview { width: 36px; height: 36px; border-radius: 6px; object-fit: cover; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: var(--muted); flex-shrink: 0; }
    
    .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 20px; border-radius: 8px; font-weight: 500; cursor: pointer; transition: all .2s; font-size: 14px; text-decoration: none; border: none; }
    .btn-primary { background: var(--primary); color: white; width: 100%; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
    
    .action-btn { background: transparent; border: none; padding: 6px; border-radius: 6px; cursor: pointer; color: var(--muted); transition: all .2s; display: inline-flex; }
    .action-btn:hover { background: #f1f5f9; color: var(--text); }
    .action-btn.danger:hover { background: #fee2e2; color: #ef4444; }
    
    .toast { position: fixed; bottom: 32px; right: 32px; background: #0f172a; color: white; padding: 12px 24px; border-radius: 8px; font-weight: 500; opacity: 0; transform: translateY(20px); transition: all .3s; pointer-events: none; z-index: 100; font-size: 14px; }
    .toast.show { opacity: 1; transform: translateY(0); }
"""

TEMPLATE_BASE = """<!doctype html>
<html lang="en">
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
        <span>Yixun Hong's Homepage</span>
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
    # Get structured info
    about = get_about_info()
    avatar_url = "/uploads/avatar.png"

    # Parse main content into sections
    raw_sections = parse_markdown_sections("content.md")
    
    # Generate HTML for each section
    sections_html = ""
    for title, body in raw_sections:
        sections_html += f"""
        <section class="cv-section">
            <h2 class="section-title">{title}</h2>
            <div class="prose">
                {body}
            </div>
        </section>
        """

    # If no sections, just render normally to avoid blank page
    if not sections_html:
        raw_html = render_markdown_file("content.md") if (CONTENT_DIR / "content.md").exists() else ""
        sections_html = f"""<div class="prose">{raw_html}</div>"""

    page_content = f"""
    <div class="container main-grid">
      <aside class="sidebar">
        <div class="card profile-card">
          <img src="{avatar_url}" class="avatar" alt="Avatar" onerror="this.src='https://ui-avatars.com/api/?name=YH&background=3b82f6&color=fff&size=128'" />
          <h1 class="profile-name">{about['name']}</h1>
          <p class="profile-role">{about['role']}</p>
          
          <div class="contact-links">
            <a href="{about['email']}" class="contact-icon" title="Email">{ICON_MAIL}</a>
            <a href="{about['github']}" class="contact-icon" target="_blank" title="GitHub">{ICON_GITHUB}</a>
          </div>
          
          <div class="location">
            {ICON_MAP} <span>{about['location']}</span>
          </div>
        </div>

        <div class="card news-card">
            <h3 class="news-title">News</h3>
            <ul class="news-list">
              <li class="news-item">Welcome to my new homepage!</li>
            </ul>
        </div>
      </aside>
      
      <main class="card content-area">
        {sections_html}
      </main>
    </div>
    """
    return TEMPLATE_BASE.format(title="Home | Yixun Hong", styles=STYLES, content=page_content, script="")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> Any:
    if get_current_user(request):
        return RedirectResponse("/upload")
    
    content = f"""
    <div class="container" style="display:flex; justify-content:center; padding-top:80px;">
      <div style="background:white; padding:40px; border-radius:16px; width:100%; max-width:400px; border:1px solid var(--border); box-shadow:var(--shadow);">
        <h1 style="margin:0 0 8px; font-size:24px;">Welcome Back</h1>
        <p style="color:var(--muted); margin:0 0 32px;">Sign in to manage your files</p>
        <form action="/login" method="post">
          <div style="margin-bottom:20px;">
            <label style="display:block; margin-bottom:8px; font-weight:500;">Username</label>
            <input name="username" required autofocus style="width:100%; padding:10px; border:1px solid var(--border); border-radius:8px; font-size:16px;" />
          </div>
          <div style="margin-bottom:32px;">
            <label style="display:block; margin-bottom:8px; font-weight:500;">Password</label>
            <input type="password" name="password" required style="width:100%; padding:10px; border:1px solid var(--border); border-radius:8px; font-size:16px;" />
          </div>
          <button type="submit" class="btn btn-primary">Sign In</button>
        </form>
      </div>
    </div>
    """
    return TEMPLATE_BASE.format(title="Login | Yixun Hong", styles=STYLES, content=content, script="")


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
        <div style="background:white; padding:24px; border-radius:12px; border:1px solid var(--border); position:sticky; top:100px;">
          <h2 style="margin-top:0; font-size:18px;">Upload Manager</h2>
          <div id="drop" class="drop-zone">
            <div style="color:var(--primary); margin-bottom:12px;">{ICON_UPLOAD_CLOUD}</div>
            <p style="margin:0; font-weight:600; color:var(--text); font-size:15px;">Click or Drag files</p>
            <p style="font-size:13px; color:var(--muted); margin:4px 0 0;">Up to 100MB per file</p>
            <input id="fileInput" type="file" multiple />
          </div>
          <div id="queue-status" style="margin-top:16px; font-size:14px; text-align:center; color:var(--muted);"></div>
          <button id="uploadBtn" class="btn btn-primary" style="margin-top:16px;" disabled>Start Upload</button>
        </div>
      </section>
      
      <section>
        <div style="background:white; padding:32px; border-radius:12px; border:1px solid var(--border); min-height:400px;">
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
    return TEMPLATE_BASE.format(title="Upload | Yixun Hong", styles=STYLES, content=content, script=script)


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