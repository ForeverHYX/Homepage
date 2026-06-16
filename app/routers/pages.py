from typing import Optional, Any
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode
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
from app.daily import (
    build_daily_payload,
    daily_payload_search_entries,
    load_daily_payload,
)
from app.daily_articles import DAILY_ARTICLES_DIR, ensure_daily_article_markdown
from app.auth import get_current_user
from app.gallery_thumbnail_utils import ensure_gallery_thumbnail

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


def _daily_url(keywords: Optional[list[str]] = None, item_type: Optional[str] = None) -> str:
    params: dict[str, str] = {}
    if keywords:
        params["keywords"] = ",".join(keywords)
    if item_type in {"paper", "repository"}:
        params["item_type"] = item_type
    if not params:
        return "/daily"
    return f"/daily?{urlencode(params)}"


def _keywords_url(current_keywords: list[str], toggle: Optional[str] = None, item_type: Optional[str] = None) -> str:
    """Build a Daily keyword toggle URL."""
    if not toggle:
        next_keywords = current_keywords
    elif toggle in current_keywords:
        next_keywords = [keyword for keyword in current_keywords if keyword != toggle]
    else:
        next_keywords = [*current_keywords, toggle]
    return _daily_url(next_keywords, item_type)


def _daily_type_url(item_type: Optional[str] = None) -> str:
    """Build a Daily type filter URL. Switching type resets keyword filters."""
    return _daily_url([], item_type)



def _build_home_payload() -> dict[str, Any]:
    about = get_about_info()
    avatar_url = "/uploads/avatar.png"
    raw_sections = parse_markdown_sections("content.md")

    # Semantic per-section accent colors — a coordinated BLUE gradient
    # (sky -> blue -> indigo, with cyan for variety), not a rainbow.
    # Mapped by lowercased title; a slug class is emitted too so CSS can
    # apply dark-mode brightness adjustments per section.
    section_accents = {
        "introduction": "#38bdf8",   # sky-400 — light/bright, welcoming
        "education":     "#3b82f6",  # blue-500 — core academic blue
        "publications":  "#6366f1",  # indigo-500 — deeper, scholarly
        "awards":        "#2563eb",  # blue-600 — distinction (royal blue)
        "teaching":      "#0ea5e9",  # sky-500 — cyan-blue, growth
        "projects":      "#6366f1",  # indigo
        "research":      "#38bdf8",  # sky
        "experience":    "#0ea5e9",  # sky
        "skills":        "#3b82f6",  # blue
        "contact":       "#60a5fa",  # blue-400
    }
    default_accent = "#3b82f6"
    sections = []
    for index, (title, body_html) in enumerate(raw_sections):
        key = title.lower().strip()
        # Use special timeline renderer for Education section
        if key == "education":
            raw_edu_md = get_raw_section_body("content.md", "Education")
            timeline_html = parse_education_timeline(raw_edu_md)
            if timeline_html:
                body_html = timeline_html
        slug = re.sub(r'[^a-z0-9]+', '-', key).strip('-') or f"section-{index}"
        sections.append({
            "title": title,
            "body_html": body_html,
            "accent_color": section_accents.get(key, default_accent),
            "accent_class": f"section-{slug}",
        })

    if not sections:
        raw_html = render_markdown_file("content.md")
        sections.append({
            "title": "",
            "body_html": raw_html,
            "accent_color": default_accent,
            "accent_class": "section-default",
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


def _build_daily_payload(keywords: Optional[str] = None, item_type: Optional[str] = None, date: Optional[str] = None) -> dict[str, Any]:
    return load_daily_payload(keywords=keywords, item_type=item_type, date=date)


def _build_gallery_payload(focus: Optional[str] = None) -> dict[str, Any]:
    upload_dir = Path(UPLOAD_DIR).resolve()
    gallery_dirs = get_gallery_folders()
    is_focused = False
    if focus and focus in gallery_dirs:
        gallery_dirs = [focus]
        is_focused = True

    albums = []
    for rel_path in gallery_dirs:
        path = safe_join(upload_dir, rel_path)
        if not path.exists() or not path.is_dir():
            continue

        images = []
        full_images = []
        try:
            for file in sorted(list(path.iterdir()), key=lambda item: item.name):
                if file.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                    rel_file_path = file.relative_to(upload_dir)
                    original_url = f"/uploads/{rel_file_path}"
                    full_images.append(original_url)

                    if is_focused:
                        images.append(original_url)
                        continue

                    thumbnail_path = ensure_gallery_thumbnail(upload_dir, file)
                    if thumbnail_path:
                        thumb_rel_path = thumbnail_path.relative_to(upload_dir)
                        images.append(f"/uploads/{thumb_rel_path}")
                    else:
                        images.append(original_url)
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
            "full_images": full_images,
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
    return _build_markdown_article_payload(
        ARTICLES_DIR / f"{slug}.md",
        slug,
        back_url="/articles",
        back_label="Back to Articles",
    )


def _build_markdown_article_payload(path: Path, slug: str, back_url: str, back_label: str) -> dict[str, Any]:
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
        "back_url": back_url,
        "back_label": back_label,
    }


def _build_daily_article_detail_payload(slug: str) -> dict[str, Any]:
    item, run_date = _daily_item_for_article_slug(slug)
    if not item:
        raise HTTPException(status_code=404, detail="Daily article not found")
    path = ensure_daily_article_markdown(item, run_date, output_dir=DAILY_ARTICLES_DIR)
    return _build_markdown_article_payload(
        path,
        slug,
        back_url=f"/daily?date={run_date}" if run_date else "/daily",
        back_label="Back to Daily",
    )


def _daily_item_for_article_slug(slug: str) -> tuple[dict[str, Any] | None, str]:
    date_match = re.match(r"^(\d{4}-\d{2}-\d{2})-", slug)
    payloads = []
    if date_match:
        payloads.append(_build_daily_payload(date=date_match.group(1)))
    payloads.append(_build_daily_payload())
    seen_dates = set()
    for payload in payloads:
        run_date = str(payload.get("run_date") or payload.get("selected_date") or "")
        if run_date in seen_dates:
            continue
        seen_dates.add(run_date)
        for item in payload.get("items", []):
            if item.get("article_slug") == slug:
                return item, run_date
    return None, ""



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
    data.extend(daily_payload_search_entries(load_daily_payload()))
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


@router.get("/api/site/daily")
def daily_api(request: Request, keyword: Optional[str] = None, keywords: Optional[str] = None, item_type: Optional[str] = None, date: Optional[str] = None) -> Any:
    effective_keywords = keywords if keywords else keyword
    payload = _build_daily_payload(effective_keywords, item_type, date)
    if not get_current_user(request):
        payload = {**payload, "feedback_config": {}}
    return JSONResponse(payload, headers={"Cache-Control": "private, max-age=60"})



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


@router.get("/daily", response_class=HTMLResponse)
def daily_page(request: Request, keywords: Optional[str] = None, item_type: Optional[str] = None, paper_id: Optional[str] = None, date: Optional[str] = None):
    payload = _build_daily_payload(keywords, item_type, date)
    is_upload_authenticated = get_current_user(request)
    return templates.TemplateResponse(request, "pages/daily.html", {
        "items": payload["items"],
        "run_date": payload["run_date"],
        "selected_date": payload["selected_date"],
        "archive_dates": payload["archive_dates"],
        "filter_keywords": payload["filter_keywords"],
        "active_item_type": payload["active_item_type"],
        "sorted_keywords": payload["sorted_keywords"],
        "feedback_config": payload["feedback_config"] if is_upload_authenticated else {},
        "is_upload_authenticated": is_upload_authenticated,
        "keywords_url": _keywords_url,
        "type_url": _daily_type_url,
        "target_paper_id": paper_id or "",
    })


@router.get("/daily/articles/{slug}", response_class=HTMLResponse)
def daily_article_detail_page(request: Request, slug: str):
    try:
        article = _build_daily_article_detail_payload(slug)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Daily article not found")
    return templates.TemplateResponse(request, "pages/article_detail.html", {
        "article": article,
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
