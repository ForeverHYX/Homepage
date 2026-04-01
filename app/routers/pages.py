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


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> Any:
    about = get_about_info()
    avatar_url = "/uploads/avatar.png"
    raw_sections = parse_markdown_sections("content.md")
    
    section_colors = ['#bfdbfe', '#93c5fd', '#60a5fa', '#3b82f6']
    sections_html = ""
    for i, (title, body) in enumerate(raw_sections):
        color = section_colors[i % len(section_colors)]
        sections_html += f"""
        <section class="cv-section">
            <h2 class="section-title" style="border-left-color: {color}">{title}</h2>
            <div class="prose">
                {body}
            </div>
        </section>
        """
    
    if not sections_html:
        raw_html = render_markdown_file("content.md")
        sections_html = f'<div class="prose">{raw_html}</div>'

    news_html = parse_and_merge_news(limit=6)
    all_news_html = parse_and_merge_news(limit=100)

    return _render(request, "index.html", {
        "about": about,
        "avatar_url": avatar_url,
        "sections_html": sections_html,
        "news_html": news_html,
        "all_news_html": all_news_html,
        "icon_mail": ICON_MAIL,
        "icon_github": ICON_GITHUB,
        "icon_map": ICON_MAP,
        "icon_maximize": ICON_MAXIMIZE,
    })


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
    articles = get_all_articles()
    all_tags = {}
    for a in articles:
        for t in a.get('tags', []):
            if t: all_tags[t] = all_tags.get(t, 0) + 1
    if tag:
        articles = [a for a in articles if tag in a.get('tags', [])]
    sorted_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)
    return _render(request, "articles.html", {
        "articles": articles, "filter_tag": tag, "sorted_tags": sorted_tags,
        "icon_calendar": ICON_CALENDAR, "icon_user": ICON_USER_S,
    })


@router.get("/gallery", response_class=HTMLResponse)
def gallery_index(request: Request, focus: Optional[str] = None) -> Any:
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
            for f in sorted(list(path.iterdir()), key=lambda x: x.name):
                if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    rel_file_path = f.relative_to(UPLOAD_DIR)
                    images.append(f"/uploads/{rel_file_path}")
        except:
            continue
        if not images:
            continue
        meta = get_folder_meta(path)
        
        sort_ts = 0.0
        date_str = meta.get("date", "")
        if date_str:
            try: sort_ts = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
            except: pass
        if sort_ts == 0.0:
            try:
                sort_ts = max(p.stat().st_mtime for p in path.iterdir())
                date_str = datetime.fromtimestamp(sort_ts).strftime("%Y-%m-%d")
            except: pass
        
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
            "path_name": path.name, "rel_path": rel_path,
            "title": meta.get("title", path.name), "desc": meta.get("description", ""),
            "date_str": date_str, "author": meta.get("author", "Yixun Hong"),
            "images": images, "sort_ts": sort_ts,
            "title_style": title_style, "meta_style": meta_style,
            "desc_style": desc_style, "card_padding": card_padding,
            "card_margin": card_margin, "nav_margin": nav_margin,
            "wrapper_class": "carousel-wrapper focused" if is_focused else "carousel-wrapper",
        })
    
    albums.sort(key=lambda x: x["sort_ts"], reverse=True)
    return _render(request, "gallery.html", {
        "albums": albums, "is_focused": is_focused,
    })


@router.get("/articles/{slug}", response_class=HTMLResponse)
def article_detail(request: Request, slug: str) -> Any:
    path = ARTICLES_DIR / f"{slug}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Article not found")
    
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    body_lines = []
    title, author, date_str = "", "Yixun Hong", ""
    tags = []
    
    for line in lines:
        sline = line.strip()
        if not title and sline.startswith("# "):
            title = sline[2:].strip(); continue
        if sline.lower().startswith("**date**:") or sline.lower().startswith("date:"):
            date_str = sline.split(":", 1)[1].strip(); continue
        if sline.lower().startswith("**author**:") or sline.lower().startswith("author:"):
            author = sline.split(":", 1)[1].strip(); continue
        if sline.lower().startswith("**tags**:") or sline.lower().startswith("tags:") or sline.lower().startswith("tag:"):
            tag_str = sline.split(":", 1)[1].strip()
            tags = [t.strip() for t in tag_str.split(",") if t.strip()]; continue
        if sline.lower().startswith("**abstract**:") or sline.lower().startswith("abstract:"):
            continue
        body_lines.append(line)
    
    clean_body = "\n".join(body_lines)
    words = re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fa5]', clean_body)
    word_count = len(words)
    read_time = max(1, round(word_count / 200))

    ICON_CLOCK = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; position:relative; top:2px;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'

    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", PdfExtension()])
    html_body = md.convert(clean_body)
    toc_html = md.toc
    
    if not title: title = slug.replace("-", " ").title()

    tags_html = ""
    for t in tags:
        tags_html += f'<span style="background:var(--surface-highlight); color:var(--text); font-size:11px; padding:2px 6px; border-radius:4px; margin-right:6px; border: 1px solid var(--border);">{t}</span>'

    return _render(request, "article_detail.html", {
        "title": title, "html_body": html_body, "toc_html": toc_html,
        "icon_calendar": ICON_CALENDAR, "icon_user": ICON_USER_S, "icon_clock": ICON_CLOCK,
        "date_str": date_str, "author": author,
        "word_count": word_count, "read_time": read_time,
        "tags_html": tags_html, "tags": tags,
    })


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
