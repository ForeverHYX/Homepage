# Personal Academic Homepage (FastAPI Edition)

A modern, highly customizable personal homepage and portfolio system built with **FastAPI**. Designed for academics, photographers, and developers who want a lightweight, modular deployable solution with powerful content management capabilities.

## ✨ Key Features

### 🎨 Modern UI & Theming
- **Dark/Light Mode**: Fully supported with system preference detection and persistent manual toggle.
- **Responsive Design**: Mobile-friendly layout using CSS Grid and Flexbox.
- **CSS Variables**: Easy theming system (modifying `STYLES` in `app/config.py`).

### 📝 Content Management
- **Markdown-Driven**: All content is stored in simple Markdown files.
- **Unified News Feed**: Automatically aggregates and sorts updates from:
    - Manual news entries (`content/news.md`).
    - New blog posts (`content/articles/*.md`).
    - New gallery albums (sorted by shoot date).
- **Article System**:
    - Dedicated blog/article section (`/articles`).
    - Smart metadata parsing (Title, Date, Author) from Markdown headers.
    - Automatic Table of Contents (TOC) generation.
    - PDF Support: Embed PDFs directly in markdown using standard image syntax.

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
2. Create `uploads` and `content` directories if they don't exist.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Create a `.env` file in the root directory:

```env
HOMEPAGE_UPLOAD_USER=admin
HOMEPAGE_UPLOAD_PASS=your_secure_password
```

### Running Locally

```bash
uvicorn app.main:app --reload
```
Visit http://127.0.0.1:8000

---

## 📂 Project Structure

```
├── app/
│   ├── main.py          # Entry point
│   ├── config.py        # Settings & Templates
│   ├── auth.py          # Authentication Logic
│   ├── utils.py         # Helper functions
│   ├── content_utils.py # Content parsing & aggregation
│   └── routers/         # API & Page Routes
├── content/             # Your Markdown Content
├── uploads/             # User uploaded files
└── .env                 # Secrets (Not tracked in git)
```

## 🛠️ Deployment

This project acts as a standard ASGI application.

**Using Nginx + Uvicorn (Recommended):**

1. Run Uvicorn as a daemon or via supervisor.
2. Nginx configuration for proxy_pass:
   ```nginx
   location / {
       proxy_pass http://127.0.0.1:8000\;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```
   *Note: Ensure `client_max_body_size` is increased in Nginx for large file uploads.*

## 🔒 Security
- Credentials are managed via `.env` file.
- **Ensure `.env` is listed in `.gitignore`** to prevent leaking secrets.

## 📄 Attribution / Framework
This website is built on [Yixun's Homepage Framework](https://github.com/ForeverHYX/Homepage).  
Copyright &copy; Yixun Hong.
