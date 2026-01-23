# Homepage Project

A personal academic homepage built with **FastAPI**.

## Features

- **Markdown Content**: Edit `content/content.md` to update main sections (Introduction, Education, etc.).
- **News**: Update `content/news.md` for manual news items.
- **Articles**: Add markdown files to `content/articles/` to publish blog posts.
- **File Upload**: Secure text/image hosting at `/upload`.

## Article Format Specification

To ensure articles display correctly on the `/articles` index page with metadata, please use the following header format at the very top of your markdown files:

```markdown
# Your Article Title
**Date**: YYYY-MM-DD
**Author**: Your Name

Your summary or introduction content goes here. This text will be used for the preview card on the articles listing page. The system captures the first 200 characters.

## Next Heading
...
```

- **Title**: The first H1 header (`# ...`) is used as the title.
- **Date**: Must be in format `**Date**: YYYY-MM-DD` or `Date: YYYY-MM-DD`.
- **Author**: Must be in format `**Author**: Name` or `Author: Name`.
- **Summary**: The text immediately following the metadata (before the next header) is used as the preview summary.

## Content Parsing Rules

### Main Content (content.md)
- Header 1 (`# Title`) starts a new section (e.g., `# Introduction`, `# Education`).
- These sections are rendered as distinct blocks in the main column.
- Standard Markdown inside sections is supported (lists, links, bold, etc.).

### Sidebar (about.md)
- `(mailto:xxx)` -> Auto-detected as Email
- `(https://github.com/xxx)` -> Auto-detected as GitHub Link
- `## Location` -> The text immediately following this header is used as location.

## Development
Run locally:
```bash
uvicorn app.main:app --reload
```

## Deployment
Service is managed by systemd: `foreverhyx-homepage`.
Configuration in `/etc/systemd/system/foreverhyx-homepage.service`.
