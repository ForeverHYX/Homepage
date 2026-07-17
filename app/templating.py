"""Shared Jinja environment and template helpers."""

from __future__ import annotations

from fastapi.templating import Jinja2Templates

from app.assets import asset_url
from app.config import BASE_DIR


templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
templates.env.globals["asset_url"] = asset_url
