from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any

import markdown

from app.cache import _cache
from app.config import EXAMS_DIR
from app.markdown_utils import PdfExtension


def _exams_mtime() -> float:
    mtime = 0.0
    if EXAMS_DIR.exists():
        for path in EXAMS_DIR.glob("*.md"):
            if path.is_file():
                mtime = max(mtime, path.stat().st_mtime)
    return mtime


def _parse_exam_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = path.stem.replace("-", " ").title()
    date_str = ""
    author = "Yixun Hong"
    summary = ""
    tags: list[str] = []
    body_lines: list[str] = []
    title_set = False

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if not title_set and stripped.startswith("# "):
            title = stripped[2:].strip()
            title_set = True
            continue
        if lower.startswith("date:") or lower.startswith("**date**:"):
            date_str = stripped.split(":", 1)[1].strip()
            continue
        if lower.startswith("author:") or lower.startswith("**author**:"):
            author = stripped.split(":", 1)[1].strip()
            continue
        if lower.startswith("tags:") or lower.startswith("tag:") or lower.startswith("**tags**:"):
            tag_str = stripped.split(":", 1)[1].strip()
            tags = [tag.strip() for tag in tag_str.split(",") if tag.strip()]
            continue
        if lower.startswith("abstract:") or lower.startswith("summary:") or lower.startswith("**abstract**:"):
            summary = stripped.split(":", 1)[1].strip()
            continue
        body_lines.append(line)

    clean_body = "\n".join(body_lines)
    if not summary:
        plain = re.sub(r"<[^>]+>", " ", clean_body)
        plain = re.sub(r"[#*_`>\[\]()-]+", " ", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        summary = f"{plain[:220]}..." if len(plain) > 220 else plain

    sort_ts = path.stat().st_mtime
    if date_str:
        for fmt in ("%Y-%m-%d", "%Y-%m"):
            try:
                sort_ts = datetime.strptime(date_str, fmt).timestamp()
                break
            except ValueError:
                continue

    words = re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fa5]", clean_body)
    renderer = markdown.Markdown(extensions=["fenced_code", "tables", "toc", PdfExtension()])
    html_body = renderer.convert(clean_body)

    return {
        "slug": path.stem,
        "title": title,
        "date": datetime.fromtimestamp(sort_ts).strftime("%Y-%m-%d"),
        "date_str": date_str,
        "author": author,
        "summary": summary,
        "tags": tags,
        "mtime": sort_ts,
        "word_count": len(words),
        "read_time": max(1, round(len(words) / 200)),
        "html_body": html_body,
        "toc_html": renderer.toc,
    }


def get_all_exams() -> list[dict[str, Any]]:
    cache_key = f"exams:{EXAMS_DIR.resolve()}"
    mtime = _exams_mtime()
    entry = _cache.get(cache_key)
    if entry and entry.get("mtime") == mtime:
        return entry["value"]

    exams = [_parse_exam_markdown(path) for path in EXAMS_DIR.glob("*.md")]
    value = sorted(exams, key=lambda item: item["mtime"], reverse=True)
    _cache[cache_key] = {"mtime": mtime, "value": value}
    return value


def get_exam_detail(slug: str) -> dict[str, Any] | None:
    path = EXAMS_DIR / f"{slug}.md"
    if not path.exists() or not path.is_file():
        return None
    exam = _parse_exam_markdown(path)
    exam["tags_html"] = "".join(f'<span class="chip article-tag-chip">{tag}</span>' for tag in exam["tags"])
    exam["back_url"] = "/exams"
    exam["back_label"] = "Back to Exams"
    exam["icon_clock"] = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; position:relative; top:2px;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
    return exam
