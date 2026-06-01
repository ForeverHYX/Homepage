from __future__ import annotations
import re
from pathlib import Path

from app.config import CONTENT_DIR
from app.cache import cache_by_mtime

# Re-exports for backward compatibility
from app.articles import get_all_articles
from app.news import parse_and_merge_news
from app.education import parse_education_timeline


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
