import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

CONTENT_DIR = Path(os.getenv("HOMEPAGE_CONTENT_DIR", BASE_DIR / "content")).resolve()
ARTICLES_DIR = CONTENT_DIR / "articles"
UPLOAD_DIR = Path(os.getenv("HOMEPAGE_UPLOAD_DIR", BASE_DIR / "uploads")).resolve()
GALLERY_CONFIG_FILE = BASE_DIR.parent / "gallery_config.json"

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Security
UPLOAD_USERNAME = os.getenv("HOMEPAGE_UPLOAD_USER", "admin")
UPLOAD_PASSWORD = os.getenv("HOMEPAGE_UPLOAD_PASS", "changeme")
SESSION_KEY = "session_token"

# Icons
ICON_UPLOAD_CLOUD = """<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>"""
ICON_FILE = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>"""
ICON_OPEN = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>"""
ICON_TRASH = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>"""
ICON_COPY = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>"""
ICON_MAIL = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>"""
ICON_GITHUB = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>"""
ICON_MAP = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>"""
ICON_CALENDAR = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; position:relative; top:2px;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>"""
ICON_USER_S = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; position:relative; top:2px;"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>"""
ICON_FOLDER = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>"""
ICON_STAR = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>"""
ICON_STAR_FILLED = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="#eab308" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>"""
ICON_MAXIMIZE = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>"""
ICON_ARROW_LEFT = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>"""
ICON_MOON = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>"""
ICON_SUN = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>"""

STYLES = """
    :root { 
        --bg: #f8fafc; --text: #334155; --heading: #0f172a; --primary: #3b82f6; --primary-hover: #2563eb; 
        --surface: #ffffff; --surface-highlight: #f1f5f9; --border: #e2e8f0; --muted: #64748b; 
        --radius: 12px; --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
        --header-bg: #ffffff;
    }
    
    [data-theme="dark"] {
        --bg: #000000; --text: #cbd5e1; --heading: #f1f5f9; --primary: #60a5fa; --primary-hover: #93c5fd; 
        --surface: #111111; --surface-highlight: #1e293b; --border: #334155; --muted: #94a3b8;
        --radius: 12px; --shadow: 0 1px 3px 0 rgb(255 255 255 / 0.05), 0 1px 2px -1px rgb(255 255 255 / 0.05); /* Subtle light shadow/border */
        --header-bg: #111111;
        
        color-scheme: dark;
    }

    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; line-height: 1.6; transition: background 0.3s, color 0.3s; }
    
    /* Layout */
    .container { max-width: 1080px; margin: 0 auto; padding: 0 24px; }
    header { background: var(--header-bg); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 10; margin-bottom: 40px; box-shadow: var(--shadow); transition: background 0.3s, border-color 0.3s; }
    .nav { display: flex; align-items: center; justify-content: space-between; height: 64px; }
    .brand { font-weight: 700; font-size: 18px; text-decoration: none; color: var(--heading); display: flex; align-items: center; gap: 8px; }
    
    .main-grid { display: grid; gap: 48px; grid-template-columns: 1fr; align-items: start; }
    @media (min-width: 800px) { .main-grid { grid-template-columns: 260px 1fr; } }
    
    /* Sidebar */
    .sidebar { display: flex; flex-direction: column; gap: 24px; position: sticky; top: 100px; }
    
    /* Common Card Style */
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; transition: background 0.3s, border-color 0.3s; }

    .profile-card { padding: 32px 24px; text-align: center; }
    .avatar { width: 140px; height: 140px; border-radius: 50%; object-fit: cover; margin-bottom: 20px; box-shadow: var(--shadow); }
    
    .news-card { padding: 24px; }
    .news-title { font-size: 18px; font-weight: 700; color: var(--heading); margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px; }
    .news-list { list-style: none; padding: 0; margin: 0; }
    .news-item { font-size: 14px; color: var(--muted); margin-bottom: 12px; }
    .news-item a { color: inherit; text-decoration: none; border-bottom: 1px dashed var(--muted); transition: all 0.2s; }
    .news-item a:hover { color: var(--primary); border-bottom-color: var(--primary); }
    
    .profile-name { margin: 0; font-size: 22px; font-weight: 700; color: var(--heading); letter-spacing: -0.01em; }
    .profile-role { color: var(--muted); margin: 6px 0 0; font-size: 15px; font-weight: 400; }
    
    .contact-links { display: flex; justify-content: center; gap: 12px; margin: 24px 0; }
    .contact-icon { color: var(--muted); transition: all .2s; padding: 8px; border-radius: 50%; background: var(--surface-highlight); display: inline-flex; width: 36px; height: 36px; align-items: center; justify-content: center; }
    .contact-icon:hover { color: var(--primary); background: #e0f2fe; }
    [data-theme="dark"] .contact-icon:hover { background: #1e3a8a; } /* Dark mode hover bg */
    
    .location { display: flex; align-items: flex-start; justify-content: center; gap: 8px; color: var(--muted); font-size: 14px; margin-top: 20px; text-align: left; line-height: 1.4; padding: 0 10px; }
    .location svg { flex-shrink: 0; margin-top: 2px; }

    /* Content Area */
    .content-area { display: flex; flex-direction: column; gap: 40px; padding: 40px; }
    
    .cv-section { animation: fadeIn 0.5s ease-out; }
    
    .section-title { font-size: 1.5rem; font-weight: 700; color: var(--heading); margin: 0 0 1.5rem 0; padding-left: 1rem; border-left: 5px solid var(--primary); letter-spacing: -0.02em; }
    
    /* Typography inside sections */
    .prose { font-size: 15px; color: var(--text); }
    .prose p { margin-bottom: 1rem; }
    .prose ul { padding-left: 1.25rem; margin-bottom: 1rem; list-style-type: disc; }
    .prose ol { padding-left: 1.25rem; margin-bottom: 1rem; list-style-type: decimal; }
    
    /* Layout for Article Detail */
    .article-container { display: grid; grid-template-columns: 1fr; gap: 40px; position: relative; }
    @media (min-width: 1000px) { .article-container { grid-template-columns: minmax(0, 1fr) 280px; } }
    
    .toc { position: sticky; top: 100px; max-height: calc(100vh - 120px); overflow-y: auto; padding: 20px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); }
    .toc ul { list-style: none; padding: 0; margin: 0; }
    .toc li { margin-bottom: 8px; font-size: 14px; }
    .toc a { color: var(--muted); text-decoration: none; transition: all .2s; display: block; }
    .toc a:hover { color: var(--primary); }
    
    /* News Card Markdown Styles override */
    .news-card ul { list-style: none; padding: 0; margin: 0; }
    .news-card li { font-size: 14px; color: var(--muted); margin-bottom: 12px; }
    .news-card li:last-child { margin-bottom: 0; padding-bottom: 0; }
    .news-card p { margin: 0; } /* Reset p inside li if markdown adds it */
    .news-card strong { color: var(--heading); font-weight: 600; } /* Ensure date/strong is dark like name/title */

    .prose li { margin-bottom: 0.5rem; }
    .prose strong { color: var(--heading); font-weight: 600; }
    .prose em { color: var(--muted); font-style: italic; }
    
    /* Article Grid Layout */
    .article-grid { display: grid; grid-template-columns: 1fr; gap: 32px; align-items: stretch; }
    @media (min-width: 1024px) { .article-grid { grid-template-columns: 1fr 240px; } }

    /* Refined Typography for Article Body */
    .prose h1, .prose h2, .prose h3, .prose h4 { color: var(--heading); line-height: 1.3; font-weight: 700; }
    /* H1 in body (if any) or large section headers */
    .prose h1 { font-size: 1.8rem; margin-top: 2rem; margin-bottom: 1rem; letter-spacing: -0.02em; } 
    /* Standard section headers */
    .prose h2 { font-size: 1.5rem; margin-top: 2rem; margin-bottom: 1rem; letter-spacing: -0.01em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
    .prose h3 { font-size: 1.25rem; margin-top: 1.5rem; margin-bottom: 0.75rem; font-weight: 600; }
    .prose h4 { font-size: 1.1rem; margin-top: 1.25rem; margin-bottom: 0.5rem; font-weight: 600; }
    
    .prose p { margin-bottom: 1.25rem; line-height: 1.75; font-size: 1.05rem; }
    .prose > *:first-child { margin-top: 0; }
    .prose a { color: var(--primary); text-decoration: none; font-weight: 500; transition: color .2s; }
    .prose a:hover { color: var(--primary-hover); text-decoration: underline; }

    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

    /* Upload UI (Keep mostly same but clean up) */
    .upload-grid { display: grid; gap: 32px; grid-template-columns: 1fr; margin-top: 32px; }
    @media (min-width: 860px) { .upload-grid { grid-template-columns: 320px 1fr; } }
    
    .drop-zone { border: 2px dashed var(--border); border-radius: var(--radius); padding: 40px 24px; text-align: center; transition: all .2s; cursor: pointer; background: var(--surface); position: relative; overflow: hidden; }
    .drop-zone:hover, .drop-zone.drag { border-color: var(--primary); background: var(--surface-highlight); }
    .drop-zone input { position: absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor: pointer; }
    
    .file-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; }
    .file-preview { width: 36px; height: 36px; border-radius: 6px; object-fit: cover; background: var(--surface-highlight); display: flex; align-items: center; justify-content: center; color: var(--primary); flex-shrink: 0; }
    
    .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 20px; border-radius: 8px; font-weight: 500; cursor: pointer; transition: all .2s; font-size: 14px; text-decoration: none; border: none; }
    .btn-primary { background: var(--primary); color: white; width: 100%; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
    
    .action-btn { background: transparent; border: none; padding: 6px; border-radius: 6px; cursor: pointer; color: var(--muted); transition: all .2s; display: inline-flex; }
    .action-btn:hover { background: var(--surface-highlight); color: var(--text); }
    .action-btn.danger:hover { background: #fee2e2; color: #ef4444; }
    
    .toast { position: fixed; bottom: 32px; right: 32px; background: #0f172a; color: white; padding: 12px 24px; border-radius: 8px; font-weight: 500; opacity: 0; transform: translateY(20px); transition: all .3s; pointer-events: none; z-index: 100; font-size: 14px; }
    .toast.show { opacity: 1; transform: translateY(0); }
"""

TEMPLATE_BASE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/png" href="/uploads/favicon.png">
  <title>{title}</title>
  <meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0f172a" media="(prefers-color-scheme: dark)">
  <style>{styles}</style>
  <script>
    (function() {{
        const saved = localStorage.getItem('theme');
        const sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (saved === 'dark' || (!saved && sysDark)) {{
            document.documentElement.setAttribute('data-theme', 'dark');
        }}
    }})();
  </script>
</head>
<body>
  <header>
    <div class="container nav">
      <a href="/" class="brand">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        <span>Yixun Hong's Homepage</span>
      </a>
      <div style="display:flex; gap:20px; font-weight:500; align-items:center;">
        <a href="/" style="text-decoration:none; color:var(--text);">Home</a>
        <a href="/articles" style="text-decoration:none; color:var(--text);">Articles</a>
        <a href="/gallery" style="text-decoration:none; color:var(--text);">Gallery</a>
        <a href="/uploads/transcript.pdf" target="_blank" style="text-decoration:none; color:var(--text);">Resume</a>
        <a href="/upload" style="text-decoration:none; color:var(--text);">Upload</a>
        <button id="themeToggle" class="action-btn" title="Toggle Theme" style="margin-left:8px;" onclick="toggleTheme()">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
        </button>
      </div>
    </div>
  </header>
  {content}
  <script>
    const ICON_MOON = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
    const ICON_SUN = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;

    function toggleTheme() {{
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(next);
    }}
    
    function updateThemeIcon(theme) {{
        const btn = document.getElementById('themeToggle');
        if (theme === 'dark') btn.innerHTML = ICON_SUN;
        else btn.innerHTML = ICON_MOON;
    }}
    
    // Init correct icon on load
    updateThemeIcon(document.documentElement.getAttribute('data-theme'));
  
    {script}
  </script>
</body>
</html>"""
