from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.cache import cache_by_mtime
from app.config import CONTENT_DIR
from app.education import parse_education_timeline as _parse_education_timeline
from app.news import parse_and_merge_news


def _parse_about_info(path: Path) -> dict:
    """Parses about.md for structured info."""
    default = {
        "email": "#",
        "github": "#",
        "location": "Earth",
        "name": "Yixun Hong",
        "role": "Student / Researcher",
    }
    if not path.exists():
        return default

    text = path.read_text(encoding="utf-8")
    info = default.copy()

    # Simple regex extraction
    if match := re.search(r"\((mailto:[^)]+)\)", text):
        info["email"] = match.group(1)
    if match := re.search(r"\((https://github[^)]+)\)", text):
        info["github"] = match.group(1)
    
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
    return cache_by_mtime(
        path,
        lambda: _parse_about_info(path),
        namespace="about_info",
    )


def _parse_raw_sections(path: Path) -> dict[str, str]:
    """Parse every H1 body once while preserving the first duplicate title."""
    sections: dict[str, str] = {}
    current_title = ""
    current_lines: list[str] = []

    def store_section() -> None:
        key = current_title.casefold()
        sections.setdefault(key, "\n".join(current_lines))

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            store_section()
            current_title = stripped[2:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    store_section()
    return sections


def get_raw_section_body(filename: str, section_title: str) -> str:
    """Read a markdown file and return the raw text body for a specific H1 section."""
    path = CONTENT_DIR / filename
    if not path.exists():
        return ""
    sections = cache_by_mtime(
        path,
        lambda: _parse_raw_sections(path),
        namespace="raw_markdown_sections",
    )
    return sections.get(section_title.casefold(), "")


@lru_cache(maxsize=8)
def parse_education_timeline(raw_markdown: str) -> str:
    """Cache the pure Education renderer for unchanged homepage content."""
    return _parse_education_timeline(raw_markdown)
