from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
)
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import BASE_DIR, ENABLE_API_DOCS, limiter
from app.routers import auth, media, pages, upload
from app.templating import templates


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Render the styled 404 page for browser navigation requests instead of raw JSON.

    Scoped to HTML/text traffic so API clients and asset fetches still receive the
    conventional error response shape.
    """
    accept = request.headers.get("accept", "")
    if (
        exc.status_code == 404
        and "text/html" in accept
        and not request.url.path.startswith(("/api/", "/static/", "/uploads/"))
    ):
        return templates.TemplateResponse(
            request, "pages/404.html", {"detail": exc.detail}, status_code=404
        )
    return await default_http_exception_handler(request, exc)


def create_app() -> FastAPI:
    """Create the complete ASGI application for tests and production."""
    application = FastAPI(
        title="Yixun Hong's Homepage",
        version="1.0.0",
        docs_url="/docs" if ENABLE_API_DOCS else None,
        redoc_url="/redoc" if ENABLE_API_DOCS else None,
        openapi_url="/openapi.json" if ENABLE_API_DOCS else None,
    )
    application.state.limiter = limiter
    application.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,
    )
    application.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler,
    )

    # Nginx serves fingerprinted static assets in production. Uploaded media
    # uses the media router so authorization is identical in every environment.
    application.mount(
        "/static",
        StaticFiles(directory=str(BASE_DIR / "static")),
        name="static",
    )
    application.include_router(media.router)
    application.include_router(pages.router)
    application.include_router(upload.router)
    application.include_router(auth.router)
    return application


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
