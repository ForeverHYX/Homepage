"""Upload authentication and a small, single-worker session store."""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import time
from threading import RLock
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status
from passlib.context import CryptContext

from app.config import (
    COOKIE_SECURE,
    SESSION_FILE,
    SESSION_TIMEOUT_SECONDS,
    UPLOAD_PASSWORD_HASH,
    UPLOAD_USERNAME,
)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_KEY = "session_token"
_SESSION_LOCK = RLock()
_AUTH_CACHE_MISSING = object()
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _load_sessions() -> dict[str, float]:
    """Load non-expired sessions; malformed state fails closed."""
    with _SESSION_LOCK:
        if not SESSION_FILE.exists():
            return {}
        try:
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        now = time.time()
        return {
            str(token): float(expiry)
            for token, expiry in data.items()
            if isinstance(expiry, (int, float)) and expiry > now
        }


def _save_sessions(sessions: dict[str, float]) -> None:
    """Atomically persist sessions with owner-only permissions."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    with _SESSION_LOCK:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=SESSION_FILE.parent,
                prefix=f".{SESSION_FILE.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
                json.dump(sessions, temporary_file, separators=(",", ":"))
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, SESSION_FILE)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass


def get_current_user(request: Request) -> bool:
    cached = getattr(request.state, "_homepage_upload_authenticated", _AUTH_CACHE_MISSING)
    if cached is not _AUTH_CACHE_MISSING:
        return bool(cached)

    token = request.cookies.get(SESSION_KEY)
    if not token:
        request.state._homepage_upload_authenticated = False
        return False
    with _SESSION_LOCK:
        sessions = _load_sessions()
        expiry = sessions.get(token)
        if expiry and expiry > time.time():
            request.state._homepage_upload_authenticated = True
            return True
        if expiry is not None:
            sessions.pop(token, None)
            _save_sessions(sessions)
    request.state._homepage_upload_authenticated = False
    return False


def _require_same_origin(request: Request) -> None:
    """Reject browser-originated unsafe requests from another origin.

    Non-browser clients commonly omit Origin and Sec-Fetch-Site, so an absent
    pair remains valid. Browsers provide at least one of them for cross-site
    form/fetch requests, complementing the SameSite cookie policy.
    """

    if request.method.upper() in _SAFE_METHODS:
        return

    origin = request.headers.get("origin")
    if origin:
        supplied = urlsplit(origin)
        expected = urlsplit(str(request.base_url))
        if (supplied.scheme, supplied.netloc) != (expected.scheme, expected.netloc):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden origin")
        return

    if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden origin")


def require_login(request: Request) -> None:
    if not get_current_user(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    _require_same_origin(request)


def verify_credentials(username: str, password: str) -> bool:
    """Verify configured credentials and fail closed when no hash exists."""
    user_ok = secrets.compare_digest(username, UPLOAD_USERNAME)
    if not UPLOAD_PASSWORD_HASH:
        return False
    try:
        password_ok = pwd_context.verify(password, UPLOAD_PASSWORD_HASH)
    except (TypeError, ValueError):
        return False
    return user_ok and password_ok


def create_session() -> str:
    with _SESSION_LOCK:
        sessions = _load_sessions()
        token = secrets.token_urlsafe(32)
        sessions[token] = time.time() + SESSION_TIMEOUT_SECONDS
        _save_sessions(sessions)
    return token


def destroy_session(token: str) -> None:
    with _SESSION_LOCK:
        sessions = _load_sessions()
        if token in sessions:
            del sessions[token]
            _save_sessions(sessions)


def get_cookie_settings() -> dict:
    return {
        "key": SESSION_KEY,
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": "lax",
        "max_age": SESSION_TIMEOUT_SECONDS,
    }
