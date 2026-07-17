from typing import Optional, Any
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode
import re
import markdown

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Request,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.config import UPLOAD_DIR
from app.templating import templates
from app.gallery_utils import get_folder_meta, get_gallery_folders
from app.markdown_utils import PdfExtension
from app.news import parse_and_merge_news
from app.daily import (
    MAX_FILTER_KEYWORDS,
    load_daily_payload,
)
from app.daily_articles import DAILY_ARTICLES_DIR, ensure_daily_article_markdown
from app.auth import get_current_user
from app.gallery_thumbnail_utils import (
    ensure_gallery_thumbnail,
    get_current_gallery_thumbnail,
    get_gallery_thumbnail_cache_token,
    warm_gallery_thumbnails,
)
from app.services.content import build_home_payload, build_publications_payload
from app.services.gallery import build_gallery_payload
from app.services.search import build_search_index

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SITE_URL = "https://foreverhyx.top"
INDEXNOW_KEY = "f3124866af9054b4f96d7cf251a01281"
SITEMAP_PATHS = (
    "/",
    "/publications",
    "/daily",
    "/gallery",
    "/resume",
)


def _publication_keywords_url(current_keywords: list[str], toggle: Optional[str] = None) -> str:
    """Build a keyword toggle URL for the Publications filter."""
    if not toggle:
        next_keywords = current_keywords
    elif toggle in current_keywords:
        next_keywords = [keyword for keyword in current_keywords if keyword != toggle]
    else:
        next_keywords = [*current_keywords, toggle]
    if not next_keywords:
        return "/publications"
    return f"/publications?keywords={quote(','.join(next_keywords))}"


def _daily_url(
    keywords: Optional[list[str]] = None,
    item_type: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    params: dict[str, str] = {}
    if date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        params["date"] = date
    if keywords:
        canonical_keywords: dict[str, str] = {}
        for keyword in keywords:
            normalized_keyword = keyword.strip()
            if normalized_keyword:
                canonical_keywords.setdefault(normalized_keyword.casefold(), normalized_keyword)
        ordered_keywords = sorted(
            canonical_keywords.values(),
            key=lambda keyword: (keyword.casefold(), keyword),
        )[:MAX_FILTER_KEYWORDS]
        if ordered_keywords:
            params["keywords"] = ",".join(ordered_keywords)
    if item_type in {"paper", "repository"}:
        params["item_type"] = item_type
    if not params:
        return "/daily"
    return f"/daily?{urlencode(params)}"


def _keywords_url(
    current_keywords: list[str],
    toggle: Optional[str] = None,
    item_type: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """Build a Daily keyword toggle URL."""
    toggle_key = toggle.casefold() if toggle else ""
    if not toggle:
        next_keywords = current_keywords
    elif any(keyword.casefold() == toggle_key for keyword in current_keywords):
        next_keywords = [
            keyword for keyword in current_keywords if keyword.casefold() != toggle_key
        ]
    else:
        next_keywords = [*current_keywords, toggle]
    return _daily_url(next_keywords, item_type, date)


def _daily_type_url(item_type: Optional[str] = None, date: Optional[str] = None) -> str:
    """Build a Daily type filter URL. Switching type resets keyword filters."""
    return _daily_url([], item_type, date)


def _build_home_payload(*, include_legacy_fields: bool = True) -> dict[str, Any]:
    return build_home_payload(include_legacy_fields=include_legacy_fields)


def _build_publications_payload(keywords: Optional[str] = None) -> dict[str, Any]:
    return build_publications_payload(keywords)


def _build_daily_payload(
    keywords: Optional[str] = None,
    item_type: Optional[str] = None,
    date: Optional[str] = None,
) -> dict[str, Any]:
    return load_daily_payload(keywords=keywords, item_type=item_type, date=date)


def _build_gallery_payload(
    focus: Optional[str] = None,
    include_private: bool = False,
    pending_thumbnails: Optional[list[Path]] = None,
) -> dict[str, Any]:
    gallery_dirs = get_gallery_folders(include_private=include_private)
    result = build_gallery_payload(
        Path(UPLOAD_DIR),
        gallery_dirs,
        focus=focus,
        defer_thumbnails=pending_thumbnails is not None,
        ensure_thumbnail=ensure_gallery_thumbnail,
        current_thumbnail=get_current_gallery_thumbnail,
        thumbnail_token=get_gallery_thumbnail_cache_token,
        folder_meta=get_folder_meta,
    )
    if pending_thumbnails is not None:
        pending_thumbnails.extend(result.pending_thumbnails)
    return result.payload


def _gallery_cache_headers(
    include_private: bool,
    thumbnails_pending: bool = False,
) -> dict[str, str]:
    if include_private:
        cache_control = "private, no-store"
    elif thumbnails_pending:
        cache_control = "no-store"
    else:
        cache_control = "public, max-age=60"
    return {"Cache-Control": cache_control, "Vary": "Cookie"}


def _admin_redirect(url: str) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=303)
    response.headers.update(
        {
            "Cache-Control": "private, no-store",
            "X-Robots-Tag": "noindex, nofollow",
        }
    )
    return response


def _build_markdown_article_payload(
    path: Path, slug: str, back_url: str, back_label: str
) -> dict[str, Any]:
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
        if (
            stripped.lower().startswith("**tags**:")
            or stripped.lower().startswith("tags:")
            or stripped.lower().startswith("tag:")
        ):
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
    markdown_renderer = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc", PdfExtension()]
    )
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


@router.get("/api/site/news")
def news_api() -> Any:
    return JSONResponse(
        {"all_news_html": parse_and_merge_news(limit=100)},
        headers={"Cache-Control": "public, max-age=60"},
    )


@router.get("/api/search-index")
def search_api():
    return JSONResponse(
        build_search_index(),
        headers={
            "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
        },
    )


@router.get("/api/site/publications")
def publications_api(keyword: Optional[str] = None, keywords: Optional[str] = None) -> Any:
    effective_keywords = keywords if keywords else keyword
    return JSONResponse(
        _build_publications_payload(effective_keywords),
        headers={"Cache-Control": "public, max-age=60"},
    )


@router.get("/api/site/daily")
def daily_api(
    request: Request,
    keyword: Optional[str] = None,
    keywords: Optional[str] = None,
    item_type: Optional[str] = None,
    date: Optional[str] = None,
) -> Any:
    effective_keywords = keywords if keywords else keyword
    payload = _build_daily_payload(effective_keywords, item_type, date)
    if not get_current_user(request):
        payload = {**payload, "feedback_config": {}}
    return JSONResponse(payload, headers={"Cache-Control": "private, max-age=60"})


@router.get("/api/site/gallery")
def gallery_api(
    request: Request,
    background_tasks: BackgroundTasks,
    focus: Optional[str] = None,
) -> Any:
    include_private = bool(get_current_user(request))
    pending_thumbnails: list[Path] = []
    payload = _build_gallery_payload(
        focus,
        include_private=include_private,
        pending_thumbnails=pending_thumbnails,
    )
    if pending_thumbnails:
        background_tasks.add_task(
            warm_gallery_thumbnails,
            Path(UPLOAD_DIR).resolve(),
            tuple(pending_thumbnails),
        )
    return JSONResponse(
        payload,
        headers=_gallery_cache_headers(
            include_private,
            thumbnails_pending=bool(pending_thumbnails),
        ),
        background=background_tasks,
    )


@router.post("/api/revalidate-gallery")
def revalidate_gallery():
    """No-op: with direct FastAPI rendering there is no Next.js cache to bust."""
    return JSONResponse({"revalidated": True, "now": datetime.now().timestamp()})


# ============================================
# HTML Page Routes (Jinja2 templates)
# ============================================


@router.get("/robots.txt", include_in_schema=False)
def robots_txt():
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /api/",
            "Disallow: /login",
            "Disallow: /share/",
            "Disallow: /upload",
            "",
            f"Sitemap: {SITE_URL}/sitemap.xml",
            "",
        ]
    )
    return Response(
        content=body,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    urls = "\n".join(
        f"""  <url>
    <loc>{SITE_URL}{path}</loc>
    <changefreq>weekly</changefreq>
    <priority>{"1.0" if path == "/" else "0.7"}</priority>
  </url>"""
        for path in SITEMAP_PATHS
    )
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
"""
    return Response(
        content=body,
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get(f"/{INDEXNOW_KEY}.txt", include_in_schema=False)
def indexnow_key_file():
    return Response(
        content=f"{INDEXNOW_KEY}\n",
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    payload = _build_home_payload(include_legacy_fields=False)
    return templates.TemplateResponse(
        request,
        "pages/home.html",
        {
            "about": payload["about"],
            "avatar_url": payload["avatar_url"],
            "sections": payload["sections"],
            "news_html": payload["news_html"],
        },
    )


@router.get("/publications", response_class=HTMLResponse)
def publications_page(request: Request, keywords: Optional[str] = None):
    payload = _build_publications_payload(keywords)
    return templates.TemplateResponse(
        request,
        "pages/publications.html",
        {
            "publications": payload["publications"],
            "filter_keywords": payload["filter_keywords"],
            "sorted_keywords": payload["sorted_keywords"],
            "keywords_url": _publication_keywords_url,
        },
    )


@router.get("/daily", response_class=HTMLResponse)
def daily_page(
    request: Request,
    keywords: Optional[str] = None,
    item_type: Optional[str] = None,
    paper_id: Optional[str] = None,
    date: Optional[str] = None,
):
    payload = _build_daily_payload(keywords, item_type, date)
    is_upload_authenticated = get_current_user(request)
    requested_date = str(date or "")
    current_run_date = str(payload.get("current_run_date") or payload["run_date"])
    available_dates = {str(value) for value in payload.get("archive_dates", [])}
    date_is_indexable = bool(requested_date) and (
        requested_date == current_run_date or requested_date in available_dates
    )
    filter_date = payload["selected_date"] if date_is_indexable else None
    has_filter_query = "keywords" in request.query_params or "item_type" in request.query_params
    has_invalid_date_query = "date" in request.query_params and not date_is_indexable
    canonical_path = _daily_url(date=requested_date if date_is_indexable else None)
    return templates.TemplateResponse(
        request,
        "pages/daily.html",
        {
            "items": payload["items"],
            "run_date": payload["run_date"],
            "selected_date": payload["selected_date"],
            "current_run_date": payload.get("current_run_date") or payload["run_date"],
            "archive_dates": payload["archive_dates"],
            "archive_counts": payload["archive_counts"],
            "profile_radar": payload["profile_radar"],
            "filter_keywords": payload["filter_keywords"],
            "active_item_type": payload["active_item_type"],
            "sorted_keywords": payload["sorted_keywords"],
            "feedback_config": payload["feedback_config"] if is_upload_authenticated else {},
            "is_upload_authenticated": is_upload_authenticated,
            "keywords_url": lambda current_keywords, toggle=None, active_type=None: _keywords_url(
                current_keywords,
                toggle,
                active_type,
                filter_date,
            ),
            "type_url": lambda active_type=None: _daily_type_url(active_type, filter_date),
            "target_paper_id": paper_id or "",
            "daily_canonical_url": f"{SITE_URL}{canonical_path}",
            "daily_robots_noindex": has_filter_query or has_invalid_date_query,
        },
    )


@router.get("/daily/articles/{slug}", response_class=HTMLResponse)
def daily_article_detail_page(request: Request, slug: str):
    try:
        article = _build_daily_article_detail_payload(slug)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Daily article not found")
    return templates.TemplateResponse(
        request,
        "pages/article_detail.html",
        {
            "article": article,
        },
    )


@router.get("/gallery", response_class=HTMLResponse)
def gallery_page(
    request: Request,
    background_tasks: BackgroundTasks,
    focus: Optional[str] = None,
):
    include_private = bool(get_current_user(request))
    pending_thumbnails: list[Path] = []
    payload = _build_gallery_payload(
        focus,
        include_private=include_private,
        pending_thumbnails=pending_thumbnails,
    )
    if pending_thumbnails:
        background_tasks.add_task(
            warm_gallery_thumbnails,
            Path(UPLOAD_DIR).resolve(),
            tuple(pending_thumbnails),
        )
    response = templates.TemplateResponse(
        request,
        "pages/gallery.html",
        {
            "albums": payload["albums"],
            "is_focused": payload["is_focused"],
            "focus": payload["focus"],
        },
        background=background_tasks,
    )
    response.headers.update(
        _gallery_cache_headers(
            include_private,
            thumbnails_pending=bool(pending_thumbnails),
        )
    )
    return response


@router.get("/resume", response_class=HTMLResponse)
def resume_page(request: Request):
    return templates.TemplateResponse(request, "pages/resume.html", {})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user(request):
        return _admin_redirect("/upload")
    response = templates.TemplateResponse(request, "pages/login.html", {})
    response.headers.update(
        {
            "Cache-Control": "private, no-store",
            "X-Robots-Tag": "noindex, nofollow",
        }
    )
    return response


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    if not get_current_user(request):
        return _admin_redirect("/login?next=%2Fupload")
    response = templates.TemplateResponse(request, "pages/upload.html", {})
    response.headers.update(
        {
            "Cache-Control": "private, no-store",
            "X-Robots-Tag": "noindex, nofollow",
        }
    )
    return response
