from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import UPLOAD_DIR, limiter
from app.routers import pages, upload, auth

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Yixun Hong's Homepage", version="0.7.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Mount Static Files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Jinja2 Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Render the styled 404 page for browser navigation requests instead of raw JSON.

    Scoped to HTML/text traffic so API clients and asset fetches still receive the
    conventional error response shape.
    """
    accept = request.headers.get("accept", "")
    if exc.status_code == 404 and "text/html" in accept and not request.url.path.startswith(("/api/", "/static/", "/uploads/")):
        return templates.TemplateResponse(
            request, "pages/404.html", {"detail": exc.detail}, status_code=404
        )
    from fastapi.exception_handlers import http_exception_handler as _default
    return await _default(request, exc)

# Include Routers
app.include_router(pages.router)
app.include_router(upload.router)
app.include_router(auth.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
