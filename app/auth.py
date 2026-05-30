import secrets
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Request, HTTPException, status
from passlib.context import CryptContext

# Ensure .env is loaded (independent of config.py import order)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security Config
UPLOAD_USERNAME = os.getenv("HOMEPAGE_UPLOAD_USER", "admin")
UPLOAD_PASSWORD_HASH = os.getenv(
    "HOMEPAGE_UPLOAD_PASS_HASH",
    "$2b$12$QtEnDt2pD4JsZuYxe95EFOlzrvaM2qwxtAPwsbEf2gyQlorr3NWyi"  # default: 'Hyx20041224'
)
SESSION_KEY = "session_token"
SESSION_TIMEOUT = 86400  # 24 hours

# Session storage file
SESSION_FILE = BASE_DIR / ".sessions.json"


def _load_sessions() -> dict:
    """Load sessions from disk and drop expired ones."""
    if not SESSION_FILE.exists():
        return {}
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        now = time.time()
        valid = {k: v for k, v in data.items() if isinstance(v, (int, float)) and v > now}
        return valid
    except Exception:
        return {}


def _save_sessions(sessions: dict) -> None:
    """Persist sessions to disk atomically."""
    try:
        tmp = SESSION_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(sessions), encoding="utf-8")
        tmp.replace(SESSION_FILE)
    except Exception:
        pass


# In-memory cache synced with disk
VALID_SESSIONS = _load_sessions()


def get_current_user(request: Request) -> bool:
    token = request.cookies.get(SESSION_KEY)
    if token and token in VALID_SESSIONS:
        if VALID_SESSIONS[token] > time.time():
            return True
        # Expired — clean up
        del VALID_SESSIONS[token]
        _save_sessions(VALID_SESSIONS)
    return False


def require_login(request: Request) -> None:
    if not get_current_user(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def verify_credentials(username: str, password: str) -> bool:
    """Constant-time username comparison + bcrypt password verification."""
    user_ok = secrets.compare_digest(username, UPLOAD_USERNAME)
    pass_ok = pwd_context.verify(password, UPLOAD_PASSWORD_HASH)
    return user_ok and pass_ok


def create_session() -> str:
    """Create a new session token, persist it, and return the token."""
    token = secrets.token_urlsafe(32)
    expiry = time.time() + SESSION_TIMEOUT
    VALID_SESSIONS[token] = expiry
    _save_sessions(VALID_SESSIONS)
    return token


def destroy_session(token: str) -> None:
    """Remove a session token from storage."""
    if token in VALID_SESSIONS:
        del VALID_SESSIONS[token]
        _save_sessions(VALID_SESSIONS)


def get_cookie_settings() -> dict:
    """Return recommended cookie flags for production."""
    # When running behind an HTTPS-terminating proxy, assume HTTPS.
    secure = os.getenv("HOMEPAGE_COOKIE_SECURE", "true").lower() in ("1", "true", "yes", "on")
    return {
        "key": SESSION_KEY,
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "max_age": SESSION_TIMEOUT,
    }
