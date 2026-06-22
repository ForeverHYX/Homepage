from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
import markdown
from app.config import CONTENT_DIR, ARTICLES_DIR, UPLOAD_DIR, GALLERY_CONFIG_FILE
from app.articles import get_all_articles
from app.utils import get_gallery_folders, get_folder_meta, safe_join

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
    from app.articles import _articles_mtime
    news_mtime = (CONTENT_DIR / "news.md").stat().st_mtime if (CONTENT_DIR / "news.md").exists() else 0
    art_mtime = _articles_mtime()
    gal_mtime = GALLERY_CONFIG_FILE.stat().st_mtime if GALLERY_CONFIG_FILE.exists() else 0
    combined = f"{news_mtime}-{art_mtime}-{gal_mtime}-{limit}"
    from app.cache import _cache
    cache_key = f"news_html:{combined}"
    entry = _cache.get(cache_key)
    if entry:
        return entry["value"]
    value = _build_news_html(limit)
    _cache[cache_key] = {"value": value}
    return value
