# Homepage

This repository powers a personal academic homepage with a hybrid architecture:

- `Next.js` serves the public-facing pages
- `FastAPI` serves content APIs, uploads, auth, static assets, and the admin dashboard

The current production site is built around this split rather than the older pure-FastAPI template system. If you are reading the repository for the first time, treat this README as the source of truth for how the project works today.

## Architecture

### Public app

The public site lives in `frontend/` and is built with:

- Next.js 16
- React 19
- TypeScript
- App Router

Current public routes:

- `/`
- `/articles`
- `/articles/[slug]`
- `/gallery`

These routes fetch their data from FastAPI JSON endpoints and render through Next.js.

### Backend app

The backend lives in `app/` and is built with:

- FastAPI
- Uvicorn
- Jinja2
- Markdown-based content parsing
- Pillow for image processing

The backend is still responsible for:

- `/api/site/*` content APIs
- `/api/search-index`
- `/upload` admin dashboard
- `/login` admin login
- file upload / delete / folder management APIs
- `/static/*`
- `/uploads/*`

Important detail: the shared site stylesheet is still served by FastAPI from `static/css/styles.css`, even when the public page itself is rendered by Next.js.

## Route split

| Route group | Runtime | Purpose |
| --- | --- | --- |
| `/`, `/articles`, `/articles/[slug]`, `/gallery` | Next.js | Public pages |
| `/api/site/*`, `/api/search-index` | FastAPI | Data for the public app |
| `/upload`, `/login`, `/api/upload`, `/api/files*`, `/api/folder*`, `/api/gallery/toggle` | FastAPI | Admin and file management |
| `/static/*`, `/uploads/*` | FastAPI | Shared assets and uploaded files |

## Current feature set

- Public academic homepage with a floating capsule-style navigation bar
- Desktop liquid-glass homepage treatment with a lower-cost custom runtime
- Mobile fallback to standard frosted glass for better performance
- Markdown-driven homepage sections
- Markdown-driven article system with:
  - tags
  - summaries
  - automatic TOC generation
  - fenced code blocks
  - PDF embedding inside markdown
- Folder-based gallery publishing with metadata
- Search across articles and albums
- Dark/light theme support
- Secure upload dashboard for:
  - drag-and-drop uploads
  - folder creation
  - file deletion
  - gallery publish/unpublish toggles
  - album metadata editing

## Repository layout

```text
.
├── app/                     # FastAPI app, APIs, auth, upload manager
│   ├── main.py
│   ├── auth.py
│   ├── config.py
│   ├── content_utils.py
│   ├── utils.py
│   └── routers/
├── frontend/                # Next.js public frontend
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── next.config.ts
├── static/                  # Shared CSS/JS served by FastAPI
├── templates/               # Jinja templates, mainly admin / compatibility paths
├── content/                 # Markdown content source
└── uploads/                 # User uploads, gallery albums, avatar, documents
```

## Content model

The site is file-driven.

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

Create a `.env` file in the repository root for the backend:

```env
HOMEPAGE_UPLOAD_USER=admin
HOMEPAGE_UPLOAD_PASS=change-me

# Optional overrides
HOMEPAGE_CONTENT_DIR=/absolute/path/to/content
HOMEPAGE_UPLOAD_DIR=/absolute/path/to/uploads
```

Frontend builds and local dev can also use:

```env
API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
BACKEND_ORIGIN=http://127.0.0.1:8000
```

`frontend/next.config.ts` rewrites `/api/*`, `/static/*`, `/uploads/*`, `/upload*`, and `/login*` back to the backend origin.

## Local development

### 1. Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
API_BASE_URL=http://127.0.0.1:8000 \
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 \
BACKEND_ORIGIN=http://127.0.0.1:8000 \
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Then open:

- `http://127.0.0.1:3000` for the public site
- `http://127.0.0.1:8000/upload` for the admin dashboard

## Production build and deploy

The current production deployment uses Next.js standalone output plus a separate FastAPI process.

### Build the frontend

```bash
cd frontend
npm install
npm run build
mkdir -p .next/standalone/.next/static
cp -R .next/static/. .next/standalone/.next/static/
```

That static copy step is required. Without it, the standalone server will miss chunk assets.

### Run the frontend

```bash
node .next/standalone/server.js
```

### Run the backend

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Reverse proxy expectation

Production should send:

- public page routes to Next.js
- `/api/*`, `/static/*`, `/uploads/*`, `/upload*`, `/login*` to FastAPI

## Notes for contributors

- `static/css/styles.css` is still part of the live frontend experience
- the homepage liquid-glass effect is implemented in `frontend/components/home-legacy-effects.tsx`
- article syntax highlighting is route-scoped and no longer loaded globally
- the homepage data layer uses FastAPI JSON endpoints plus Next.js revalidation
- admin auth is intentionally simple and currently uses an in-memory session set; if you need persistent or multi-instance auth, replace it with a proper session store

## License / attribution

This project is the source for Yixun Hong's homepage and remains highly tailored to that deployment. You are free to study and adapt the structure, but expect to customize content parsing, deployment, and styling for your own use case.
