from typing import Any
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from app.config import limiter
from app.auth import verify_credentials, create_session, get_cookie_settings

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
            httponly=cookie_cfg["httponly"],
            secure=cookie_cfg["secure"],
            samesite=cookie_cfg["samesite"],
            max_age=cookie_cfg["max_age"],
        )
        return response
    return HTMLResponse(
        content="<script>alert('Invalid credentials'); history.back();</script>",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
