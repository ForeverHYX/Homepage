import os
from pathlib import Path
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

CONTENT_DIR = Path(os.getenv("HOMEPAGE_CONTENT_DIR", BASE_DIR / "content")).resolve()
ARTICLES_DIR = CONTENT_DIR / "articles"
UPLOAD_DIR = Path(os.getenv("HOMEPAGE_UPLOAD_DIR", BASE_DIR / "uploads")).resolve()
GALLERY_CONFIG_FILE = BASE_DIR / "gallery_config.json"

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiter shared instance
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Security
SESSION_KEY = "session_token"

UPLOAD_USERNAME = os.getenv("HOMEPAGE_UPLOAD_USER", "admin")
UPLOAD_PASSWORD = os.getenv("HOMEPAGE_UPLOAD_PASS", "changeme")

