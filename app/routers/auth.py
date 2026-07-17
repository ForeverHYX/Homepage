from typing import Any

from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import (
    SESSION_KEY,
    create_session,
    destroy_session,
    get_cookie_settings,
    require_login,
    verify_credentials,
)
from app.config import limiter

router = APIRouter()


@router.post("/api/login")
@limiter.limit("10/minute")
def api_login(request: Request, username: str = Form(...), password: str = Form(...)) -> Any:
    username = username.strip()
    if verify_credentials(username, password):
        token = create_session()
        response = RedirectResponse(url="/upload", status_code=status.HTTP_303_SEE_OTHER)
        cookie_cfg = get_cookie_settings()
        response.set_cookie(
            key=cookie_cfg["key"],
            value=token,
            path=cookie_cfg["path"],
            httponly=cookie_cfg["httponly"],
            secure=cookie_cfg["secure"],
            samesite=cookie_cfg["samesite"],
            max_age=cookie_cfg["max_age"],
        )
        response.headers["Cache-Control"] = "private, no-store"
        return response
    return HTMLResponse(
        content="<script>alert('Invalid credentials'); history.back();</script>",
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/api/logout")
def api_logout(request: Request) -> RedirectResponse:
    """End the current upload session and remove its browser cookie."""
    require_login(request)
    token = request.cookies.get(SESSION_KEY)
    if token:
        destroy_session(token)

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    cookie_cfg = get_cookie_settings()
    response.delete_cookie(
        key=cookie_cfg["key"],
        path=cookie_cfg["path"],
        httponly=cookie_cfg["httponly"],
        secure=cookie_cfg["secure"],
        samesite=cookie_cfg["samesite"],
    )
    response.headers.update(
        {
            "Cache-Control": "private, no-store",
            "X-Robots-Tag": "noindex, nofollow",
        }
    )
    return response
