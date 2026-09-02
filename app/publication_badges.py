"""Conference-aware badges for structured publication blocks."""

from __future__ import annotations

import re
from html import escape
from typing import Any


# Ordered and deliberately data-driven so new architecture venues can be added
# without changing the publication parser or templates.
CONFERENCE_BADGE_STYLES: tuple[dict[str, Any], ...] = (
    {
        "id": "micro",
        "aliases": (
            r"\bmicro\s*\d*\b",
            r"international symposium on microarchitecture",
        ),
    },
    {
        "id": "isca",
        "aliases": (
            r"\bisca\s*\d*\b",
            r"international symposium on computer architecture",
        ),
    },
    {
        "id": "hpca",
        "aliases": (
            r"\bhpca\s*\d*\b",
            r"high.performance computer architecture",
        ),
    },
    {
        "id": "asplos",
        "aliases": (
            r"\basplos\s*\d*\b",
            r"architectural support for programming languages",
        ),
    },
    {
        "id": "cgo",
        "aliases": (
            r"\bcgo\s*\d*\b",
            r"code generation and optimization",
        ),
    },
)

ARTIFACT_BADGE_LABELS = {
    "artifact available": ("artifact-available", "Artifact Available"),
    "available": ("artifact-available", "Artifact Available"),
    "artifact functional": ("artifact-functional", "Artifact Functional"),
    "artifact evaluated functional": ("artifact-functional", "Artifact Functional"),
    "functional": ("artifact-functional", "Artifact Functional"),
    "results reproduced": ("results-reproduced", "Results Reproduced"),
    "reproduced": ("results-reproduced", "Results Reproduced"),
}

ARTIFACT_BADGE_ICONS = {
    "artifact-available": (
        '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="M4 7h16v13H4z"/>'
        '<path d="M3 4h18v3H3z"/><path d="M9 11h6"/></svg>'
    ),
    "artifact-functional": (
        '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"><circle cx="12" cy="12" r="9"/>'
        '<path d="m8 12 2.5 2.5L16 9"/></svg>'
    ),
    "results-reproduced": (
        '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="M20 7v5h-5"/>'
        '<path d="M4 17v-5h5"/><path d="M6.1 9a7 7 0 0 1 11.2-2L20 9"/>'
        '<path d="M17.9 15A7 7 0 0 1 6.7 17L4 15"/></svg>'
    ),
}


def resolve_conference_style(*values: str) -> str:
    """Resolve the first configured architecture conference from publication fields."""
    haystack = " ".join(str(value or "") for value in values).casefold()
    for style in CONFERENCE_BADGE_STYLES:
        if any(re.search(pattern, haystack, flags=re.IGNORECASE) for pattern in style["aliases"]):
            return str(style["id"])
    return ""


def parse_artifact_badges(value: str) -> list[dict[str, str]]:
    """Parse pipe/comma/semicolon-separated artifact badges into safe view data."""
    badges: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in re.split(r"[,;|]", value or ""):
        raw_label = item.strip()
        if not raw_label:
            continue
        key = re.sub(r"[^a-z0-9]+", " ", raw_label.casefold()).strip()
        slug, label = ARTIFACT_BADGE_LABELS.get(
            key,
            (re.sub(r"[^a-z0-9]+", "-", key).strip("-") or "custom", raw_label),
        )
        if slug in seen:
            continue
        seen.add(slug)
        badges.append(
            {
                "slug": slug,
                "label": label,
                "icon_html": ARTIFACT_BADGE_ICONS.get(slug, ""),
            }
        )
    return badges


def render_artifact_badges(badges: list[dict[str, str]]) -> str:
    if not badges:
        return ""
    rendered = []
    for badge in badges:
        label = escape(str(badge["label"]))
        slug = escape(str(badge["slug"]), quote=True)
        icon = str(badge.get("icon_html", ""))
        rendered.append(
            f'<span class="publication-artifact-badge publication-artifact-{slug}" '
            f'title="{label}">{icon}<span>{label}</span></span>'
        )
    return (
        '<div class="publication-artifact-badges" aria-label="Artifact badges">'
        f"{''.join(rendered)}</div>"
    )
