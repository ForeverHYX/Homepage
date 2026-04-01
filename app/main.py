from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from app.config import UPLOAD_DIR
from app.routers import pages, upload

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Yixun Hong's Homepage", version="0.5.0")

# Jinja2 Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.state.templates = templates

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include Routers
app.include_router(pages.router)
app.include_router(upload.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
