# Foreverhyx Homepage (Lightweight)

## Features
- Markdown-driven homepage (edit `content/index.md` to update)
- Upload center at `/upload` with login protection
- Local disk storage for uploaded files

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit:
- Home: http://localhost:8000/
- Upload UI (requires login): http://localhost:8000/upload
- Upload API: `POST /api/upload`
- File list: `GET /api/files`
- File access: `/uploads/{filename}`

## Environment Variables
- `HOMEPAGE_CONTENT_DIR`: Markdown directory (default `./content`)
- `HOMEPAGE_UPLOAD_DIR`: Upload directory (default `./uploads`)
- `HOMEPAGE_UPLOAD_USER`: Upload UI username (default `admin`)
- `HOMEPAGE_UPLOAD_PASS`: Upload UI password (default `changeme`)

## Structure
```
app/
  main.py
content/
  index.md
uploads/
requirements.txt
```

## Notes
The upload UI uses HTTP Basic Auth for simplicity. Use a strong password and consider adding IP allow-lists or a VPN if exposed publicly.
