from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
from html import escape
import re
import markdown
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension
from app.config import CONTENT_DIR
from app.cache import cache_by_mtime

class PdfTreeprocessor(Treeprocessor):
    def run(self, root):
        for element in root.iter():
            if element.tag == 'img':
                src = element.get('src')
                if src and src.lower().endswith('.pdf'):
                    element.tag = 'embed'
                    element.set('type', 'application/pdf')
                    element.set('style', 'width:100%; min-height:800px; border:none;')
                    if 'alt' in element.attrib:
                        del element.attrib['alt']

class PdfExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(PdfTreeprocessor(md), 'pdf_embed', 15)


def _render_inline_markdown(text: str) -> str:
    rendered = markdown.markdown(text.strip(), extensions=["fenced_code", "tables", "toc", PdfExtension()])
    if rendered.startswith("<p>") and rendered.endswith("</p>"):
        return rendered[3:-4]
    return rendered


def _split_publication_keywords(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;|]", value) if item.strip()]


def _publication_icon(kind: str) -> str:
    if kind == "paper":
        return (
            '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="15" height="15" '
            'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
            '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
            '<path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>'
            '</svg>'
        )
    return (
        '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="15" height="15" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/>'
        '</svg>'
    )



def _publication_kind(fields: dict[str, str], venue: str) -> str:
    explicit = fields.get("type", fields.get("kind", fields.get("category", ""))).strip().lower()
    if explicit in {"journal", "j", "transaction", "transactions"}:
        return "journal"
    if explicit in {"conference", "conf", "c", "proceedings"}:
        return "conference"

    venue_lower = venue.lower()
    if "journal" in venue_lower or "transactions" in venue_lower:
        return "journal"
    return "conference"


def _publication_index_label(kind: str, counters: dict[str, int]) -> str:
    key = "journal" if kind == "journal" else "conference"
    counters[key] = counters.get(key, 0) + 1
    prefix = "T" if key == "journal" else "C"
    return f"{prefix}{counters[key]}"


def _publication_venue_label(fields: dict[str, str], venue: str) -> str:
    explicit = fields.get("venue_short", fields.get("venue_label", fields.get("abbr", ""))).strip()
    if explicit:
        return explicit

    parenthetical = re.findall(r"\(([^()]{2,24})\)", venue)
    for candidate in reversed(parenthetical):
        compact = candidate.strip()
        if re.search(r"[A-Z]", compact) and not re.search(r"\s", compact):
            return compact
    return ""


def _parse_publication_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key = ""
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if match := re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", line):
            current_key = match.group(1).strip().lower().replace("-", "_")
            fields[current_key] = match.group(2).strip()
        elif current_key:
            fields[current_key] = f"{fields[current_key]} {line.strip()}".strip()
    return fields


def _build_publication(fields: dict[str, str], counters: dict[str, int]) -> dict[str, object]:
    title = fields.get("title", "").strip()
    venue = fields.get("venue", "").strip()
    authors = fields.get("authors", "").strip()
    keywords = _split_publication_keywords(fields.get("keywords", fields.get("tags", "")))
    publication_kind = _publication_kind(fields, venue)
    index_label = _publication_index_label(publication_kind, counters)
    venue_label = _publication_venue_label(fields, venue)

    return {
        "title": title,
        "title_html": _render_inline_markdown(title) if title else "",
        "venue": venue,
        "venue_html": _render_inline_markdown(venue) if venue else "",
        "authors": authors,
        "authors_html": _render_inline_markdown(authors) if authors else "",
        "keywords": keywords,
        "kind": publication_kind,
        "index_label": index_label,
        "venue_label": venue_label,
        "paper": fields.get("paper", "").strip(),
        "code": fields.get("code", "").strip(),
    }


def _render_publication_data(publication: dict[str, object]) -> str:
    title_html = str(publication["title_html"])
    venue_html = str(publication["venue_html"])
    authors_html = str(publication["authors_html"])
    publication_kind = str(publication["kind"])
    index_label = str(publication["index_label"])
    venue_label = str(publication["venue_label"])
    keywords = list(publication["keywords"])

    badge_html = f'<span class="publication-badge publication-index publication-index-{publication_kind}">{escape(index_label)}</span>'
    if venue_label:
        badge_html += f'<span class="publication-badge publication-venue-label">{escape(venue_label)}</span>'

    tag_html = "".join(
        f'<span class="publication-keyword">{escape(keyword)}</span>'
        for keyword in keywords
    )
    tag_group = f'<div class="publication-keywords">{tag_html}</div>' if tag_html else ""

    links = []
    for kind, label in (("paper", "Paper"), ("code", "Code")):
        href = str(publication[kind])
        if href:
            safe_href = escape(href, quote=True)
            links.append(
                f'<a class="publication-link publication-link-{kind}" href="{safe_href}" '
                f'target="_blank" rel="noreferrer" title="{label}" aria-label="{label}">'
                f'{_publication_icon(kind)}<span class="publication-link-label">{label}</span></a>'
            )
    link_group = f'<div class="publication-links">{"".join(links)}</div>' if links else ""
    footer = f'<div class="publication-footer">{tag_group}{link_group}</div>' if tag_group or link_group else ""

    return (
        '<article class="publication-entry">'
        '<div class="publication-heading">'
        f'<div class="publication-badges">{badge_html}</div>'
        '<div class="publication-copy">'
        f'<div class="publication-title"><strong>{title_html}</strong></div>'
        f'<div class="publication-venue"><em>{venue_html}</em></div>'
        f'<div class="publication-authors">{authors_html}</div>'
        f'{footer}'
        '</div>'
        '</div>'
        '</article>'
    )


def _render_publication(fields: dict[str, str], counters: dict[str, int]) -> str:
    return _render_publication_data(_build_publication(fields, counters))


def _parse_publication_block(lines: list[str], counters: dict[str, int]) -> str:
    return _render_publication(_parse_publication_fields(lines), counters)


def _publication_slug(title: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or fallback.lower()


def _parse_publications_raw(path: Path) -> list[dict[str, object]]:
    publications: list[dict[str, object]] = []
    counters = {"conference": 0, "journal": 0}
    slug_counts: dict[str, int] = {}
    block: list[str] = []
    in_publication = False

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == ":::publication":
            in_publication = True
            block = []
            continue
        if in_publication and stripped == ":::":
            publication = _build_publication(_parse_publication_fields(block), counters)
            base_slug = _publication_slug(
                str(publication["title"]),
                str(publication["index_label"]),
            )
            slug_counts[base_slug] = slug_counts.get(base_slug, 0) + 1
            publication["slug"] = (
                base_slug
                if slug_counts[base_slug] == 1
                else f"{base_slug}-{slug_counts[base_slug]}"
            )
            publication["html"] = _render_publication_data(publication)
            publications.append(publication)
            in_publication = False
            block = []
            continue
        if in_publication:
            block.append(line)

    return publications


def get_publications(filename: str = "content.md") -> list[dict[str, object]]:
    """Return structured publication blocks with stable badges and anchors."""
    path = CONTENT_DIR / filename
    return cache_by_mtime(
        path,
        lambda: _parse_publications_raw(path) if path.exists() else [],
        namespace="publications",
    )


def _preprocess_publication_blocks(text: str) -> str:
    output: list[str] = []
    block: list[str] = []
    counters = {"conference": 0, "journal": 0}
    in_publication = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == ":::publication":
            in_publication = True
            block = []
            continue
        if in_publication and stripped == ":::":
            output.append(_parse_publication_block(block, counters))
            in_publication = False
            block = []
            continue
        if in_publication:
            block.append(line)
        else:
            output.append(line)

    if in_publication:
        output.append(":::publication")
        output.extend(block)

    return "\n".join(output)

def _parse_sections_raw(path: Path) -> List[Tuple[str, str]]:
    text = _preprocess_publication_blocks(path.read_text(encoding="utf-8"))
    sections = []
    current_title = ""
    current_lines = []
    
    def flush():
        if current_title or current_lines:
            raw_body = "\n".join(current_lines)
            html_body = markdown.markdown(raw_body, extensions=["fenced_code", "tables", "toc", PdfExtension()])
            sections.append((current_title, html_body))

    for line in text.splitlines():
        if line.strip().startswith("# "):
            flush()
            current_title = line.strip()[2:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    
    # Filter out empty sections
    return [s for s in sections if s[0] or s[1]]

def parse_markdown_sections(filename: str) -> List[Tuple[str, str]]:
    """
    Parses a markdown file into sections based on H1 headers (# Header).
    Returns a list of (Title, HTML_Content) tuples.
    """
    path = CONTENT_DIR / filename
    return cache_by_mtime(
        path,
        lambda: _parse_sections_raw(path) if path.exists() else [],
        namespace="markdown_sections",
    )

def _render_markdown_raw(path: Path) -> str:
    text = _preprocess_publication_blocks(path.read_text(encoding="utf-8"))
    return markdown.markdown(text, extensions=["fenced_code", "tables", "toc", PdfExtension()])

def render_markdown_file(filename: str) -> str:
    path = CONTENT_DIR / filename
    return cache_by_mtime(
        path,
        lambda: _render_markdown_raw(path) if path.exists() else "",
        namespace="rendered_markdown",
    )
