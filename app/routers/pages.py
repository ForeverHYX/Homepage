from typing import Optional, Any
import datetime
from datetime import datetime
import secrets
from pathlib import Path
import re
import markdown

from fastapi import APIRouter, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.config import (
    UPLOAD_DIR, ARTICLES_DIR,
    ICON_MAIL, ICON_GITHUB, ICON_MAP, ICON_CALENDAR, ICON_USER_S, 
    ICON_ARROW_LEFT, ICON_MAXIMIZE
)
from app.utils import (
    parse_markdown_sections, render_markdown_file, get_gallery_folders, 
    safe_join, get_folder_meta, PdfExtension
)
from app.content_utils import get_about_info, parse_and_merge_news, get_all_articles
from app.auth import get_current_user, VALID_SESSIONS, SESSION_KEY, UPLOAD_USERNAME, UPLOAD_PASSWORD

router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates


def _render(request, name, context=None):
    t = _templates(request)
    ctx = {"request": request}
    if context:
        ctx.update(context)
    return t.TemplateResponse(request=request, name=name, context=ctx)


def _build_home_payload() -> dict[str, Any]:
    about = get_about_info()
    avatar_url = "/uploads/avatar.png"
    raw_sections = parse_markdown_sections("content.md")

    section_colors = ["#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6"]
    sections = []
    for index, (title, body_html) in enumerate(raw_sections):
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


def _build_articles_payload(tag: Optional[str] = None) -> dict[str, Any]:
    articles = get_all_articles()
    all_tags: dict[str, int] = {}
    for article in articles:
        for article_tag in article.get("tags", []):
            if article_tag:
                all_tags[article_tag] = all_tags.get(article_tag, 0) + 1

    filtered_articles = articles
    if tag:
        filtered_articles = [article for article in articles if tag in article.get("tags", [])]

    sorted_tags = sorted(all_tags.items(), key=lambda item: item[1], reverse=True)

    return {
        "articles": filtered_articles,
        "filter_tag": tag,
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
        tags_html += f'<span style="background:var(--surface-highlight); color:var(--text); font-size:11px; padding:2px 6px; border-radius:4px; margin-right:6px; border: 1px solid var(--border);">{tag}</span>'

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


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> Any:
    payload = _build_home_payload()
    return _render(request, "index.html", {
        **payload,
        "icon_mail": ICON_MAIL,
        "icon_github": ICON_GITHUB,
        "icon_map": ICON_MAP,
        "icon_maximize": ICON_MAXIMIZE,
    })


@router.get("/api/site/home")
def home_api() -> Any:
    return JSONResponse(_build_home_payload())


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


@router.get("/articles", response_class=HTMLResponse)
def articles_index(request: Request, tag: Optional[str] = None) -> Any:
    payload = _build_articles_payload(tag)
    return _render(request, "articles.html", {
        **payload,
        "icon_calendar": ICON_CALENDAR, "icon_user": ICON_USER_S,
    })


@router.get("/api/site/articles")
def articles_api(tag: Optional[str] = None) -> Any:
    return JSONResponse(_build_articles_payload(tag))


@router.get("/gallery", response_class=HTMLResponse)
def gallery_index(request: Request, focus: Optional[str] = None) -> Any:
    payload = _build_gallery_payload(focus)
    return _render(request, "gallery.html", payload)


@router.get("/api/site/gallery")
def gallery_api(focus: Optional[str] = None) -> Any:
    return JSONResponse(_build_gallery_payload(focus))


@router.get("/articles/{slug}", response_class=HTMLResponse)
def article_detail(request: Request, slug: str) -> Any:
    payload = _build_article_detail_payload(slug)
    return _render(request, "article_detail.html", {
        **payload,
        "icon_calendar": ICON_CALENDAR,
        "icon_user": ICON_USER_S,
    })


@router.get("/api/site/articles/{slug}")
def article_detail_api(slug: str) -> Any:
    return JSONResponse(_build_article_detail_payload(slug))


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> Any:
    if get_current_user(request):
        return RedirectResponse("/upload")
    return _render(request, "login.html", {})


@router.post("/login")
def login(username: str = Form(...), password: str = Form(...)) -> Any:
    username = username.strip()
    password = password.strip()
    if (
        secrets.compare_digest(username, UPLOAD_USERNAME) and 
        secrets.compare_digest(password, UPLOAD_PASSWORD)
    ):
        token = secrets.token_urlsafe(32)
        VALID_SESSIONS.add(token)
        response = RedirectResponse(url="/upload", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key=SESSION_KEY, value=token, httponly=True, max_age=86400)
        return response
    return HTMLResponse(
        content="<script>alert('Invalid credentials'); history.back();</script>", 
        status_code=status.HTTP_401_UNAUTHORIZED
    )
