from __future__ import annotations
import os
import json
import secrets
from pathlib import Path
from typing import List, Tuple
from PIL import Image

from fastapi import HTTPException
import markdown
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension

from app.config import CONTENT_DIR, GALLERY_CONFIG_FILE

# --- Extensions ---

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


# --- Gallery Utilities ---

def get_gallery_folders() -> List[str]:
    if not GALLERY_CONFIG_FILE.exists():
        return []
    try:
        data = json.loads(GALLERY_CONFIG_FILE.read_text())
        return data.get("folders", [])
    except:
        return []

def toggle_gallery_folder(folder_path: str, enable: bool):
    folders = set(get_gallery_folders())
    if enable:
        folders.add(folder_path)
    else:
        folders.discard(folder_path)
    GALLERY_CONFIG_FILE.write_text(json.dumps({"folders": list(folders)}))

def get_folder_meta(folder_path: Path) -> dict:
    meta_file = folder_path / "meta.json"
    default = {"title": folder_path.name, "description": "", "date": ""}
    if meta_file.exists():
        try:
            stored = json.loads(meta_file.read_text())
            return {**default, **stored}
        except:
            pass
    return default

def save_folder_meta(folder_path: Path, title: str, description: str, date: str = ""):
    meta = {"title": title, "description": description, "date": date}
    (folder_path / "meta.json").write_text(json.dumps(meta))


# --- Image / File Utilities ---

def process_uploaded_image(file_path: Path) -> str:
    """Converts JPG to WebP and returns the new filename."""
    if file_path.suffix.lower() in ['.jpg', '.jpeg']:
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too huge (optional, but good for galleries)
                if max(img.size) > 1920:
                    img.thumbnail((1920, 1920))

                webp_path = file_path.with_suffix('.webp')
                img.save(webp_path, 'WEBP', quality=80)
            
            # Remove original
            file_path.unlink()
            return webp_path.name
        except Exception as e:
            print(f"Error converting image {file_path}: {e}")
    return file_path.name

def safe_join(base: Path, target: str) -> Path:
    candidate = (base / target).resolve()
    if base not in candidate.parents and candidate != base:
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate


# --- Markdown / Content Utilities ---

def parse_markdown_sections(filename: str) -> List[Tuple[str, str]]:
    """
    Parses a markdown file into sections based on H1 headers (# Header).
    Returns a list of (Title, HTML_Content) tuples.
    """
    path = CONTENT_DIR / filename
    if not path.exists():
        return []
    
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

def render_markdown_file(filename: str) -> str:
    path = CONTENT_DIR / filename
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    return markdown.markdown(text, extensions=["fenced_code", "tables", "toc", PdfExtension()])
