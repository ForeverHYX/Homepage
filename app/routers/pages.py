from typing import Optional, Any
import datetime
from datetime import datetime
import secrets
from pathlib import Path
import markdown

from fastapi import APIRouter, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import (
    TEMPLATE_BASE, STYLES, UPLOAD_DIR, ARTICLES_DIR,
    ICON_MAIL, ICON_GITHUB, ICON_MAP, ICON_CALENDAR, ICON_USER_S, 
    ICON_ARROW_LEFT, ICON_MAXIMIZE, ICON_ARROW_LEFT
)
from app.utils import (
    parse_markdown_sections, render_markdown_file, get_gallery_folders, 
    safe_join, get_folder_meta, PdfExtension
)
from app.content_utils import get_about_info, parse_and_merge_news, get_all_articles
from app.auth import get_current_user, VALID_SESSIONS, SESSION_KEY, UPLOAD_USERNAME, UPLOAD_PASSWORD

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def index() -> str:
    # Get structured info
    about = get_about_info()
    avatar_url = "/uploads/avatar.png"

    # Parse main content into sections
    raw_sections = parse_markdown_sections("content.md")
    
    # Section Colors (Light Blue to Primary Blue)
    section_colors = ['#bfdbfe', '#93c5fd', '#60a5fa', '#3b82f6']

    # Generate HTML for each section
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

    # If no sections, just render normally to avoid blank page
    if not sections_html:
        raw_html = render_markdown_file("content.md")
        sections_html = f"""<div class="prose">{raw_html}</div>"""

    # Render News (Merged & Sorted)
    news_html = parse_and_merge_news()

    page_content = f"""
    <div class="container main-grid">
      <aside class="sidebar">
        <div class="card profile-card">
          <img src="{avatar_url}" class="avatar" alt="Avatar" onerror="this.src='https://ui-avatars.com/api/?name=YH&background=3b82f6&color=fff&size=128'" />
          <h1 class="profile-name">{about['name']}</h1>
          <p class="profile-role">{about['role']}</p>
          
          <div class="contact-links">
            <a href="{about['email']}" class="contact-icon" title="Email">{ICON_MAIL}</a>
            <a href="{about['github']}" class="contact-icon" target="_blank" title="GitHub">{ICON_GITHUB}</a>
          </div>
          
          <div class="location">
            {ICON_MAP} <span>{about['location']}</span>
          </div>
        </div>

        <div class="card news-card">
            <h3 class="news-title">News</h3>
            {news_html}
        </div>
      </aside>
      
      <main class="card content-area">
        {sections_html}
      </main>
    </div>
    """
    return TEMPLATE_BASE.format(title="Home | Yixun Hong", styles=STYLES, content=page_content, script="")


@router.get("/articles", response_class=HTMLResponse)
def articles_index() -> str:
    articles = get_all_articles()
    
    list_items = ""
    for art in articles:
        # Create a card for each article
        list_items += f"""
        <div class="card" style="padding:24px; margin-bottom:0px; transition: transform 0.2s;">
            <h2 style="margin:0 0 12px 0; font-size:1.5rem;">
                <a href="/articles/{art["slug"]}" style="text-decoration:none; color:var(--heading);">{art["title"]}</a>
            </h2>
            <div style="font-size:13px; color:var(--muted); margin-bottom:12px; display:flex; gap:16px;">
                 <span>{ICON_CALENDAR} {art["date"]}</span>
                 <span>{ICON_USER_S} {art["author"]}</span>
            </div>
            <p style="color:var(--text); font-size:15px; margin:0; line-height:1.6;">
                {art["summary"]}
            </p>
            <div style="margin-top:16px;">
                <a href="/articles/{art["slug"]}" style="font-weight:600; font-size:14px; color:var(--primary); text-decoration:none;">Read more &rarr;</a>
            </div>
        </div>
        """
    
    content_html = f"""
    <div class="container">
        <div class="content-area" style="max-width:100%; margin:0 auto; padding:40px 0; background:transparent;">
            <h1 class="section-title" style="border-left-color: var(--primary); margin-bottom:24px; font-size: 3rem; padding-bottom:10px;">Articles</h1>
            <div style="max-width:800px; display:flex; flex-direction:column; gap:24px;">
                {list_items if articles else "<p>No articles yet.</p>"}
            </div>
        </div>
    </div>
    """
    return TEMPLATE_BASE.format(title="Articles | Yixun Hong", styles=STYLES, content=content_html, script="")


@router.get("/gallery", response_class=HTMLResponse)
def gallery_index(focus: Optional[str] = None) -> str:
    gallery_dirs = get_gallery_folders()
    
    is_focused = False
    if focus and focus in gallery_dirs:
        gallery_dirs = [focus]
        is_focused = True

    # Gather data first
    albums_data = []

    for rel_path in gallery_dirs:
         path = safe_join(UPLOAD_DIR, rel_path)
         if not path.exists() or not path.is_dir():
             continue
             
         # Get Images
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
             
         # Get metadata
         meta = get_folder_meta(path)
         title = meta.get("title", path.name)
         desc = meta.get("description", "")
         date_str = meta.get("date", "")
         
         # Determine Sort Timestamp
         sort_ts = 0.0
         if date_str:
             try:
                 sort_ts = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
             except: pass
         
         if sort_ts == 0.0:
            # Fallback to latest mtime in folder
            try:
                sort_ts = max(p.stat().st_mtime for p in path.iterdir())
                date_str = datetime.fromtimestamp(sort_ts).strftime("%Y-%m-%d")
            except: pass
            
         albums_data.append({
             "path_name": path.name,
             "rel_path": rel_path,
             "title": title,
             "desc": desc,
             "date_str": date_str,
             "images": images,
             "sort_ts": sort_ts
         })
    
    # Sort by date descending
    albums_data.sort(key=lambda x: x["sort_ts"], reverse=True)

    albums_html_inner = ""
    
    # Header Button (Back)
    if is_focused:
        albums_html_inner += f"""
        <div style="margin-bottom: 24px;">
            <a href="/gallery" class="btn" style="background:var(--surface); border:1px solid var(--border); color:var(--text); text-decoration:none; padding:8px 16px; border-radius:4px; display:inline-flex; align-items:center;">
                {ICON_ARROW_LEFT} <span style="margin-left:8px;">Back to All Galleries</span>
            </a>
        </div>
        """
    
    for album in albums_data:
         # Zoom Button Logic
         zoom_btn = ""
         if not is_focused:
             zoom_btn = f"""
             <a href="/gallery?focus={album['rel_path']}" title="Expand View" style="color:var(--muted); transition:color .2s; display:inline-flex; border:1px solid var(--border); padding:4px; border-radius:4px; margin-left:12px;">
                {ICON_MAXIMIZE}
             </a>
             """
         
         # Build Carousel HTML
         slides = ""
         for img_url in album["images"]:
             slides += f"""
             <div class="carousel-slide" onclick="openLightbox('{img_url}')">
                 <img src="{img_url}" loading="lazy" alt="Photo">
             </div>
             """
         
         wrapper_class = "carousel-wrapper focused" if is_focused else "carousel-wrapper"
         
         albums_html_inner += f"""
         <section class="gallery-album mb-12">
             <div style="margin-bottom:16px; display:flex; align-items:center;">
                <div style="flex:1;">
                    <div style="display:flex; align-items:center;">
                        <h2 style="font-size:1.5rem; font-weight:700; margin:0; text-transform:capitalize; border-left: 5px solid var(--primary); padding-left: 12px; line-height: 1.2;">{album['title']}</h2>
                        {zoom_btn}
                    </div>
                    {f'<p style="margin:4px 0 0 0; padding-left:17px; color:var(--muted); font-size:0.9rem; font-weight:500;">{album["date_str"]}</p>' if album["date_str"] else ''}
                    {f'<p style="margin:4px 0 0 0; padding-left:17px; color:var(--text); font-size:1rem;">{album["desc"]}</p>' if album["desc"] else ''}
                </div>
             </div>
             <div class="{wrapper_class}">
                 <div class="carousel-container" id="carousel-{album['path_name']}">
                     {slides}
                 </div>
             </div>
         </section>
         """
    
    # Unified Container Structure matching /articles
    final_content = f"""
    <div class="container">
        <div class="content-area" style="max-width:800px; margin:0 auto; padding:40px 0; background:transparent;">
            <h1 class="section-title" style="border-left-color: var(--primary); margin-bottom:24px; font-size: 3rem; padding-bottom:10px;">Gallery</h1>
            <div style="display:flex; flex-direction:column; gap:24px;">
                {albums_html_inner if albums_data else "<p>No albums found.</p>"}
            </div>
        </div>
    </div>
    """

    extra_styles = """
    .gallery-album { margin-bottom: 60px; }
    
    /* Lightbox Styles */
    .lightbox-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.95);
        z-index: 10000;
        display: none;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    .lightbox-overlay.active {
        display: flex;
        opacity: 1;
    }
    .lightbox-content {
        max-width: 95vw;
        max-height: 95vh;
        border-radius: 4px;
        box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
        transform: scale(0.95);
        transition: transform 0.3s ease;
    }
    .lightbox-overlay.active .lightbox-content {
        transform: scale(1);
    }
    .lightbox-close {
        position: absolute;
        top: 20px;
        right: 30px;
        color: white;
        font-size: 50px;
        cursor: pointer;
        z-index: 10001;
        line-height: 0.8;
        background: transparent;
        border: none;
        padding: 0;
        font-family: serif; 
        opacity: 0.8;
        transition: opacity 0.2s;
    }
    .lightbox-close:hover {
        opacity: 1;
    }

    /* Carousel / Filmstrip Styles */
    .carousel-wrapper {
        background: var(--surface);
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
        border-radius: 16px;
        padding: 20px 0;
        overflow: hidden;
        transition: all 0.3s ease;
    }
    
    /* Focused Mode Modifications */
    .carousel-wrapper.focused {
        /* Keep the shadow box look */
        background: var(--surface);
        border: 1px solid var(--border);
        box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1); /* Stronger shadow */
        border-radius: 20px;
        padding: 32px;
        
        /* Expand width slightly beyond normal container if possible, or just be full width */
        width: 100%;
    }

    .carousel-container { 
        overflow-x: auto; 
        display: flex;
        gap: 16px;
        padding: 0 24px 12px 24px;
        align-items: center; 
        scrollbar-width: thin;
        scrollbar-color: var(--muted) transparent;
    }
    
    .carousel-wrapper.focused .carousel-container {
        /* Convert to grid/wrap layout */
        flex-wrap: wrap;
        justify-content: center; /* Center images */
        gap: 16px; /* Space between images */
        padding: 0;
        height: auto; /* Let it grow vertically */
        overflow-x: visible; /* No scrollbar needed horizontally usually */
        align-items: flex-start;
    }
    
    /* Scrollbar Logic for Focused */
    .carousel-wrapper.focused .carousel-container::-webkit-scrollbar { display: none; }

    .carousel-container::-webkit-scrollbar { height: 6px; }
    .carousel-container::-webkit-scrollbar-track { background: transparent; }
    .carousel-container::-webkit-scrollbar-thumb { background-color: var(--muted); border-radius: 3px; }
    .carousel-container::-webkit-scrollbar-thumb:hover { background-color: var(--text); }
    
    .carousel-slide {
        flex: 0 0 auto;
        height: 500px;
        border-radius: 8px;
        overflow: hidden;
        transition: all 0.3s;
        cursor: pointer;
    }
    
    .carousel-wrapper.focused .carousel-slide {
        /* Fixed height for rows */
        height: 280px; 
        border-radius: 8px; /* Keep rounded corners */
        box-shadow: var(--shadow); /* Individual shadow */
        opacity: 1;
        transition: transform 0.2s;
    }

    .carousel-wrapper.focused .carousel-slide:hover {
        transform: scale(1.02); /* Subtle zoom on hover */
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    
    .carousel-slide img {
        height: 100%;
        width: auto; 
        object-fit: contain; 
        display: block;
    }
    
    @media(max-width: 800px) {
        .carousel-slide { height: 300px; }
        .carousel-wrapper.focused .carousel-slide { height: 200px; } /* Smaller on mobile */
    }
    """
    
    script = """
    // Lightbox Logic
    window.openLightbox = (url) => {
        const overlay = document.getElementById('lightboxOverlay');
        const img = document.getElementById('lightboxImg');
        img.src = url;
        overlay.style.display = 'flex';
        void overlay.offsetWidth;
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    };
    
    window.closeLightbox = () => {
        const overlay = document.getElementById('lightboxOverlay');
        overlay.classList.remove('active');
        setTimeout(() => {
            overlay.style.display = 'none';
            document.getElementById('lightboxImg').src = '';
            document.body.style.overflow = '';
        }, 300);
    };

    // Auto Scroll Logic (Only for non-focused)
    document.addEventListener('DOMContentLoaded', () => {
        // If focused, we might disable auto-scroll to let user inspect
        const carousels = document.querySelectorAll('.carousel-container');
        const isFocused = document.querySelector('.carousel-wrapper.focused');
        
        if (isFocused) return; // Disable auto scroll in focused mode

        carousels.forEach(container => {
            let interval;
            const startAutoPlay = () => {
                interval = setInterval(() => {
                    const currentScroll = container.scrollLeft;
                    const maxScroll = container.scrollWidth - container.clientWidth;
                    if (currentScroll >= maxScroll - 5) {
                        container.scrollTo({ left: 0, behavior: 'smooth' });
                    } else {
                        container.scrollBy({ left: 400, behavior: 'smooth' });
                    }
                }, 2000);
            };
            const stopAutoPlay = () => clearInterval(interval);
            startAutoPlay();
            container.addEventListener('mouseenter', stopAutoPlay);
            container.addEventListener('mouseleave', startAutoPlay);
            container.addEventListener('touchstart', stopAutoPlay, {passive: true});
            container.addEventListener('touchend', startAutoPlay);
        });
    });
    """

    # Add Lightbox Structure to final content
    final_content += """
    <!-- Lightbox Structure -->
    <div id="lightboxOverlay" class="lightbox-overlay" onclick="closeLightbox()">
        <button class="lightbox-close" onclick="closeLightbox()">&times;</button>
        <img id="lightboxImg" class="lightbox-content" src="" alt="Full Size" onclick="event.stopPropagation()">
    </div>
    """
    
    return TEMPLATE_BASE.format(title="Gallery | Yixun Hong", styles=STYLES + extra_styles, content=final_content, script=script)


@router.get("/articles/{slug}", response_class=HTMLResponse)
def article_detail(slug: str) -> Any:
    path = ARTICLES_DIR / f"{slug}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Article not found")
    
    text = path.read_text(encoding="utf-8")
    
    # Parse Metadata manually to separate it from body
    lines = text.splitlines()
    body_lines = []
    
    title = ""
    author = "Yixun Hong"
    date_str = ""
    
    # Simple state parsers
    for line in lines:
        sline = line.strip()
        if not title and sline.startswith("# "):
            title = sline[2:].strip()
            continue
        if sline.lower().startswith("**date**:") or sline.lower().startswith("date:"):
            date_str = sline.split(":", 1)[1].strip()
            continue
        if sline.lower().startswith("**author**:") or sline.lower().startswith("author:"):
            author = sline.split(":", 1)[1].strip()
            continue
        
        body_lines.append(line)
    
    clean_body = "\n".join(body_lines)
    
    # Rendering with TOC
    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", PdfExtension()])
    html_body = md.convert(clean_body)
    toc_html = md.toc
    
    if not title: title = slug.replace("-", " ").title()

    content = f"""
    <div class="container article-grid" style="margin-top:40px; margin-bottom:60px;">
      <!-- Main Content Card -->
      <main class="card content-area" style="padding:40px; min-width:0;">
        <div style="margin-bottom:20px;">
            <a href="/articles" class="action-btn" style="text-decoration:none; padding-left:0;">&larr; Back to Articles</a>
        </div>
        
        <header style="margin-bottom:8px; border-bottom:1px solid var(--border); padding-bottom:8px;">
            <h1 style="font-size:2.5rem; font-weight:600; color:var(--heading); margin:0 0 8px 0; padding-left:16px; border-left:6px solid var(--primary); line-height:1.2;">{title}</h1>
            <div style="display:flex; gap:24px; color:var(--muted); font-size:15px; padding-left:22px;">
                 <span style="display:flex; align-items:center;">{ICON_CALENDAR} {date_str}</span>
                 <span style="display:flex; align-items:center;">{ICON_USER_S} {author}</span>
            </div>
        </header>

        <article class="prose">
          {html_body}
        </article>
      </main>

      <!-- Right Sidebar (TOC) -->
      <aside>
          <div class="toc" style="position:sticky; top:100px;">
              <p style="font-weight:700; color:var(--heading); margin-top:0; margin-bottom:12px; font-size:14px; text-transform:uppercase; letter-spacing:0.05em;">Contents</p>
              {toc_html}
          </div>
      </aside>

    </div>
    """
    return TEMPLATE_BASE.format(title=f"{title} | Yixun Hong", styles=STYLES, content=content, script="")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> Any:
    if get_current_user(request):
        return RedirectResponse("/upload")
    
    content = f"""
    <div class="container" style="display:flex; justify-content:center; padding-top:80px;">
      <div style="background:var(--surface); padding:40px; border-radius:16px; width:100%; max-width:400px; border:1px solid var(--border); box-shadow:var(--shadow);">
        <h1 style="margin:0 0 8px; font-size:24px;">Welcome Back</h1>
        <p style="color:var(--muted); margin:0 0 32px;">Sign in to manage your files</p>
        <form action="/login" method="post">
          <div style="margin-bottom:20px;">
            <label style="display:block; margin-bottom:8px; font-weight:500;">Username</label>
            <input name="username" required autofocus style="width:100%; padding:10px; border:1px solid var(--border); border-radius:8px; font-size:16px; background:var(--bg); color:var(--text);" />
          </div>
          <div style="margin-bottom:32px;">
            <label style="display:block; margin-bottom:8px; font-weight:500;">Password</label>
            <input type="password" name="password" required style="width:100%; padding:10px; border:1px solid var(--border); border-radius:8px; font-size:16px; background:var(--bg); color:var(--text);" />
          </div>
          <button type="submit" class="btn btn-primary">Sign In</button>
        </form>
      </div>
    </div>
    """
    return TEMPLATE_BASE.format(title="Login | Yixun Hong", styles=STYLES, content=content, script="")


@router.post("/login")
def login(username: str = Form(...), password: str = Form(...)) -> Any:
    # Strip whitespace just in case
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
