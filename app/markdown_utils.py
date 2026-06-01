from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
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


def _parse_sections_raw(path: Path) -> List[Tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
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
    text = path.read_text(encoding="utf-8")
    return markdown.markdown(text, extensions=["fenced_code", "tables", "toc", PdfExtension()])

def render_markdown_file(filename: str) -> str:
    path = CONTENT_DIR / filename
    if not path.exists():
        return ""
    return cache_by_mtime(path, lambda: _render_markdown_raw(path))
