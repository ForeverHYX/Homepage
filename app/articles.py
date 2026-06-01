from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import List
import markdown
from app.config import ARTICLES_DIR
from app.cache import cache_by_mtime

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
