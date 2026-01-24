from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.config import UPLOAD_DIR
from app.routers import pages, upload

app = FastAPI(title="Yixun Hong's Homepage", version="0.4.1")

# Mount Static Files (Uploads)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include Routers
app.include_router(pages.router)
app.include_router(upload.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
