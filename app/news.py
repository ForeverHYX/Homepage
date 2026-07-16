from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import markdown

from app.cache import FileSignature, cache_by_signature, file_signature
from app.config import CONTENT_DIR, GALLERY_CONFIG_FILE, UPLOAD_DIR
from app.utils import get_folder_meta, get_gallery_folders, safe_join


NEWS_CACHE_NAMESPACE = "news"
NEWS_ITEMS_CACHE_KEY = "merged_items"


class _NewsItem(TypedDict):
    date: datetime
    html: str


def _parse_news_date(value: str) -> datetime:
    for date_format, expected_length in (("%Y-%m-%d", 10), ("%Y-%m", 7)):
        if len(value) != expected_length:
            continue
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            return datetime.min
    return datetime.min


def _build_news_items() -> tuple[_NewsItem, ...]:
    """Parse manual news and gallery releases into one date-sorted sequence."""
    items: list[_NewsItem] = []

    news_path = CONTENT_DIR / "news.md"
    if news_path.exists():
        text = news_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not (line.startswith("- ") or line.startswith("* ")):
                continue

            content = line[2:].strip()
            match = re.match(r"\*\*(.*?)\*\*:(.*)", content)
            if not match:
                continue

            date_str = match.group(1).strip()
            body_raw = match.group(2).strip()
            body_html = markdown.markdown(body_raw).replace("<p>", "").replace("</p>", "")
            items.append(
                {
                    "date": _parse_news_date(date_str),
                    "html": f"<strong>{date_str}:</strong> {body_html}",
                }
            )

    for rel_path in get_gallery_folders():
        try:
            folder_path = safe_join(UPLOAD_DIR, rel_path)
            if not folder_path.exists():
                continue
            meta = get_folder_meta(folder_path)
            date_value = str(meta.get("date", ""))
            parsed_date = _parse_news_date(date_value)
            if parsed_date == datetime.min:
                continue

            date_str = parsed_date.strftime("%Y-%m")
            title = meta.get("title", rel_path)
            items.append(
                {
                    "date": parsed_date,
                    "html": (
                        f'<strong>{date_str}:</strong> New album released: '
                        f'<a href="/gallery?focus={rel_path}">{title}</a>.'
                    ),
                }
            )
        except Exception:
            # One malformed or missing album should not hide the remaining feed.
            continue

    items.sort(key=lambda item: item["date"], reverse=True)
    return tuple(items)


def _render_news_html(items: tuple[_NewsItem, ...], limit: int) -> str:
    if not items:
        return '<ul class="news-list"><li class="news-item">No news yet.</li></ul>'

    html_parts = ['<ul class="news-list">']
    html_parts.extend(
        f'<li class="news-item">{item["html"]}</li>' for item in items[:limit]
    )
    html_parts.append("</ul>")
    return "".join(html_parts)


def _build_news_html(limit: int) -> str:
    """Backward-compatible uncached renderer used by older integrations."""
    return _render_news_html(_build_news_items(), limit)


def _gallery_metadata_signatures() -> tuple[tuple[str, FileSignature], ...]:
    """Track visible album metadata even when files change outside the app."""
    signatures: list[tuple[str, FileSignature]] = []
    for rel_path in get_gallery_folders():
        try:
            meta_path = safe_join(UPLOAD_DIR, rel_path) / "meta.json"
        except Exception:
            continue
        signatures.append((str(meta_path.resolve()), file_signature(meta_path)))
    return tuple(sorted(signatures))


def parse_and_merge_news(limit: int = 6) -> str:
    """Render news while parsing all sources only once per input signature."""
    news_path = CONTENT_DIR / "news.md"
    signature = (
        (str(news_path.resolve()), file_signature(news_path)),
        (str(GALLERY_CONFIG_FILE.resolve()), file_signature(GALLERY_CONFIG_FILE)),
        _gallery_metadata_signatures(),
    )
    items = cache_by_signature(
        NEWS_ITEMS_CACHE_KEY,
        signature,
        _build_news_items,
        namespace=NEWS_CACHE_NAMESPACE,
    )
    return _render_news_html(items, limit)
