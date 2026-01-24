# Personal Academic Homepage (FastAPI Edition)

A modern, highly customizable personal homepage and portfolio system built with **FastAPI**. Designed for academics, photographers, and developers who want a lightweight, single-file deployable solution with powerful content management capabilities.

## ✨ Key Features

### 🎨 Modern UI & Theming
- **Dark/Light Mode**: Fully supported with system preference detection and persistent manual toggle.
- **Responsive Design**: Mobile-friendly layout using CSS Grid and Flexbox.
- **CSS Variables**: Easy theming system (modifying `STYLES` in `app/main.py`).

### 📝 Content Management
- **Markdown-Driven**: all content is stored in simple Markdown files.
- **Static Content Blocks**:
    - `content/content.md`: Main homepage sections (Introduction, Education, etc.).
    - `content/news.md`: Sidebar news updates.
    - `content/about.md`: Sidebar profile information.
- **Article System**:
    - Dedicated blog/article section (`/articles`).
    - Smart metadata parsing (Title, Date, Author) from Markdown headers.
    - Automatic Table of Contents (TOC) generation.
    - Syntax highlighting for code blocks.

### 🖼️ Advanced Gallery System
- **Folder-Based Organization**: Simply upload a folder of images to create an album.
- **Dual View Modes**:
    - **Focused View**: Grid layout with shadow boxes for browsing.
    - **Classic View**: Auto-scrolling horizontal filmstrip/carousel.
- **Lightbox**: Full-screen image viewer with high-res support.
- **Metadata Support**: Edit Album Title, Description, and "Shoot Date" via the web UI.
- **Smart Sorting**: Albums sorted by Shoot Date (customizable) or upload time.

### ☁️ File & Upload Manager
- **Secure Web Dashboard**: Manage files at `/upload`.
- **Drag & Drop Upload**: Support for batch uploading images and files.
- **File System Operations**: Create folders, delete files, and navigate directories.
- **Gallery Management**: One-click toggle to publish/unpublish specific folders to the public Gallery.
- **Metadata Editor**: GUI for editing folder titles and dates (saved to `meta.json`).
- **Auth**: Simple username/password protection for admin areas.

---

## 🚀 Quick Start

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running Locally

```bash
uvicorn app.main:app --reload
```
Visit http://127.0.0.1:8000

---

## 📂 Content Guide

### 1. Articles (`content/articles/*.md`)
Create a new markdown file in `content/articles/`. Use the following format for metadata recognition:

```markdown
# My Awesome Paper
**Date**: 2023-10-24
**Author**: Yixun Hong

This is the summary text that appears on the card.

## Introduction
Content starts here...
```

### 2. Main Page (`content/content.md`)
Use H1 headers (`#`) to separate sections (Bio, Research, Education etc). The system will automatically render them as styled cards.

```markdown
# Biography
I am a researcher...

# Education
* **PhD**, University of Science
...
```

### 3. Gallery Structure
Galleries are standard folders in `uploads/`.
- **To Create**: Go to `/upload`, create a folder, upload JPEGs.
- **To Publish**: Click the "Star" icon next to the folder in the Upload Manager.
- **To Edit Info**: Click the "Pencil" icon to set a custom Title, Description, or specific Shoot Date.

---

## 🛠️ Deployment

This project acts as a standard ASGI application.

**Using Nginx + Uvicorn (Recommended):**

1. Run Uvicorn as a daemon or via supervisor.
2. Nginx configuration for proxy_pass:
   ```nginx
   location / {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```
   *Note: Ensure `client_max_body_size` is increased in Nginx for large file uploads.*

## 🔒 Security
- Default credentials are set via environment variables or `secrets.compare_digest` in `app/main.py`.
- **Change the default password** in `app/main.py` (variables `UPLOAD_USERNAME` / `UPLOAD_PASSWORD`) before deploying.
