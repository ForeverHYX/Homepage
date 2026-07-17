import os
from pathlib import Path
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

CONTENT_DIR = Path(os.getenv("HOMEPAGE_CONTENT_DIR", BASE_DIR / "content")).resolve()
UPLOAD_DIR = Path(os.getenv("HOMEPAGE_UPLOAD_DIR", BASE_DIR / "uploads")).resolve()
GALLERY_CONFIG_FILE = BASE_DIR / "gallery_config.json"

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiter shared instance
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Security

UPLOAD_USERNAME = os.getenv("HOMEPAGE_UPLOAD_USER", "admin")
UPLOAD_PASSWORD_HASH = os.getenv("HOMEPAGE_UPLOAD_PASS_HASH", "").strip()
COOKIE_SECURE = os.getenv("HOMEPAGE_COOKIE_SECURE", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SESSION_FILE = Path(os.getenv("HOMEPAGE_SESSION_FILE", BASE_DIR / ".sessions.json")).resolve()
SESSION_TIMEOUT_SECONDS = int(os.getenv("HOMEPAGE_SESSION_TIMEOUT_SECONDS", "86400"))
SHARE_LINK_FILE = Path(
    os.getenv("HOMEPAGE_SHARE_LINK_FILE", BASE_DIR / ".share-links.json")
).resolve()
USE_X_ACCEL_REDIRECT = os.getenv("HOMEPAGE_USE_X_ACCEL_REDIRECT", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ENABLE_API_DOCS = os.getenv("HOMEPAGE_ENABLE_API_DOCS", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# These files are part of the public site rather than private file-manager
# storage. Public Gallery folders are added dynamically from gallery_config.json.
PUBLIC_UPLOAD_FILES = frozenset(
    {
        "ASC25.webp",
        "avatar.png",
        "favicon.png",
        "resume.pdf",
        "zju.png",
    }
)
PUBLIC_UPLOAD_PREFIXES = ("paper/",)
