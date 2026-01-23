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

### Parsing Rules
The homepage uses a structured parsing approach for better styling:

- **Sections (content.md)**:
  - Header 1 (`# Title`) starts a new section (e.g., `# Introduction`, `# Education`).
  - These sections are rendered as distinct, styled cards on the right column.
  - Standard Markdown inside sections is supported (lists, links, bold, etc.).

- **Sidebar (about.md)**:
  - `(mailto:xxx)` -> Email Icon
  - `(https://github.com/xxx)` -> GitHub Icon
  - `## Location` -> The text immediately following this header is used as location.

### Tips for formatting
- Do NOT use `#` for inner headers. Use `##` or `###`. Top-level `#` is reserved for section splitting.
- Images can be used normally: `![Alt](/uploads/img.png)`.


## Development
Run locally:
```bash
uvicorn app.main:app --reload
```

## Deployment
Service is managed by systemd: `foreverhyx-homepage`.
Configuration in `/etc/systemd/system/foreverhyx-homepage.service`.
