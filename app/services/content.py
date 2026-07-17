"""Presentation payloads derived from the Markdown content store."""

from __future__ import annotations

import re
from typing import Any

from app.assets import upload_url
from app.content_utils import (
    get_about_info,
    get_raw_section_body,
    parse_education_timeline,
)
from app.markdown_utils import (
    get_publications,
    parse_markdown_sections,
    render_markdown_file,
)
from app.news import parse_and_merge_news


SECTION_ACCENTS = {
    "introduction": "#38bdf8",
    "education": "#3b82f6",
    "selected publication": "#6366f1",
    "awards": "#2563eb",
    "teaching": "#0ea5e9",
    "projects": "#6366f1",
    "research": "#38bdf8",
    "experience": "#0ea5e9",
    "skills": "#3b82f6",
    "contact": "#60a5fa",
}
DEFAULT_SECTION_ACCENT = "#3b82f6"


def _homepage_sections() -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    for index, (title, body_html) in enumerate(parse_markdown_sections("content.md")):
        normalized_title = title.casefold().strip()
        if normalized_title == "education":
            education_markdown = get_raw_section_body("content.md", "Education")
            body_html = parse_education_timeline(education_markdown) or body_html
        slug = re.sub(r"[^a-z0-9]+", "-", normalized_title).strip("-")
        sections.append(
            {
                "title": title,
                "body_html": body_html,
                "accent_color": SECTION_ACCENTS.get(
                    normalized_title,
                    DEFAULT_SECTION_ACCENT,
                ),
                "accent_class": f"section-{slug or f'section-{index}'}",
            }
        )
    if sections:
        return sections
    return [
        {
            "title": "",
            "body_html": render_markdown_file("content.md"),
            "accent_color": DEFAULT_SECTION_ACCENT,
            "accent_class": "section-default",
        }
    ]


def _legacy_sections_html(sections: list[dict[str, str]]) -> str:
    fragments: list[str] = []
    for section in sections:
        title_html = ""
        if section["title"]:
            title_html = (
                '<h2 class="section-title" style="border-left-color: '
                f'{section["accent_color"]}">{section["title"]}</h2>'
            )
        fragments.append(
            f"""
            <section class="cv-section">
                {title_html}
                <div class="prose">
                    {section["body_html"]}
                </div>
            </section>
            """
        )
    return "".join(fragments)


def build_home_payload(*, include_legacy_fields: bool = True) -> dict[str, Any]:
    sections = _homepage_sections()
    payload: dict[str, Any] = {
        "about": get_about_info(),
        "avatar_url": upload_url("avatar.png"),
        "sections": sections,
        "news_html": parse_and_merge_news(limit=6),
    }
    if include_legacy_fields:
        payload["sections_html"] = _legacy_sections_html(sections)
        payload["all_news_html"] = parse_and_merge_news(limit=100)
    return payload


def build_publications_payload(keywords: str | None = None) -> dict[str, Any]:
    publications = get_publications()
    keyword_counts: dict[str, int] = {}
    for publication in publications:
        for keyword in publication.get("keywords", []):
            if keyword:
                normalized = str(keyword)
                keyword_counts[normalized] = keyword_counts.get(normalized, 0) + 1

    selected_keywords = [
        keyword.strip() for keyword in (keywords or "").split(",") if keyword.strip()
    ]
    filtered_publications = publications
    if selected_keywords:
        filtered_publications = [
            publication
            for publication in publications
            if all(keyword in publication.get("keywords", []) for keyword in selected_keywords)
        ]
    return {
        "publications": filtered_publications,
        "filter_keywords": selected_keywords,
        "sorted_keywords": sorted(
            keyword_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ),
    }
