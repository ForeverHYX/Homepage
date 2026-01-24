from __future__ import annotations

import os
import secrets
import re
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Any
from PIL import Image, ImageOps

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import markdown
from dotenv import load_dotenv
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

CONTENT_DIR = Path(os.getenv("HOMEPAGE_CONTENT_DIR", BASE_DIR / "content")).resolve()
ARTICLES_DIR = CONTENT_DIR / "articles"
UPLOAD_DIR = Path(os.getenv("HOMEPAGE_UPLOAD_DIR", BASE_DIR / "uploads")).resolve()

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Yixun Hong's Homepage", version="0.4.0")

# Security
UPLOAD_USERNAME = os.getenv("HOMEPAGE_UPLOAD_USER", "admin")
UPLOAD_PASSWORD = os.getenv("HOMEPAGE_UPLOAD_PASS", "changeme")
SESSION_KEY = "session_token"
VALID_SESSIONS = set()

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# --- Extensions ---

class PdfTreeprocessor(Treeprocessor):
    def run(self, root):
        for element in root.iter():
            if element.tag == 'img':
                src = element.get('src')
                if src and src.lower().endswith('.pdf'):
                    element.tag = 'embed'
                    element.set('type', 'application/pdf')
                    element.set('style', 'width:100%; min-height:800px; border:none;')
                    if 'alt' in element.attrib:
                        del element.attrib['alt']

class PdfExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(PdfTreeprocessor(md), 'pdf_embed', 15)


# --- Utilities ---

GALLERY_CONFIG_FILE = BASE_DIR / "gallery_config.json"

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
    default = {"title": folder_path.name, "description": "", "date": ""}
    if meta_file.exists():
        try:
            stored = json.loads(meta_file.read_text())
            return {**default, **stored}
        except:
            pass
    return default

def save_folder_meta(folder_path: Path, title: str, description: str, date: str = ""):
    meta = {"title": title, "description": description, "date": date}
    (folder_path / "meta.json").write_text(json.dumps(meta))


def process_uploaded_image(file_path: Path) -> str:
    """Converts JPG to WebP and returns the new filename."""
    if file_path.suffix.lower() in ['.jpg', '.jpeg']:
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too huge (optional, but good for galleries)
                if max(img.size) > 1920:
                    img.thumbnail((1920, 1920))

                webp_path = file_path.with_suffix('.webp')
                img.save(webp_path, 'WEBP', quality=80)
            
            # Remove original
            file_path.unlink()
            return webp_path.name
        except Exception as e:
            print(f"Error converting image {file_path}: {e}")
    return file_path.name

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
            html_body = markdown.markdown(raw_body, extensions=["fenced_code", "tables", "toc", PdfExtension()])
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


def get_all_articles() -> List[dict]:
    """Scans ARTICLES_DIR for markdown files and returns sorting info."""
    if not ARTICLES_DIR.exists():
        return []
    
    articles = []
    for f in ARTICLES_DIR.glob("*.md"):
        stats = f.stat()
        text = f.read_text(encoding="utf-8")
        title = f.stem.replace("-", " ").title()
        date_str = ""
        author = "Yixun Hong"
        summary = ""
        
        # Parse Frontmatter-like lines (or just top lines)
        lines = text.splitlines()
        content_lines = []
        
        for line in lines:
            line_strip = line.strip()
            # Title
            if not title or title == f.stem.replace("-", " ").title():
                if line_strip.startswith("# "):
                    title = line_strip[2:].strip()
                    continue
            
            # Metadata
            if line_strip.lower().startswith("**date**:") or line_strip.lower().startswith("date:"):
                date_str = line_strip.split(":", 1)[1].strip()
                continue
            
            if line_strip.lower().startswith("**author**:") or line_strip.lower().startswith("author:"):
                author = line_strip.split(":", 1)[1].strip()
                continue
                
            # Content for summary (skip headers and empty lines)
            if not line_strip or line_strip.startswith("#") or line_strip.startswith("!"):
                continue
            content_lines.append(line_strip)
            
        # Generate Summary (first ~200 chars)
        full_content = " ".join(content_lines)
        if len(full_content) > 200:
            summary = full_content[:200] + "..."
        else:
            summary = full_content

        # Fallback date from mtime if not in file
        mtime = stats.st_mtime
        if date_str:
            try:
                # Try parse YYYY-MM-DD
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                mtime = dt.timestamp()
            except ValueError:
                try: 
                    dt = datetime.strptime(date_str, "%Y-%m")
                    mtime = dt.timestamp()
                except ValueError:
                    pass

        articles.append({
            "slug": f.stem,
            "title": title,
            "date": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"),
            "author": author,
            "summary": summary,
            "mtime": mtime
        })
    
    # Sort by time desc
    return sorted(articles, key=lambda x: x["mtime"], reverse=True)


def parse_and_merge_news() -> str:
    """Parses news.md and merges with articles, sorting by date."""
    items = []
    
    # 1. Parse Manual News (from content.md)
    news_path = CONTENT_DIR / "news.md"
    if news_path.exists():
        text = news_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not (line.startswith("- ") or line.startswith("* ")):
                continue
            
            # Remove bullet
            content = line[2:].strip()
            
            # Try to extract date **YYYY-MM**: or **YYYY-MM-DD**:
            match = re.match(r'\*\*(.*?)\*\*:(.*)', content)
            if match:
                date_str = match.group(1).strip()
                body_raw = match.group(2).strip()
                
                # Parse Date
                dt = datetime.min
                try:
                    if len(date_str) == 10: # YYYY-MM-DD
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                    elif len(date_str) == 7: # YYYY-MM
                        dt = datetime.strptime(date_str, "%Y-%m")
                except ValueError:
                    pass
                
                # Render Body (handle links etc)
                # Using markdown for the body part to support [Link](url)
                body_html = markdown.markdown(body_raw).replace('<p>','').replace('</p>','')
                
                items.append({
                    "date": dt,
                    "html": f"<strong>{date_str}:</strong> {body_html}"
                })
    
    # 2. Parse Articles
    for art in get_all_articles():
        dt = datetime.fromtimestamp(art["mtime"])
        date_str = dt.strftime("%Y-%m")
        # Ensure consistent format
        items.append({
            "date": dt,
            "html": f"<strong>{date_str}:</strong> New blog post: <a href=\"/articles/{art['slug']}\">{art['title']}</a>."
        })
        
    # 3. Sort by date desc
    items.sort(key=lambda x: x["date"], reverse=True)
    
    # 4. Limit to max 5 items
    items = items[:5]
    
    # 5. Render
    if not items:
        return '<ul class="news-list"><li class="news-item">No news yet.</li></ul>'
        
    html = '<ul class="news-list">'
    for item in items:
        html += f'<li class="news-item">{item["html"]}</li>'
    html += '</ul>'
    
    return html


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
ICON_OPEN = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>"""
ICON_TRASH = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>"""
ICON_COPY = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>"""
ICON_MAIL = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>"""
ICON_GITHUB = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>"""
ICON_MAP = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>"""
ICON_CALENDAR = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; position:relative; top:2px;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>"""
ICON_USER_S = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; position:relative; top:2px;"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>"""
ICON_FOLDER = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>"""
ICON_STAR = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>"""
ICON_STAR_FILLED = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="#eab308" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>"""
ICON_MAXIMIZE = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>"""
ICON_ARROW_LEFT = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>"""
ICON_MOON = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>"""
ICON_SUN = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>"""

STYLES = """
    :root { 
        --bg: #f8fafc; --text: #334155; --heading: #0f172a; --primary: #3b82f6; --primary-hover: #2563eb; 
        --surface: #ffffff; --surface-highlight: #f1f5f9; --border: #e2e8f0; --muted: #64748b; 
        --radius: 12px; --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
        --header-bg: #ffffff;
    }
    
    [data-theme="dark"] {
        --bg: #000000; --text: #cbd5e1; --heading: #f1f5f9; --primary: #60a5fa; --primary-hover: #93c5fd; 
        --surface: #111111; --surface-highlight: #1e293b; --border: #334155; --muted: #94a3b8;
        --radius: 12px; --shadow: 0 1px 3px 0 rgb(255 255 255 / 0.05), 0 1px 2px -1px rgb(255 255 255 / 0.05); /* Subtle light shadow/border */
        --header-bg: #111111;
        
        color-scheme: dark;
    }

    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; line-height: 1.6; transition: background 0.3s, color 0.3s; }
    
    /* Layout */
    .container { max-width: 1080px; margin: 0 auto; padding: 0 24px; }
    header { background: var(--header-bg); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 10; margin-bottom: 40px; box-shadow: var(--shadow); transition: background 0.3s, border-color 0.3s; }
    .nav { display: flex; align-items: center; justify-content: space-between; height: 64px; }
    .brand { font-weight: 700; font-size: 18px; text-decoration: none; color: var(--heading); display: flex; align-items: center; gap: 8px; }
    
    .main-grid { display: grid; gap: 48px; grid-template-columns: 1fr; align-items: start; }
    @media (min-width: 800px) { .main-grid { grid-template-columns: 260px 1fr; } }
    
    /* Sidebar */
    .sidebar { display: flex; flex-direction: column; gap: 24px; position: sticky; top: 100px; }
    
    /* Common Card Style */
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; transition: background 0.3s, border-color 0.3s; }

    .profile-card { padding: 32px 24px; text-align: center; }
    .avatar { width: 140px; height: 140px; border-radius: 50%; object-fit: cover; margin-bottom: 20px; box-shadow: var(--shadow); }
    
    .news-card { padding: 24px; }
    .news-title { font-size: 18px; font-weight: 700; color: var(--heading); margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px; }
    .news-list { list-style: none; padding: 0; margin: 0; }
    .news-item { font-size: 14px; color: var(--muted); margin-bottom: 12px; }
    .news-item a { color: inherit; text-decoration: none; border-bottom: 1px dashed var(--muted); transition: all 0.2s; }
    .news-item a:hover { color: var(--primary); border-bottom-color: var(--primary); }
    
    .profile-name { margin: 0; font-size: 22px; font-weight: 700; color: var(--heading); letter-spacing: -0.01em; }
    .profile-role { color: var(--muted); margin: 6px 0 0; font-size: 15px; font-weight: 400; }
    
    .contact-links { display: flex; justify-content: center; gap: 12px; margin: 24px 0; }
    .contact-icon { color: var(--muted); transition: all .2s; padding: 8px; border-radius: 50%; background: var(--surface-highlight); display: inline-flex; width: 36px; height: 36px; align-items: center; justify-content: center; }
    .contact-icon:hover { color: var(--primary); background: #e0f2fe; }
    [data-theme="dark"] .contact-icon:hover { background: #1e3a8a; } /* Dark mode hover bg */
    
    .location { display: flex; align-items: flex-start; justify-content: center; gap: 8px; color: var(--muted); font-size: 14px; margin-top: 20px; text-align: left; line-height: 1.4; padding: 0 10px; }
    .location svg { flex-shrink: 0; margin-top: 2px; }

    /* Content Area */
    .content-area { display: flex; flex-direction: column; gap: 40px; padding: 40px; }
    
    .cv-section { animation: fadeIn 0.5s ease-out; }
    
    .section-title { font-size: 1.5rem; font-weight: 700; color: var(--heading); margin: 0 0 1.5rem 0; padding-left: 1rem; border-left: 5px solid var(--primary); letter-spacing: -0.02em; }
    
    /* Typography inside sections */
    .prose { font-size: 15px; color: var(--text); }
    .prose p { margin-bottom: 1rem; }
    .prose ul { padding-left: 1.25rem; margin-bottom: 1rem; list-style-type: disc; }
    .prose ol { padding-left: 1.25rem; margin-bottom: 1rem; list-style-type: decimal; }
    
    /* Layout for Article Detail */
    .article-container { display: grid; grid-template-columns: 1fr; gap: 40px; position: relative; }
    @media (min-width: 1000px) { .article-container { grid-template-columns: minmax(0, 1fr) 280px; } }
    
    .toc { position: sticky; top: 100px; max-height: calc(100vh - 120px); overflow-y: auto; padding: 20px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); }
    .toc ul { list-style: none; padding: 0; margin: 0; }
    .toc li { margin-bottom: 8px; font-size: 14px; }
    .toc a { color: var(--muted); text-decoration: none; transition: all .2s; display: block; }
    .toc a:hover { color: var(--primary); }
    
    /* News Card Markdown Styles override */
    .news-card ul { list-style: none; padding: 0; margin: 0; }
    .news-card li { font-size: 14px; color: var(--muted); margin-bottom: 12px; }
    .news-card li:last-child { margin-bottom: 0; padding-bottom: 0; }
    .news-card p { margin: 0; } /* Reset p inside li if markdown adds it */
    .news-card strong { color: var(--heading); font-weight: 600; } /* Ensure date/strong is dark like name/title */

    .prose li { margin-bottom: 0.5rem; }
    .prose strong { color: var(--heading); font-weight: 600; }
    .prose em { color: var(--muted); font-style: italic; }
    
    /* Article Grid Layout */
    .article-grid { display: grid; grid-template-columns: 1fr; gap: 32px; align-items: stretch; }
    @media (min-width: 1024px) { .article-grid { grid-template-columns: 1fr 240px; } }

    /* Refined Typography for Article Body */
    .prose h1, .prose h2, .prose h3, .prose h4 { color: var(--heading); line-height: 1.3; font-weight: 700; }
    /* H1 in body (if any) or large section headers */
    .prose h1 { font-size: 1.8rem; margin-top: 2rem; margin-bottom: 1rem; letter-spacing: -0.02em; } 
    /* Standard section headers */
    .prose h2 { font-size: 1.5rem; margin-top: 2rem; margin-bottom: 1rem; letter-spacing: -0.01em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
    .prose h3 { font-size: 1.25rem; margin-top: 1.5rem; margin-bottom: 0.75rem; font-weight: 600; }
    .prose h4 { font-size: 1.1rem; margin-top: 1.25rem; margin-bottom: 0.5rem; font-weight: 600; }
    
    .prose p { margin-bottom: 1.25rem; line-height: 1.75; font-size: 1.05rem; }
    .prose > *:first-child { margin-top: 0; }
    .prose a { color: var(--primary); text-decoration: none; font-weight: 500; transition: color .2s; }
    .prose a:hover { color: var(--primary-hover); text-decoration: underline; }

    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

    /* Upload UI (Keep mostly same but clean up) */
    .upload-grid { display: grid; gap: 32px; grid-template-columns: 1fr; margin-top: 32px; }
    @media (min-width: 860px) { .upload-grid { grid-template-columns: 320px 1fr; } }
    
    .drop-zone { border: 2px dashed var(--border); border-radius: var(--radius); padding: 40px 24px; text-align: center; transition: all .2s; cursor: pointer; background: var(--surface); position: relative; overflow: hidden; }
    .drop-zone:hover, .drop-zone.drag { border-color: var(--primary); background: var(--surface-highlight); }
    .drop-zone input { position: absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor: pointer; }
    
    .file-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; }
    .file-preview { width: 36px; height: 36px; border-radius: 6px; object-fit: cover; background: var(--surface-highlight); display: flex; align-items: center; justify-content: center; color: var(--primary); flex-shrink: 0; }
    
    .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 20px; border-radius: 8px; font-weight: 500; cursor: pointer; transition: all .2s; font-size: 14px; text-decoration: none; border: none; }
    .btn-primary { background: var(--primary); color: white; width: 100%; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
    
    .action-btn { background: transparent; border: none; padding: 6px; border-radius: 6px; cursor: pointer; color: var(--muted); transition: all .2s; display: inline-flex; }
    .action-btn:hover { background: var(--surface-highlight); color: var(--text); }
    .action-btn.danger:hover { background: #fee2e2; color: #ef4444; }
    
    .toast { position: fixed; bottom: 32px; right: 32px; background: #0f172a; color: white; padding: 12px 24px; border-radius: 8px; font-weight: 500; opacity: 0; transform: translateY(20px); transition: all .3s; pointer-events: none; z-index: 100; font-size: 14px; }
    .toast.show { opacity: 1; transform: translateY(0); }
"""

TEMPLATE_BASE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/png" href="/uploads/favicon.png">
  <title>{title}</title>
  <meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0f172a" media="(prefers-color-scheme: dark)">
  <style>{styles}</style>
  <script>
    (function() {{
        const saved = localStorage.getItem('theme');
        const sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (saved === 'dark' || (!saved && sysDark)) {{
            document.documentElement.setAttribute('data-theme', 'dark');
        }}
    }})();
  </script>
</head>
<body>
  <header>
    <div class="container nav">
      <a href="/" class="brand">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        <span>Yixun Hong's Homepage</span>
      </a>
      <div style="display:flex; gap:20px; font-weight:500; align-items:center;">
        <a href="/" style="text-decoration:none; color:var(--text);">Home</a>
        <a href="/articles" style="text-decoration:none; color:var(--text);">Articles</a>
        <a href="/gallery" style="text-decoration:none; color:var(--text);">Gallery</a>
        <a href="/uploads/transcript.pdf" target="_blank" style="text-decoration:none; color:var(--text);">Resume</a>
        <a href="/upload" style="text-decoration:none; color:var(--text);">Upload</a>
        <button id="themeToggle" class="action-btn" title="Toggle Theme" style="margin-left:8px;" onclick="toggleTheme()">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
        </button>
      </div>
    </div>
  </header>
  {content}
  <script>
    const ICON_MOON = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
    const ICON_SUN = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;

    function toggleTheme() {{
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(next);
    }}
    
    function updateThemeIcon(theme) {{
        const btn = document.getElementById('themeToggle');
        if (theme === 'dark') btn.innerHTML = ICON_SUN;
        else btn.innerHTML = ICON_MOON;
    }}
    
    // Init correct icon on load
    updateThemeIcon(document.documentElement.getAttribute('data-theme'));
  
    {script}
  </script>
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
    
    # Section Colors (Light Blue to Primary Blue)
    section_colors = ['#bfdbfe', '#93c5fd', '#60a5fa', '#3b82f6']

    # Generate HTML for each section
    sections_html = ""
    for i, (title, body) in enumerate(raw_sections):
        color = section_colors[i % len(section_colors)]
        
        sections_html += f"""
        <section class="cv-section">
            <h2 class="section-title" style="border-left-color: {color}">{title}</h2>
            <div class="prose">
                {body}
            </div>
        </section>
        """

    # If no sections, just render normally to avoid blank page
    if not sections_html:
        raw_html = render_markdown_file("content.md") if (CONTENT_DIR / "content.md").exists() else ""
        sections_html = f"""<div class="prose">{raw_html}</div>"""

    # Render News (Merged & Sorted)
    news_html = parse_and_merge_news()

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
            {news_html}
        </div>
      </aside>
      
      <main class="card content-area">
        {sections_html}
      </main>
    </div>
    """
    return TEMPLATE_BASE.format(title="Home | Yixun Hong", styles=STYLES, content=page_content, script="")


@app.get("/articles", response_class=HTMLResponse)
def articles_index() -> str:
    articles = get_all_articles()
    
    list_items = ""
    for art in articles:
        # Create a card for each article
        list_items += f"""
        <div class="card" style="padding:24px; margin-bottom:0px; transition: transform 0.2s;">
            <h2 style="margin:0 0 12px 0; font-size:1.5rem;">
                <a href="/articles/{art["slug"]}" style="text-decoration:none; color:var(--heading);">{art["title"]}</a>
            </h2>
            <div style="font-size:13px; color:var(--muted); margin-bottom:12px; display:flex; gap:16px;">
                 <span>{ICON_CALENDAR} {art["date"]}</span>
                 <span>{ICON_USER_S} {art["author"]}</span>
            </div>
            <p style="color:var(--text); font-size:15px; margin:0; line-height:1.6;">
                {art["summary"]}
            </p>
            <div style="margin-top:16px;">
                <a href="/articles/{art["slug"]}" style="font-weight:600; font-size:14px; color:var(--primary); text-decoration:none;">Read more &rarr;</a>
            </div>
        </div>
        """
    
    content_html = f"""
    <div class="container">
        <div class="content-area" style="max-width:800px; margin:0 auto; padding:40px 0; background:transparent;">
            <h1 class="section-title" style="border-left-color: var(--primary); margin-bottom:24px; font-size: 3rem; padding-bottom:10px;">Articles</h1>
            <div style="display:flex; flex-direction:column; gap:24px;">
                {list_items if articles else "<p>No articles yet.</p>"}
            </div>
        </div>
    </div>
    """
    return TEMPLATE_BASE.format(title="Articles | Yixun Hong", styles=STYLES, content=content_html, script="")


@app.get("/gallery", response_class=HTMLResponse)
def gallery_index(focus: Optional[str] = None) -> str:
    gallery_dirs = get_gallery_folders()
    
    is_focused = False
    if focus and focus in gallery_dirs:
        gallery_dirs = [focus]
        is_focused = True

    # Gather data first
    albums_data = []

    for rel_path in gallery_dirs:
         path = safe_join(UPLOAD_DIR, rel_path)
         if not path.exists() or not path.is_dir():
             continue
             
         # Get Images
         images = []
         try:
             for f in sorted(list(path.iterdir()), key=lambda x: x.name):
                 if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                      rel_file_path = f.relative_to(UPLOAD_DIR)
                      images.append(f"/uploads/{rel_file_path}")
         except:
             continue
                  
         if not images:
             continue
             
         # Get metadata
         meta = get_folder_meta(path)
         title = meta.get("title", path.name)
         desc = meta.get("description", "")
         date_str = meta.get("date", "")
         
         # Determine Sort Timestamp
         sort_ts = 0.0
         if date_str:
             try:
                 sort_ts = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
             except: pass
         
         if sort_ts == 0.0:
            # Fallback to latest mtime in folder
            try:
                sort_ts = max(p.stat().st_mtime for p in path.iterdir())
                # If no provided date, maybe format this for display? 
                # User asked: "按文件上传的日期" (upload date) if no date provided.
                # We can store this as fallback date_str for display too.
                date_str = datetime.fromtimestamp(sort_ts).strftime("%Y-%m-%d")
            except: pass
            
         albums_data.append({
             "path_name": path.name,
             "rel_path": rel_path,
             "title": title,
             "desc": desc,
             "date_str": date_str,
             "images": images,
             "sort_ts": sort_ts
         })
    
    # Sort by date descending
    albums_data.sort(key=lambda x: x["sort_ts"], reverse=True)

    albums_html = ""
    
    # Header Button (Back)
    if is_focused:
        albums_html += f"""
        <div style="margin-bottom: 24px;">
            <a href="/gallery" class="btn" style="background:var(--surface); border:1px solid var(--border); color:var(--text);">
                {ICON_ARROW_LEFT} Back to All Galleries
            </a>
        </div>
        """
    
    for album in albums_data:
         # Zoom Button Logic
         zoom_btn = ""
         if not is_focused:
             zoom_btn = f"""
             <a href="/gallery?focus={album['rel_path']}" title="Expand View" style="color:var(--muted); transition:color .2s; display:inline-flex; border:1px solid var(--border); padding:4px; border-radius:4px; margin-left:12px;">
                {ICON_MAXIMIZE}
             </a>
             """
         
         # Build Carousel HTML
         slides = ""
         for img_url in album["images"]:
             slides += f"""
             <div class="carousel-slide" onclick="openLightbox('{img_url}')">
                 <img src="{img_url}" loading="lazy" alt="Photo">
             </div>
             """
         
         wrapper_class = "carousel-wrapper focused" if is_focused else "carousel-wrapper"
         
         albums_html += f"""
         <section class="gallery-album mb-12">
             <div style="margin-bottom:16px; display:flex; align-items:center;">
                <div style="flex:1;">
                    <div style="display:flex; align-items:center;">
                        <h2 style="font-size:1.5rem; font-weight:700; margin:0; text-transform:capitalize; border-left: 5px solid var(--primary); padding-left: 12px; line-height: 1.2;">{album['title']}</h2>
                        {zoom_btn}
                    </div>
                    {f'<p style="margin:4px 0 0 0; padding-left:17px; color:var(--muted); font-size:0.9rem; font-weight:500;">{album["date_str"]}</p>' if album["date_str"] else ''}
                    {f'<p style="margin:4px 0 0 0; padding-left:17px; color:var(--text); font-size:1rem;">{album["desc"]}</p>' if album["desc"] else ''}
                </div>
             </div>
             <div class="{wrapper_class}">
                 <div class="carousel-container" id="carousel-{album['path_name']}">
                     {slides}
                 </div>
             </div>
         </section>
         """
    
    extra_styles = """
    .gallery-album { margin-bottom: 60px; }
    
    /* Lightbox Styles */
    .lightbox-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.95);
        z-index: 10000;
        display: none;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    .lightbox-overlay.active {
        display: flex;
        opacity: 1;
    }
    .lightbox-content {
        max-width: 95vw;
        max-height: 95vh;
        border-radius: 4px;
        box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
        transform: scale(0.95);
        transition: transform 0.3s ease;
    }
    .lightbox-overlay.active .lightbox-content {
        transform: scale(1);
    }
    .lightbox-close {
        position: absolute;
        top: 20px;
        right: 30px;
        color: white;
        font-size: 50px;
        cursor: pointer;
        z-index: 10001;
        line-height: 0.8;
        background: transparent;
        border: none;
        padding: 0;
        font-family: serif; 
        opacity: 0.8;
        transition: opacity 0.2s;
    }
    .lightbox-close:hover {
        opacity: 1;
    }

    /* Carousel / Filmstrip Styles */
    .carousel-wrapper {
        background: var(--surface);
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
        border-radius: 16px;
        padding: 20px 0;
        overflow: hidden;
        transition: all 0.3s ease;
    }
    
    /* Focused Mode Modifications */
    .carousel-wrapper.focused {
        /* Keep the shadow box look */
        background: var(--surface);
        border: 1px solid var(--border);
        box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1); /* Stronger shadow */
        border-radius: 20px;
        padding: 32px;
        
        /* Expand width slightly beyond normal container if possible, or just be full width */
        width: 100%;
    }

    .carousel-container { 
        overflow-x: auto; 
        display: flex;
        gap: 16px;
        padding: 0 24px 12px 24px;
        align-items: center; 
        scrollbar-width: thin;
        scrollbar-color: var(--muted) transparent;
    }
    
    .carousel-wrapper.focused .carousel-container {
        /* Convert to grid/wrap layout */
        flex-wrap: wrap;
        justify-content: center; /* Center images */
        gap: 16px; /* Space between images */
        padding: 0;
        height: auto; /* Let it grow vertically */
        overflow-x: visible; /* No scrollbar needed horizontally usually */
        align-items: flex-start;
    }
    
    /* Scrollbar Logic for Focused */
    .carousel-wrapper.focused .carousel-container::-webkit-scrollbar { display: none; }

    .carousel-container::-webkit-scrollbar { height: 6px; }
    .carousel-container::-webkit-scrollbar-track { background: transparent; }
    .carousel-container::-webkit-scrollbar-thumb { background-color: var(--muted); border-radius: 3px; }
    .carousel-container::-webkit-scrollbar-thumb:hover { background-color: var(--text); }
    
    .carousel-slide {
        flex: 0 0 auto;
        height: 500px;
        border-radius: 8px;
        overflow: hidden;
        transition: all 0.3s;
        cursor: pointer;
    }
    
    .carousel-wrapper.focused .carousel-slide {
        /* Fixed height for rows */
        height: 280px; 
        border-radius: 8px; /* Keep rounded corners */
        box-shadow: var(--shadow); /* Individual shadow */
        opacity: 1;
        transition: transform 0.2s;
    }

    .carousel-wrapper.focused .carousel-slide:hover {
        transform: scale(1.02); /* Subtle zoom on hover */
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    
    .carousel-slide img {
        height: 100%;
        width: auto; 
        object-fit: contain; 
        display: block;
    }
    
    @media(max-width: 800px) {
        .carousel-slide { height: 300px; }
        .carousel-wrapper.focused .carousel-slide { height: 200px; } /* Smaller on mobile */
    }
    """
    
    script = """
    // Lightbox Logic
    window.openLightbox = (url) => {
        const overlay = document.getElementById('lightboxOverlay');
        const img = document.getElementById('lightboxImg');
        img.src = url;
        overlay.style.display = 'flex';
        void overlay.offsetWidth;
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    };
    
    window.closeLightbox = () => {
        const overlay = document.getElementById('lightboxOverlay');
        overlay.classList.remove('active');
        setTimeout(() => {
            overlay.style.display = 'none';
            document.getElementById('lightboxImg').src = '';
            document.body.style.overflow = '';
        }, 300);
    };

    // Auto Scroll Logic (Only for non-focused)
    document.addEventListener('DOMContentLoaded', () => {
        // If focused, we might disable auto-scroll to let user inspect
        const carousels = document.querySelectorAll('.carousel-container');
        const isFocused = document.querySelector('.carousel-wrapper.focused');
        
        if (isFocused) return; // Disable auto scroll in focused mode

        carousels.forEach(container => {
            let interval;
            const startAutoPlay = () => {
                interval = setInterval(() => {
                    const currentScroll = container.scrollLeft;
                    const maxScroll = container.scrollWidth - container.clientWidth;
                    if (currentScroll >= maxScroll - 5) {
                        container.scrollTo({ left: 0, behavior: 'smooth' });
                    } else {
                        container.scrollBy({ left: 400, behavior: 'smooth' });
                    }
                }, 2000);
            };
            const stopAutoPlay = () => clearInterval(interval);
            startAutoPlay();
            container.addEventListener('mouseenter', stopAutoPlay);
            container.addEventListener('mouseleave', startAutoPlay);
            container.addEventListener('touchstart', stopAutoPlay, {passive: true});
            container.addEventListener('touchend', startAutoPlay);
        });
    });
    """

    content = f"""
    <div class="container">
        <div class="content-area" style="max-width:100%; margin:0 auto; padding:40px 0; background:transparent;">
             <h1 class="section-title" style="border-left-color: var(--primary); margin-bottom:24px; font-size: 3rem; padding-bottom:10px;">Gallery</h1>
            <p style="color:var(--muted); font-size:1.1rem; margin-top:-16px; margin-bottom:40px; padding-left:14px;">A collection of moments.</p>
        
            {albums_html if albums_html else '<div style="padding:24px; text-align:center; color:var(--muted);">No gallery albums yet. Upload a folder and toggle it in the Upload Manager.</div>'}
        </div>
    </div>
    
    <!-- Lightbox Structure -->
    <div id="lightboxOverlay" class="lightbox-overlay" onclick="closeLightbox()">
        <button class="lightbox-close" onclick="closeLightbox()">&times;</button>
        <img id="lightboxImg" class="lightbox-content" src="" alt="Full Size" onclick="event.stopPropagation()">
    </div>
    """
    
    return TEMPLATE_BASE.format(title="Gallery | Yixun Hong", styles=STYLES + extra_styles, content=content, script=script)


@app.get("/articles/{slug}", response_class=HTMLResponse)
def article_detail(slug: str) -> Any:
    path = ARTICLES_DIR / f"{slug}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Article not found")
    
    text = path.read_text(encoding="utf-8")
    
    # Parse Metadata manually to separate it from body
    lines = text.splitlines()
    body_lines = []
    
    title = ""
    author = "Yixun Hong"
    date_str = ""
    
    # Simple state parsers
    for line in lines:
        sline = line.strip()
        if not title and sline.startswith("# "):
            title = sline[2:].strip()
            continue
        if sline.lower().startswith("**date**:") or sline.lower().startswith("date:"):
            date_str = sline.split(":", 1)[1].strip()
            continue
        if sline.lower().startswith("**author**:") or sline.lower().startswith("author:"):
            author = sline.split(":", 1)[1].strip()
            continue
        
        body_lines.append(line)
    
    clean_body = "\n".join(body_lines)
    
    # Rendering with TOC
    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", PdfExtension()])
    html_body = md.convert(clean_body)
    toc_html = md.toc
    
    if not title: title = slug.replace("-", " ").title()

    content = f"""
    <div class="container article-grid" style="margin-top:40px; margin-bottom:60px;">
      <!-- Main Content Card -->
      <main class="card content-area" style="padding:40px; min-width:0;">
        <div style="margin-bottom:20px;">
            <a href="/articles" class="action-btn" style="text-decoration:none; padding-left:0;">&larr; Back to Articles</a>
        </div>
        
        <header style="margin-bottom:8px; border-bottom:1px solid var(--border); padding-bottom:8px;">
            <h1 style="font-size:2.5rem; font-weight:600; color:var(--heading); margin:0 0 8px 0; padding-left:16px; border-left:6px solid var(--primary); line-height:1.2;">{title}</h1>
            <div style="display:flex; gap:24px; color:var(--muted); font-size:15px; padding-left:22px;">
                 <span style="display:flex; align-items:center;">{ICON_CALENDAR} {date_str}</span>
                 <span style="display:flex; align-items:center;">{ICON_USER_S} {author}</span>
            </div>
        </header>

        <article class="prose">
          {html_body}
        </article>
      </main>

      <!-- Right Sidebar (TOC) -->
      <aside>
          <div class="toc" style="position:sticky; top:100px;">
              <p style="font-weight:700; color:var(--heading); margin-top:0; margin-bottom:12px; font-size:14px; text-transform:uppercase; letter-spacing:0.05em;">Contents</p>
              {toc_html}
          </div>
      </aside>

    </div>
    """
    return TEMPLATE_BASE.format(title=f"{title} | Yixun Hong", styles=STYLES, content=content, script="")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> Any:
    if get_current_user(request):
        return RedirectResponse("/upload")
    
    content = f"""
    <div class="container" style="display:flex; justify-content:center; padding-top:80px;">
      <div style="background:var(--surface); padding:40px; border-radius:16px; width:100%; max-width:400px; border:1px solid var(--border); box-shadow:var(--shadow);">
        <h1 style="margin:0 0 8px; font-size:24px;">Welcome Back</h1>
        <p style="color:var(--muted); margin:0 0 32px;">Sign in to manage your files</p>
        <form action="/login" method="post">
          <div style="margin-bottom:20px;">
            <label style="display:block; margin-bottom:8px; font-weight:500;">Username</label>
            <input name="username" required autofocus style="width:100%; padding:10px; border:1px solid var(--border); border-radius:8px; font-size:16px; background:var(--bg); color:var(--text);" />
          </div>
          <div style="margin-bottom:32px;">
            <label style="display:block; margin-bottom:8px; font-weight:500;">Password</label>
            <input type="password" name="password" required style="width:100%; padding:10px; border:1px solid var(--border); border-radius:8px; font-size:16px; background:var(--bg); color:var(--text);" />
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
        <div style="background:var(--surface); padding:24px; border-radius:12px; border:1px solid var(--border); position:sticky; top:100px;">
          <h2 style="margin-top:0; font-size:18px;">Upload Manager</h2>
          
          <div style="margin-bottom:16px;">
             <div style="font-weight:600; margin-bottom:8px; font-size:14px; color:var(--muted);">Current Path:</div>
             <div style="display:flex; gap:8px; align-items:center; background:var(--surface-highlight); padding:8px; border-radius:6px; font-family:monospace; overflow-x:auto;">
                 <button class="action-btn" onclick="openPath('')">Home</button>
                 <span id="currentPathDisplay">/</span>
             </div>
          </div>

          <div style="display:flex; gap:8px; margin-bottom:16px;">
             <input type="text" id="folderName" placeholder="New Folder" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text);">
             <button class="btn btn-primary" id="createFolderBtn" style="padding:0 12px;">+</button>
          </div>

          <div id="drop" class="drop-zone">
            <div style="color:var(--primary); margin-bottom:12px;">{ICON_UPLOAD_CLOUD}</div>
            <p style="margin:0; font-weight:600; color:var(--text); font-size:15px;">Click to Add Files</p>
            <input id="fileInput" type="file" multiple />
          </div>
          <div id="queue-status" style="margin-top:16px; font-size:14px; text-align:center; color:var(--muted);"></div>
          <button id="uploadBtn" class="btn btn-primary" style="margin-top:16px;" disabled>Start Upload</button>
        </div>
      </section>
      
      <section>
        <div style="background:var(--surface); padding:32px; border-radius:12px; border:1px solid var(--border); min-height:400px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px;">
            <h2 style="margin:0; font-size:20px;">Files & Folders</h2>
            <button id="refreshBtn" onclick="fetchFiles(currentPath)" class="action-btn">Refresh</button>
          </div>
          <div id="fileList"></div>
          <div id="emptyState" style="text-align:center; padding:60px 0; color:var(--muted); display:none;">
            <div style="opacity:0.5; margin-bottom:16px;">{ICON_FILE}</div>
            Folder is empty
          </div>
        </div>
      </section>
    </div>
    <div id="toast" class="toast">Action Completed</div>
    
    <!-- Edit Meta Modal -->
    <div id="metaModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000; align-items:center; justify-content:center;">
        <div style="background:var(--surface); padding:24px; border-radius:12px; width:100%; max-width:400px; box-shadow:var(--shadow);">
            <h3 style="margin:0 0 16px;">Edit Folder Info</h3>
            <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Title</label>
                <input id="metaTitle" type="text" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text);">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Shoot Date</label>
                <input id="metaDate" type="date" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text);">
            </div>
            <div style="margin-bottom:20px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Description</label>
                <textarea id="metaDesc" rows="3" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text); font-family:inherit;"></textarea>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:8px;">
                <button class="btn" style="background:var(--surface-highlight); color:var(--text);" onclick="closeMetaModal()">Cancel</button>
                <button class="btn btn-primary" style="width:auto;" onclick="saveMeta()">Save</button>
            </div>
        </div>
    </div>
    """

    script = f"""
      const drop = document.getElementById('drop');
      const fileInput = document.getElementById('fileInput');
      const uploadBtn = document.getElementById('uploadBtn');
      const queueEl = document.getElementById('queue-status');
      const fileList = document.getElementById('fileList');
      const toast = document.getElementById('toast');
      const pathDisplay = document.getElementById('currentPathDisplay');
      
      const metaModal = document.getElementById('metaModal');
      const metaTitle = document.getElementById('metaTitle');
      const metaDesc = document.getElementById('metaDesc');
      const metaDate = document.getElementById('metaDate');
      let currentEditPath = "";
      
      let queue = [];
      let currentPath = "";

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
      
      window.openMetaModal = (path, title, desc, date) => {{
          currentEditPath = path;
          metaTitle.value = title || "";
          metaDesc.value = desc || "";
          metaDate.value = date || "";
          metaModal.style.display = 'flex';
      }};
      
      window.closeMetaModal = () => {{
          metaModal.style.display = 'none';
      }};
      
      window.saveMeta = async () => {{
          const form = new FormData();
          form.append('path', currentEditPath);
          form.append('title', metaTitle.value);
          form.append('description', metaDesc.value);
          form.append('date', metaDate.value);
          
          try {{
            await fetch('/api/folder/meta', {{ method: 'POST', body: form }});
            closeMetaModal();
            fetchFiles(currentPath);
            showToast('Info Updated');
          }} catch(e) {{ alert(e); }}
      }};

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

      async function fetchFiles(path = currentPath) {{
         // Fix: Ensure path is a string, not an Event object
         if (typeof path !== 'string') path = currentPath;

         currentPath = path;
         pathDisplay.textContent = path ? '/ ' + path : '/';
         
         const res = await fetch(`/api/files?path=${{encodeURIComponent(path)}}`);
         if (res.status === 401) return location.href = '/login';
         const data = await res.json();
         
         fileList.innerHTML = '';
         if (path) {{
            const parts = path.split('/');
            parts.pop();
            const upPath = parts.join('/');
            const div = document.createElement('div');
            div.className = 'file-item';
            div.style.background = 'var(--surface-highlight)';
            div.innerHTML = `<div style="cursor:pointer; width:100%; display:flex; gap:12px; font-weight:600;" onclick="openPath('${{upPath}}')">Previous Directory</div>`;
            fileList.appendChild(div);
         }}

         if (data.files.length === 0) {{
           document.getElementById('emptyState').style.display = 'block';
         }} else {{
           document.getElementById('emptyState').style.display = 'none';
         }}

         data.files.forEach(f => {{
           const div = document.createElement('div');
           div.className = 'file-item';
           
           if (f.type === 'dir') {{
               const isGal = f.is_gallery;
               // Escaping for JS string safety
               const safeTitle = (f.title || f.name).replace(/'/g, "\\'");
               const safeDesc = (f.description || "").replace(/'/g, "\\'");
               const safeDate = (f.date || "");
               
               div.innerHTML = `
                 <div style="display:flex; align-items:center; gap:16px; flex:1; cursor:pointer;" onclick="openPath('${{f.path}}')">
                   <div class="file-preview" style="background:var(--surface-highlight); color:var(--primary); display:flex; align-items:center; justify-content:center;">{ICON_FOLDER}</div>
                   <div>
                       <div style="font-weight:600;">${{f.title || f.name}}</div>
                       ${{isGal ? '<small style="color:#eab308">★ Gallery Album</small>' : ''}}
                   </div>
                 </div>
                 <div style="display:flex; gap:4px; align-items:center;">
                    <button class="action-btn" onclick="openMetaModal('${{f.path}}', '${{safeTitle}}', '${{safeDesc}}', '${{safeDate}}')" title="Edit Info">✎</button>
                    <button class="action-btn" onclick="toggleGallery('${{f.path}}', ${{!isGal}})" title="Toggle Gallery">
                        ${{isGal ? `{ICON_STAR_FILLED}` : `{ICON_STAR}`}}
                    </button>
                    <button class="action-btn danger" onclick="deleteFile('${{f.path}}')" title="Delete">{ICON_TRASH}</button>
                 </div>
               `;
           }} else {{
               const isImg = getIcon(f.name) === 'img';
               const bg = isImg ? `url(${{f.url}})` : 'none';
               const iconHtml = isImg ? '' : `{ICON_FILE}`;
               
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
                    <a href="${{f.url}}" target="_blank" class="action-btn" title="Open">{ICON_OPEN}</a>
                    <button class="action-btn" onclick="copyUrl('${{f.url}}')" title="Copy Link">{ICON_COPY}</button>
                    <button class="action-btn danger" onclick="deleteFile('${{f.url.replace('/uploads/', '')}}')" title="Delete">{ICON_TRASH}</button>
                 </div>
               `;
           }}
           fileList.appendChild(div);
         }});
      }}

      window.openPath = (path) => fetchFiles(path);

      window.toggleGallery = async (path, enable) => {{
          const form = new FormData();
          form.append('path', path);
          form.append('enable', enable);
          try {{
            await fetch('/api/gallery/toggle', {{method:'POST', body:form}});
            fetchFiles(currentPath);
            showToast('Gallery Updated');
          }} catch(e) {{ alert(e); }}
      }};

      document.getElementById('createFolderBtn').addEventListener('click', async () => {{
          const name = document.getElementById('folderName').value;
          if (!name) return;
          const form = new FormData();
          form.append('name', name);
          form.append('path', currentPath);
          await fetch('/api/folder', {{method:'POST', body:form}});
          document.getElementById('folderName').value = '';
          fetchFiles(currentPath);
      }});

      window.copyUrl = async (url) => {{
        await navigator.clipboard.writeText(location.origin + url);
        showToast('Link copied');
      }};

      window.deleteFile = async (path) => {{
        if (!confirm('Permanently delete ' + path + '? Folder contents will be lost.')) return;
        const res = await fetch(`/api/files/${{encodeURIComponent(path)}}`, {{ method:'DELETE' }});
        if (res.ok) {{ showToast('Deleted'); fetchFiles(currentPath); }}
      }};


      uploadBtn.addEventListener('click', async () => {{
        if (queue.length === 0) return;
        
        uploadBtn.textContent = 'Uploading...';
        uploadBtn.disabled = true;
        
        try {{
            for (const f of queue) {{
              const form = new FormData();
              form.append('file', f);
              form.append('path', currentPath);
              
              const res = await fetch('/api/upload', {{ method:'POST', body:form }});
              if (!res.ok) {{
                  const txt = await res.text();
                  console.error('Upload failed', res.status, txt);
                  alert(`Upload failed: ${{res.status}}`);
              }}
            }}
            showToast('Upload Complete');
        }} catch(e) {{
            alert(`Network error: ${{e}}`);
        }} finally {{
            queue = [];
            uploadBtn.textContent = 'Start Upload';
            queueEl.textContent = '';
            fetchFiles(currentPath);
        }}
      }});

      // Remove default event listener in favor of onclick with correct arg
      // document.getElementById('refreshBtn').addEventListener('click', fetchFiles);
      fetchFiles();
    """
    return TEMPLATE_BASE.format(title="Upload | Yixun Hong", styles=STYLES, content=content, script=script)


@app.post("/api/upload")
async def upload_file_api(request: Request, file: UploadFile = File(...), path: str = Form("")) -> JSONResponse:
    require_login(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    
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
            chunk = await file.read(1024 * 1024 * 5) # 5MB chunks
            if not chunk:
                break
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


@app.post("/api/folder")
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


@app.post("/api/folder/meta")
def update_folder_meta(request: Request, path: str = Form(...), title: str = Form(...), description: str = Form(...), date: str = Form("")) -> JSONResponse:
    require_login(request)
    target = safe_join(UPLOAD_DIR, path)
    if not target.exists() or not target.is_dir():
         raise HTTPException(status_code=404, detail="Folder not found")
    
    save_folder_meta(target, title, description, date)
    return JSONResponse({"detail": "Updated"})


@app.post("/api/gallery/toggle")
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


@app.get("/api/files")
def list_files_api(request: Request, path: str = "") -> JSONResponse:
    require_login(request)
    
    target_dir = UPLOAD_DIR
    if path:
        target_dir = safe_join(UPLOAD_DIR, path)
    
    if not target_dir.exists():
         raise HTTPException(status_code=404, detail="Path not found")

    items: List[dict] = []
    gallery_set = set(get_gallery_folders())
    
    # Sort: Folders first, then files (by mtime desc)
    try:
        entries = list(target_dir.iterdir())
    except NotADirectoryError:
         raise HTTPException(status_code=400, detail="Not a directory")

    entries.sort(key=lambda x: (not x.is_dir(), -x.stat().st_mtime))
    
    for p in entries:
        rel_path = str(p.relative_to(UPLOAD_DIR))
        
        if p.is_dir():
            meta = get_folder_meta(p)
            items.append({
                "name": p.name,
                "type": "dir",
                "is_gallery": rel_path in gallery_set,
                "path": rel_path,
                "title": meta.get("title", p.name),
                "description": meta.get("description", ""),
                "date": meta.get("date", "")
            })
        else:
            items.append({
                "name": p.name,
                "type": "file",
                "size": p.stat().st_size,
                "url": f"/uploads/{rel_path}"
            })
            
    return JSONResponse({"files": items, "current_path": path})


@app.delete("/api/files/{path:path}")
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


@app.get("/api/files/{file_path:path}")
def download_file_api(file_path: str) -> FileResponse:
    target = safe_join(UPLOAD_DIR, file_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)