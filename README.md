# Homepage Project

This is a personal homepage built with **FastAPI**.

## Directory Structure
- `app/main.py`: Core application code (FastAPI).
- `content/`: Markdown files for page content.
  - `nav.md`: (Optional) Navigation content.
  - `about.md`: Sidebar profile info (Avatar, Contact links, Location).
  - `content.md`: Main body text (Right column).
- `uploads/`: Directory for file uploads.

## Content Format

### `about.md` parsing rules
The app looks for specific lines to generate the sidebar:
- `(mailto:xxx)` -> Email Icon
- `(https://github.com/xxx)` -> GitHub Icon
- `## Location` -> The text immediately following this header is used as location.

## Development
Run locally:
```bash
uvicorn app.main:app --reload
```

## Deployment
Service is managed by systemd: `foreverhyx-homepage`.
Configuration in `/etc/systemd/system/foreverhyx-homepage.service`.
