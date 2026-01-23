# Foreverhyx Homepage (Lightweight)

## Features
- Markdown-driven homepage (edit `content/index.md` to update)
- Simple upload backend with local disk storage

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit:
- Home: http://localhost:8000/
- Upload API: `POST /api/upload`
- File list: `GET /api/files`
- File access: `/uploads/{filename}`

## Environment Variables
- `HOMEPAGE_CONTENT_DIR`: Markdown directory (default `./content`)
- `HOMEPAGE_UPLOAD_DIR`: Upload directory (default `./uploads`)

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
This is the minimal runnable version. Next steps could include auth, admin UI, image optimization, and CDN.
