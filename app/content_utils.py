from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import json

import markdown
from app.config import ARTICLES_DIR, CONTENT_DIR, UPLOAD_DIR
from app.cache import cache_by_mtime
from app.utils import PdfExtension, get_gallery_folders, get_folder_meta, safe_join

def _articles_mtime() -> float:
    """Return the most recent mtime among all files in ARTICLES_DIR."""
    mtime = 0.0
    if ARTICLES_DIR.exists():
        for f in ARTICLES_DIR.iterdir():
            if f.is_file():
                mtime = max(mtime, f.stat().st_mtime)
    return mtime

def _build_articles_list() -> List[dict]:
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
        tags = []
        
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

            if line_strip.lower().startswith("**tags**:") or line_strip.lower().startswith("tags:") or line_strip.lower().startswith("tag:"):
                tag_str = line_strip.split(":", 1)[1].strip()
                # Split by comma
                tags = [t.strip() for t in tag_str.split(",") if t.strip()]
                continue
                
            if line_strip.lower().startswith("**abstract**:") or line_strip.lower().startswith("abstract:"):
                summary = line_strip.split(":", 1)[1].strip()
                continue
                
            # Content for summary (skip headers and empty lines)
            if not line_strip or line_strip.startswith("#") or line_strip.startswith("!"):
                continue
            content_lines.append(line_strip)
            
        # Generate Summary (first ~200 chars) if no abstract provided
        if not summary:
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
            "tags": tags,
            "mtime": mtime
        })
    
    # Sort by time desc
    return sorted(articles, key=lambda x: x["mtime"], reverse=True)

def get_all_articles() -> List[dict]:
    """Cached articles list keyed by directory mtime."""
    mtime = _articles_mtime()
    # We use a synthetic path key so cache_by_mtime can work
    key_path = ARTICLES_DIR / ".articles_cache"
    # Fake mtime: touch the key file to reflect current mtime
    # Simpler: use a custom in-memory cache with mtime key
    from app.cache import _cache
    cache_key = f"articles:{ARTICLES_DIR.resolve()}"
    entry = _cache.get(cache_key)
    if entry and entry.get("mtime") == mtime:
        return entry["value"]
    value = _build_articles_list()
    _cache[cache_key] = {"mtime": mtime, "value": value}
    return value


def _build_news_html(limit: int) -> str:
    """Parses news.md and merges with articles and galleries, sorting by date."""
    items = []
    
    # 1. Parse Manual News (from news.md)
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

    # 3. Parse Galleries
    for rel_path in get_gallery_folders():
        try:
            folder_path = safe_join(UPLOAD_DIR, rel_path)
            if not folder_path.exists():
                continue
            meta = get_folder_meta(folder_path)
            # Use date from meta, fallback to empty
            date_val = meta.get("date", "")
            
            dt = datetime.min
            if date_val:
                try:
                    # Try various formats
                    if len(date_val) == 10:
                        dt = datetime.strptime(date_val, "%Y-%m-%d")
                    elif len(date_val) == 7:
                        dt = datetime.strptime(date_val, "%Y-%m")
                except ValueError:
                    pass
            
            # Only add if we have a valid date parsed (assuming news feed is date-driven)
            if dt != datetime.min:
                date_str = dt.strftime("%Y-%m")
                title = meta.get("title", rel_path)
                items.append({
                    "date": dt,
                    "html": f"<strong>{date_str}:</strong> New album released: <a href=\"/gallery?focus={rel_path}\">{title}</a>."
                })
        except Exception:
            pass
        
    # 4. Sort by date desc
    items.sort(key=lambda x: x["date"], reverse=True)
    
    # 5. Limit 
    # Use limit currently passed
    visible_items = items[:limit]
    
    # 6. Render
    if not items:
        return '<ul class="news-list"><li class="news-item">No news yet.</li></ul>'
        
    html = '<ul class="news-list">'
    for item in visible_items:
        html += f'<li class="news-item">{item["html"]}</li>'
    html += '</ul>'
    
    return html

def parse_and_merge_news(limit: int = 6) -> str:
    """Cached news HTML keyed by news.md mtime + articles mtime + gallery config mtime."""
    news_mtime = (CONTENT_DIR / "news.md").stat().st_mtime if (CONTENT_DIR / "news.md").exists() else 0
    art_mtime = _articles_mtime()
    gal_mtime = (UPLOAD_DIR / "gallery_config.json").stat().st_mtime if (UPLOAD_DIR / "gallery_config.json").exists() else 0
    combined = f"{news_mtime}-{art_mtime}-{gal_mtime}-{limit}"
    from app.cache import _cache
    cache_key = f"news_html:{combined}"
    entry = _cache.get(cache_key)
    if entry:
        return entry["value"]
    value = _build_news_html(limit)
    _cache[cache_key] = {"value": value}
    return value


def _parse_about_info(path: Path) -> dict:
    """Parses about.md for structured info."""
    default = {
        "email": "#", "github": "#", "location": "Earth", 
        "name": "Yixun Hong", "role": "Student / Researcher"
    }
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
            
    if "## Role" in text:
        parts = text.split("## Role")
        if len(parts) > 1:
            # Take the first non-empty line after the header
            lines = parts[1].strip().split("\n")
            if lines:
                info["role"] = lines[0].strip()

    # Allow overriding name/role via comments or specific syntax if needed, 
    # but for now we keep them hardcoded or minimal as requested.
    
    return info

def get_about_info() -> dict:
    """Cached about info keyed by about.md mtime."""
    path = CONTENT_DIR / "about.md"
    return cache_by_mtime(path, lambda: _parse_about_info(path))


def get_raw_section_body(filename: str, section_title: str) -> str:
    """Read a markdown file and return the raw text body for a specific H1 section."""
    path = CONTENT_DIR / filename
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    current_title = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.strip().startswith("# "):
            if current_title.lower() == section_title.lower():
                return "\n".join(current_lines)
            current_title = line.strip()[2:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title.lower() == section_title.lower():
        return "\n".join(current_lines)
    return ""



def parse_education_timeline(raw_markdown: str) -> str:
    """
    Parses the Education section markdown into a timeline HTML.
    
    Expected format per entry:
        - **Institution Name** | date range
          *Role / Degree*
          ![Alt text](/path/to/logo.png)
    
    Returns timeline HTML or falls back to standard markdown rendering.
    """
    import re as _re
    
    lines = raw_markdown.splitlines()
    entries: list[dict] = []
    current_entry: dict | None = None
    
    for line in lines:
        stripped = line.strip()
        
        # New bullet item
        if stripped.startswith("- ") or stripped.startswith("* "):
            if current_entry:
                entries.append(current_entry)
            
            content = stripped[2:].strip()
            
            # Parse: **Institution** | date range
            inst_match = _re.match(r'\*\*(.+?)\*\*\s*\|\s*(.*)', content)
            if inst_match:
                current_entry = {
                    "institution": inst_match.group(1).strip(),
                    "date_range": inst_match.group(2).strip(),
                    "role": "",
                    "logos": [],
                }
            else:
                # Fallback: just bold text without pipe
                bold_match = _re.match(r'\*\*(.+?)\*\*(.*)', content)
                if bold_match:
                    current_entry = {
                        "institution": bold_match.group(1).strip(),
                        "date_range": bold_match.group(2).strip().lstrip("(").rstrip(")").strip(),
                        "role": "",
                        "logos": [],
                    }
                else:
                    current_entry = None
            continue
        
        # Continuation lines (indented)
        if current_entry and stripped:
            # Role: *italic text*
            role_match = _re.match(r'^\*(.+?)\*$', stripped)
            if role_match:
                current_entry["role"] = role_match.group(1).strip()
                continue
            
            # Logo: ![alt](url)
            img_match = _re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', stripped)
            if img_match:
                for alt, url in img_match:
                    current_entry["logos"].append({"alt": alt, "url": url})
                continue
            
            # Additional description text (not italic, not image)
            if not stripped.startswith("#"):
                if current_entry["role"]:
                    current_entry["role"] += " " + stripped
                else:
                    current_entry["role"] = stripped
    
    # Flush last entry
    if current_entry:
        entries.append(current_entry)
    
    if not entries:
        return ""
    
    # Generate timeline HTML
    html_parts = ['<div class="edu-timeline">']
    for entry in entries:
        is_active = "present" in entry["date_range"].lower()
        active_class = " is-active" if is_active else ""
        
        # Logos
        logos_html = ""
        if entry["logos"]:
            logo_imgs = "".join(
                f'<img src="{logo["url"]}" alt="{logo["alt"]}" class="edu-logo">'
                for logo in entry["logos"]
            )
            logos_html = f'<div class="edu-logo-group">{logo_imgs}</div>'
        
        # Role (support markdown links in role text)
        role_text = entry["role"]
        if role_text:
            # Convert inline markdown links [text](url)
            role_text = _re.sub(
                r'\[([^\]]+)\]\(([^)]+)\)',
                r'<a href="\2" class="link-styled">\1</a>',
                role_text
            )
            # Convert bold
            role_text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', role_text)
            # Convert italic
            role_text = _re.sub(r'\*(.+?)\*', r'<em>\1</em>', role_text)
        
        role_html = f'<p class="edu-role">{role_text}</p>' if role_text else ""
        
        html_parts.append(f'''
            <div class="edu-timeline-item{active_class}">
                <div class="edu-timeline-date">
                    <span>{entry["date_range"]}</span>
                </div>
                <div class="edu-timeline-marker">
                    <div class="edu-timeline-dot"></div>
                </div>
                <div class="edu-timeline-content">
                    <div class="edu-timeline-text">
                        <span class="edu-institution">{entry["institution"]}</span>
                        {role_html}
                    </div>
                    {logos_html}
                </div>
            </div>''')
    
    html_parts.append('</div>')
    return "\n".join(html_parts)

