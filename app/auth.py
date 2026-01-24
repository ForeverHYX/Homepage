import secrets
import os
from fastapi import Request, HTTPException, status

# Security Config
UPLOAD_USERNAME = os.getenv("HOMEPAGE_UPLOAD_USER", "admin")
UPLOAD_PASSWORD = os.getenv("HOMEPAGE_UPLOAD_PASS", "changeme")
SESSION_KEY = "session_token"
VALID_SESSIONS = set()

def get_current_user(request: Request) -> bool:
    token = request.cookies.get(SESSION_KEY)
    if token and token in VALID_SESSIONS:
        return True
    return False

def require_login(request: Request) -> None:
    if not get_current_user(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
