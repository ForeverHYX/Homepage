"""Shared Jinja environment and template helpers."""

from __future__ import annotations

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.assets import asset_url
from app.auth import get_current_user
from app.config import BASE_DIR


def _authentication_context(request: Request) -> dict[str, bool]:
    return {"show_upload_navigation": get_current_user(request)}


templates = Jinja2Templates(
    directory=str(BASE_DIR / "app" / "templates"),
    context_processors=[_authentication_context],
)
templates.env.globals["asset_url"] = asset_url
