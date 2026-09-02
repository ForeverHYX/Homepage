"""Conference-aware badges for structured publication blocks."""

from __future__ import annotations

import re
from html import escape
from typing import Any

from app.assets import asset_url


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

ARTIFACT_BADGE_IMAGES = {
    "artifact-available": "images/publication-badges/artifacts_available.jpg",
    "artifact-functional": "images/publication-badges/artifacts_evaluated_functional.jpg",
    "results-reproduced": "images/publication-badges/results_reproduced.jpg",
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
                "image_path": ARTIFACT_BADGE_IMAGES.get(slug, ""),
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
        image_path = str(badge.get("image_path", ""))
        if image_path:
            image_src = escape(asset_url(image_path), quote=True)
            rendered.append(
                '<span class="publication-artifact-badge '
                f'publication-artifact-badge-official publication-artifact-{slug}" '
                f'role="img" aria-label="{label}" title="{label}">'
                f'<img src="{image_src}" width="104" height="104" alt="" '
                'loading="lazy" decoding="async">'
                f'<span class="visually-hidden">{label}</span></span>'
            )
        else:
            rendered.append(
                '<span class="publication-artifact-badge '
                f'publication-artifact-badge-text publication-artifact-{slug}" '
                f'title="{label}"><span>{label}</span></span>'
            )
    return (
        '<div class="publication-artifact-badges" aria-label="Artifact badges">'
        f"{''.join(rendered)}</div>"
    )
