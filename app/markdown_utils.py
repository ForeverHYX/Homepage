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


def _render_publication(fields: dict[str, str]) -> str:
    title = fields.get("title", "").strip()
    venue = fields.get("venue", "").strip()
    authors = fields.get("authors", "").strip()
    keywords = _split_publication_keywords(fields.get("keywords", fields.get("tags", "")))

    title_html = _render_inline_markdown(title) if title else ""
    venue_html = _render_inline_markdown(venue) if venue else ""
    authors_html = _render_inline_markdown(authors) if authors else ""

    tag_html = "".join(
        f'<span class="publication-keyword">{escape(keyword)}</span>'
        for keyword in keywords
    )
    tag_group = f'<div class="publication-keywords">{tag_html}</div>' if tag_html else ""

    links = []
    for kind, label in (("paper", "Paper"), ("code", "Code")):
        href = fields.get(kind, "").strip()
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
        f'<div class="publication-title"><strong>{title_html}</strong></div>'
        f'<div class="publication-venue"><em>{venue_html}</em></div>'
        f'<div class="publication-authors">{authors_html}</div>'
        f'{footer}'
        '</article>'
    )


def _parse_publication_block(lines: list[str]) -> str:
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
    return _render_publication(fields)


def _preprocess_publication_blocks(text: str) -> str:
    output: list[str] = []
    block: list[str] = []
    in_publication = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == ":::publication":
            in_publication = True
            block = []
            continue
        if in_publication and stripped == ":::":
            output.append(_parse_publication_block(block))
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
    if not path.exists():
        return []
    return cache_by_mtime(path, lambda: _parse_sections_raw(path))

def _render_markdown_raw(path: Path) -> str:
    text = _preprocess_publication_blocks(path.read_text(encoding="utf-8"))
    return markdown.markdown(text, extensions=["fenced_code", "tables", "toc", PdfExtension()])

def render_markdown_file(filename: str) -> str:
    path = CONTENT_DIR / filename
    if not path.exists():
        return ""
    return cache_by_mtime(path, lambda: _render_markdown_raw(path))
