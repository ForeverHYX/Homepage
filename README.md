# Homepage

This repository powers a personal academic homepage. It runs as a **single
process** built entirely on **FastAPI + Jinja2 templates + vanilla JS** — no
React, no Next.js, no build step, no database. Markdown files in `content/`
are the sole data source.

> **Note on `frontend/`**: the original Next.js app still lives in the
> `frontend/` directory for reference, but it is **no longer part of the
> deployment**. Everything described below is the current, live system.

### Why Next.js was removed

The production server is a 2-core / 1.7 GB Debian 12 box. Under the previous
hybrid setup, Next.js consumed ~150 MB of RAM even though nearly every
component was marked `"use client"`, making it effectively a thin proxy in
front of FastAPI. Removing it:

- freed ~130 MB of RAM,
- cut TTFB from ~80–120 ms down to **17–27 ms**,
- eliminated the frontend build step, and
- collapsed the deployment into a single gunicorn-managed process.

## Architecture

A single FastAPI application (run under gunicorn with 2 uvicorn workers in
production) serves both HTML pages and JSON APIs out of one process:

- **FastAPI 0.115.8** serves HTML pages (via Jinja2 templates) **and** JSON APIs
- **Uvicorn workers** managed by **gunicorn** (2 workers in production)
- **Vanilla JS** for all client-side interactivity — no React, no Next.js,
  no build step
- **Markdown files in `content/`** as the sole data source — zero database
- **Deployed on Debian 12** (2-core / 1.7 GB RAM), managed by **systemd**
  with **Nginx** as the reverse proxy

The backend lives in `app/` and is organized as:

| Module | Responsibility |
| --- | --- |
| `app/main.py` | App entry + Jinja2Templates setup |
| `app/config.py` | Paths, rate limiter, env vars |
| `app/auth.py` | bcrypt + session tokens |
| `app/cache.py` | mtime-based in-memory cache |
| `app/articles.py` | Article parsing |
| `app/news.py` | News aggregation |
| `app/content_utils.py` | Section extraction, about parsing |
| `app/markdown_utils.py` | Markdown renderer (with PDF embed extension) |
| `app/education.py` | Education timeline parser |
| `app/file_utils.py` | Image conversion, safe path join |
| `app/gallery_utils.py` | Gallery config management |
| `app/utils.py` | Unified re-exports |
| `app/routers/pages.py` | HTML page routes + JSON API + payload builders |
| `app/routers/upload.py` | File upload APIs |
| `app/routers/auth.py` | Login API |

## Route split

| Route group | Handler | Purpose |
| --- | --- | --- |
| `/`, `/articles`, `/articles/{slug}`, `/gallery`, `/resume` | FastAPI + Jinja2 | Public HTML pages |
| `/login`, `/upload` | FastAPI + Jinja2 | Admin pages (auth-gated) |
| `/api/site/*`, `/api/search-index` | FastAPI JSON | Data for client-side JS fetches |
| `/api/upload`, `/api/files*`, `/api/folder*`, `/api/gallery/toggle`, `/api/login` | FastAPI JSON | Admin operations (auth-gated) |
| `/static/*` | Nginx direct | CSS + JS assets (7-day immutable cache) |
| `/uploads/*` | Nginx direct | Uploaded files (7-day cache) |

## Current feature set

- Public academic homepage with a floating capsule-style navigation bar
- Custom SVG `feDisplacementMap` liquid-glass effect (880-line vanilla JS
  engine, no libraries)
- Custom lightfield animation engine (6 gradient light spots, mouse parallax,
  theme-adaptive)
- Mobile fallback to standard frosted glass for better performance
- Markdown-driven homepage sections
- Markdown-driven article system with:
  - tags
  - summaries
  - automatic TOC generation
  - fenced code blocks
  - inline PDF embedding (via a custom Python-Markdown `PdfExtension`)
- Folder-based gallery publishing with metadata
- Search across articles and albums
- Dark/light theme via `data-theme` attribute + CSS custom properties
- Secure upload dashboard for:
  - drag-and-drop uploads
  - folder creation
  - file deletion
  - gallery publish/unpublish toggles
  - album metadata editing
  - automatic JPG→WebP conversion (quality 80, max 1920px) on upload

## Repository layout

```text
.
├── app/                          # FastAPI application
│   ├── main.py                   # App entry + Jinja2Templates setup
│   ├── config.py                 # Paths, rate limiter, env vars
│   ├── auth.py                   # bcrypt + session tokens
│   ├── cache.py                  # mtime-based in-memory cache
│   ├── articles.py               # Article parsing
│   ├── news.py                   # News aggregation
│   ├── content_utils.py          # Section extraction, about parsing
│   ├── markdown_utils.py         # Markdown renderer (with PDF embed extension)
│   ├── education.py              # Education timeline parser
│   ├── file_utils.py             # Image conversion, safe path join
│   ├── gallery_utils.py          # Gallery config management
│   ├── utils.py                  # Unified re-exports
│   ├── routers/
│   │   ├── pages.py              # HTML page routes + JSON API + payload builders
│   │   ├── upload.py             # File upload APIs
│   │   └── auth.py               # Login API
│   └── templates/
│       ├── base.html             # Layout: nav island, lightfield, footer, scripts
│       └── pages/
│           ├── home.html
│           ├── articles.html
│           ├── article_detail.html
│           ├── gallery.html
│           ├── resume.html
│           ├── login.html
│           ├── upload.html
│           └── 404.html
├── static/
│   ├── css/styles.css            # Single stylesheet (~3400 lines)
│   └── js/
│       ├── effects/
│       │   ├── liquid-glass.js   # SVG feDisplacementMap glass effect
│       │   └── lightfield.js     # Animated gradient light field
│       └── components/
│           ├── site-header.js    # Nav island, search, theme toggle
│           ├── content-enhancer.js  # Code highlighting + GitHub cards
│           ├── gallery-view.js   # Carousel + lightbox
│           ├── upload-manager.js # Drag-drop upload dashboard
│           ├── anniversary-calendar.js
│           └── anniversary-data.js
├── content/                      # Markdown content (the "database")
│   ├── about.md                  # Profile info
│   ├── content.md                # Homepage sections
│   ├── news.md                   # Manual news entries
│   └── articles/*.md             # One file per article
├── uploads/                      # Gallery albums, avatar, documents
│   ├── <album>/                  # Images + meta.json per album
│   ├── avatar.png
│   └── transcript.pdf
├── deploy/                       # Saved deployment configs
│   └── nginx-foreverhyx.conf
├── frontend/                     # LEGACY Next.js code — kept for reference, NOT deployed
├── requirements.txt
└── README.md
```

## Content model

The site is file-driven. There is **no database** — Markdown files in
`content/` are the sole data source, and the in-memory cache invalidates
automatically whenever a file's mtime changes.

### Homepage content

- `content/about.md`
  - basic profile info such as email, GitHub link, location, name, role
- `content/content.md`
  - main homepage sections
- `content/news.md`
  - manual news entries

### Articles

- `content/articles/*.md`
  - each markdown file becomes an article
  - the parser extracts title, date, author, tags, abstract/summary

### Gallery

- `uploads/<album>/`
  - image files for one album
- `uploads/<album>/meta.json`
  - optional album title, description, date, author
- `gallery_config.json`
  - controls which upload folders are publicly exposed as gallery albums

### Misc assets

- `uploads/avatar.png`
  - homepage avatar
- `uploads/transcript.pdf`
  - resume / transcript link if you want one in the nav

## Environment variables

Create a `.env` file in the repository root:

```env
HOMEPAGE_UPLOAD_USER=admin
HOMEPAGE_UPLOAD_PASS=change-me
HOMEPAGE_UPLOAD_PASS_HASH=<bcrypt hash>  # alternative to plain pass
HOMEPAGE_CONTENT_DIR=/path/to/content    # optional override
HOMEPAGE_UPLOAD_DIR=/path/to/uploads     # optional override
HOMEPAGE_COOKIE_SECURE=true              # production HTTPS
```

## Local development

There is **no frontend build step** — static JS is served directly. Edit
static files and refresh.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

> Tip: append `?v=N` to a static asset URL during development to bust
> browser cache after editing.

## Production deploy

There is **no build step** — gunicorn runs the FastAPI app directly.

```bash
# Backend only — no build step
gunicorn app.main:app -k uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 --workers 2 --timeout 60
```

Nginx proxies `/*` and `/api/*` to FastAPI on `127.0.0.1:8000` and serves
`/static/` and `/uploads/` directly (7-day cache). A reference Nginx config
lives at `deploy/nginx-foreverhyx.conf`.

The systemd service file lives at
`/etc/systemd/system/foreverhyx-homepage.service` and manages the gunicorn
process.

## Notes for contributors

- **No build step.** Edit static files and refresh the browser — there is no
  bundler, no transpiler, no `npm run build`.
- **Cache-bust with `?v=N`.** Because assets are served directly, append a
  `?v=N` query param when iterating on CSS/JS during development.
- **`static/css/styles.css` is the single source of truth for styling** —
  one ~3400-line stylesheet powers the entire site.
- Sessions are stored in `.sessions.json` and are safe across the multiple
  uvicorn workers; this is plain `token_urlsafe(32)` plus bcrypt, intentionally
  simple — replace it with a real session store if you need more.
- Rate limiting is provided by `slowapi` (200/min global, stricter on
  `/login` and `/upload`).
- All filesystem access uses `safe_join()` to prevent path traversal.
- Windows-compatible SVG filter regions are required for the liquid-glass
  effect — a black-shadow bug there was recently fixed.

## License / attribution

This project is the source for Yixun Hong's homepage and remains highly
tailored to that deployment. You are free to study and adapt the structure,
but expect to customize content parsing, deployment, and styling for your
own use case.
