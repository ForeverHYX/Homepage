from typing import Optional, Any
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import re
import markdown

from fastapi import APIRouter, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import (
    UPLOAD_DIR, ARTICLES_DIR,
    limiter,
)
from app.utils import (
    parse_markdown_sections, render_markdown_file, get_gallery_folders, 
    safe_join, get_folder_meta, PdfExtension
)
from app.content_utils import get_about_info, parse_and_merge_news, get_all_articles, parse_education_timeline, get_raw_section_body

router = APIRouter()

# Template setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def _tags_url(current_tags: list[str], toggle: Optional[str] = None) -> str:
    """Build a tag toggle URL for the articles filter."""
    if not toggle:
        next_tags = current_tags
    elif toggle in current_tags:
        next_tags = [t for t in current_tags if t != toggle]
    else:
        next_tags = [*current_tags, toggle]
    if not next_tags:
        return "/articles"
    return f"/articles?tags={quote(','.join(next_tags))}"



def _build_home_payload() -> dict[str, Any]:
    about = get_about_info()
    avatar_url = "/uploads/avatar.png"
    raw_sections = parse_markdown_sections("content.md")

    section_colors = ["#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6"]
    sections = []
    for index, (title, body_html) in enumerate(raw_sections):
        # Use special timeline renderer for Education section
        if title.lower() == "education":
            raw_edu_md = get_raw_section_body("content.md", "Education")
            timeline_html = parse_education_timeline(raw_edu_md)
            if timeline_html:
                body_html = timeline_html
        sections.append({
            "title": title,
            "body_html": body_html,
            "accent_color": section_colors[index % len(section_colors)],
        })

    if not sections:
        raw_html = render_markdown_file("content.md")
        sections.append({
            "title": "",
            "body_html": raw_html,
            "accent_color": section_colors[0],
        })

    sections_html = ""
    for section in sections:
        title_html = ""
        if section["title"]:
            title_html = (
                f'<h2 class="section-title" style="border-left-color: {section["accent_color"]}">'
                f'{section["title"]}</h2>'
            )
        sections_html += f"""
        <section class="cv-section">
            {title_html}
            <div class="prose">
                {section["body_html"]}
            </div>
        </section>
        """

    news_html = parse_and_merge_news(limit=6)
    all_news_html = parse_and_merge_news(limit=100)

    return {
        "about": about,
        "avatar_url": avatar_url,
        "sections": sections,
        "sections_html": sections_html,
        "news_html": news_html,
        "all_news_html": all_news_html,
    }


def _build_articles_payload(tags: Optional[str] = None) -> dict[str, Any]:
    articles = get_all_articles()
    all_tags: dict[str, int] = {}
    for article in articles:
        for article_tag in article.get("tags", []):
            if article_tag:
                all_tags[article_tag] = all_tags.get(article_tag, 0) + 1

    # Parse comma-separated tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    filtered_articles = articles
    if tag_list:
        filtered_articles = [article for article in articles if all(t in article.get("tags", []) for t in tag_list)]

    sorted_tags = sorted(all_tags.items(), key=lambda item: item[1], reverse=True)

    return {
        "articles": filtered_articles,
        "filter_tags": tag_list,
        "sorted_tags": sorted_tags,
    }


def _build_gallery_payload(focus: Optional[str] = None) -> dict[str, Any]:
    gallery_dirs = get_gallery_folders()
    is_focused = False
    if focus and focus in gallery_dirs:
        gallery_dirs = [focus]
        is_focused = True

    albums = []
    for rel_path in gallery_dirs:
        path = safe_join(UPLOAD_DIR, rel_path)
        if not path.exists() or not path.is_dir():
            continue

        images = []
        try:
            for file in sorted(list(path.iterdir()), key=lambda item: item.name):
                if file.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                    rel_file_path = file.relative_to(UPLOAD_DIR)
                    images.append(f"/uploads/{rel_file_path}")
        except Exception:
            continue

        if not images:
            continue

        meta = get_folder_meta(path)
        sort_ts = 0.0
        date_str = meta.get("date", "")
        if date_str:
            try:
                sort_ts = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
            except ValueError:
                pass
        if sort_ts == 0.0:
            try:
                sort_ts = max(item.stat().st_mtime for item in path.iterdir())
                date_str = datetime.fromtimestamp(sort_ts).strftime("%Y-%m-%d")
            except Exception:
                pass

        if is_focused:
            title_style = "font-size:2.5rem; font-weight:600; margin:0 0 16px 0; text-transform:capitalize; border-left: 6px solid var(--primary); padding-left: 16px; line-height: 1.2; color:var(--heading);"
            meta_style = "display:flex; gap:24px; color:var(--muted); font-size:15px; padding-left:22px; margin-bottom:16px;"
            desc_style = "margin:0 0 24px 0; padding-left:22px; color:var(--text); font-size:1rem; line-height:1.6;"
            card_padding = "padding:40px;"
            card_margin = "margin-bottom:60px;"
            nav_margin = "margin-bottom:24px;"
        else:
            title_style = "font-size:1.5rem; font-weight:700; margin:0 0 12px 0; text-transform:capitalize; line-height: 1.2; color:var(--heading);"
            meta_style = "font-size:13px; color:var(--muted); margin-bottom:12px; display:flex; gap:16px; align-items:center; flex-wrap:wrap;"
            desc_style = "color:var(--text); font-size:15px; margin:0 0 16px 0; line-height:1.6;"
            card_padding = "padding:24px;"
            card_margin = "margin-bottom:24px;"
            nav_margin = "margin-bottom:16px;"

        albums.append({
            "path_name": path.name,
            "rel_path": rel_path,
            "title": meta.get("title", path.name),
            "desc": meta.get("description", ""),
            "date_str": date_str,
            "author": meta.get("author", "Yixun Hong"),
            "images": images,
            "sort_ts": sort_ts,
            "title_style": title_style,
            "meta_style": meta_style,
            "desc_style": desc_style,
            "card_padding": card_padding,
            "card_margin": card_margin,
            "nav_margin": nav_margin,
            "wrapper_class": "carousel-wrapper focused" if is_focused else "carousel-wrapper",
        })

    albums.sort(key=lambda album: album["sort_ts"], reverse=True)
    return {
        "albums": albums,
        "is_focused": is_focused,
        "focus": focus,
    }


def _build_article_detail_payload(slug: str) -> dict[str, Any]:
    path = ARTICLES_DIR / f"{slug}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Article not found")

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    body_lines = []
    title, author, date_str = "", "Yixun Hong", ""
    tags: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not title and stripped.startswith("# "):
            title = stripped[2:].strip()
            continue
        if stripped.lower().startswith("**date**:") or stripped.lower().startswith("date:"):
            date_str = stripped.split(":", 1)[1].strip()
            continue
        if stripped.lower().startswith("**author**:") or stripped.lower().startswith("author:"):
            author = stripped.split(":", 1)[1].strip()
            continue
        if stripped.lower().startswith("**tags**:") or stripped.lower().startswith("tags:") or stripped.lower().startswith("tag:"):
            tag_str = stripped.split(":", 1)[1].strip()
            tags = [tag.strip() for tag in tag_str.split(",") if tag.strip()]
            continue
        if stripped.lower().startswith("**abstract**:") or stripped.lower().startswith("abstract:"):
            continue
        body_lines.append(line)

    clean_body = "\n".join(body_lines)
    words = re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fa5]", clean_body)
    word_count = len(words)
    read_time = max(1, round(word_count / 200))

    icon_clock = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; position:relative; top:2px;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
    markdown_renderer = markdown.Markdown(extensions=["fenced_code", "tables", "toc", PdfExtension()])
    html_body = markdown_renderer.convert(clean_body)
    toc_html = markdown_renderer.toc

    if not title:
        title = slug.replace("-", " ").title()

    tags_html = ""
    for tag in tags:
        tags_html += f'<span class="chip article-tag-chip">{tag}</span>'

    return {
        "slug": slug,
        "title": title,
        "html_body": html_body,
        "toc_html": toc_html,
        "date_str": date_str,
        "author": author,
        "word_count": word_count,
        "read_time": read_time,
        "tags_html": tags_html,
        "tags": tags,
        "icon_clock": icon_clock,
    }



@router.get("/api/site/home")
def home_api() -> Any:
    payload = _build_home_payload()
    return JSONResponse(payload, headers={"Cache-Control": "public, max-age=60"})


@router.get("/api/search-index")
def search_api():
    data = []
    for a in get_all_articles():
        data.append({
            "type": "Article", "title": a['title'], "desc": a['summary'],
            "tags": a.get('tags', []), "date": a['date'],
            "url": f"/articles/{a['slug']}"
        })
    for rel_path in get_gallery_folders():
        path = safe_join(UPLOAD_DIR, rel_path)
        if not path.exists(): continue
        meta = get_folder_meta(path)
        data.append({
            "type": "Album", "title": meta.get("title", path.name),
            "desc": meta.get("description", ""), "tags": [],
            "date": meta.get("date", ""), "url": f"/gallery?focus={rel_path}"
        })
    return JSONResponse(data)



@router.get("/api/site/articles")
def articles_api(tag: Optional[str] = None, tags: Optional[str] = None) -> Any:
    # Support both old single-tag and new multi-tag param
    effective_tags = tags if tags else tag
    return JSONResponse(_build_articles_payload(effective_tags), headers={"Cache-Control": "public, max-age=60"})
    return JSONResponse(_build_articles_payload(tag), headers={"Cache-Control": "public, max-age=60"})



@router.get("/api/site/gallery")
def gallery_api(focus: Optional[str] = None) -> Any:
    return JSONResponse(_build_gallery_payload(focus), headers={"Cache-Control": "public, max-age=60"})



@router.get("/api/site/articles/{slug}")
def article_detail_api(slug: str) -> Any:
    return JSONResponse(_build_article_detail_payload(slug), headers={"Cache-Control": "public, max-age=300"})


@router.post("/api/revalidate-gallery")
def revalidate_gallery():
    """No-op: with direct FastAPI rendering there is no Next.js cache to bust."""
    return JSONResponse({"revalidated": True, "now": datetime.now().timestamp()})


# ============================================
# HTML Page Routes (Jinja2 templates)
# ============================================

@router.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    payload = _build_home_payload()
    return templates.TemplateResponse(request, "pages/home.html", {
        "about": payload["about"],
        "avatar_url": payload["avatar_url"],
        "sections": payload["sections"],
        "news_html": payload["news_html"],
        "all_news_html": payload["all_news_html"],
    })


@router.get("/articles", response_class=HTMLResponse)
def articles_page(request: Request, tags: Optional[str] = None):
    payload = _build_articles_payload(tags)
    return templates.TemplateResponse(request, "pages/articles.html", {
        "articles": payload["articles"],
        "filter_tags": payload["filter_tags"],
        "sorted_tags": payload["sorted_tags"],
        "tags_url": _tags_url,
    })


@router.get("/articles/{slug}", response_class=HTMLResponse)
def article_detail_page(request: Request, slug: str):
    try:
        article = _build_article_detail_payload(slug)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Article not found")
    return templates.TemplateResponse(request, "pages/article_detail.html", {
        "article": article,
    })


@router.get("/gallery", response_class=HTMLResponse)
def gallery_page(request: Request, focus: Optional[str] = None):
    payload = _build_gallery_payload(focus)
    return templates.TemplateResponse(request, "pages/gallery.html", {
        "albums": payload["albums"],
        "is_focused": payload["is_focused"],
        "focus": payload["focus"],
    })


@router.get("/resume", response_class=HTMLResponse)
def resume_page(request: Request):
    return templates.TemplateResponse(request, "pages/resume.html", {})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "pages/login.html", {})


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(request, "pages/upload.html", {})


