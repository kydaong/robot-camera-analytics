"""
Main FastAPI application
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1 import chat, inspection, workflow, xmpro
from app.config import settings
from app.core.database import create_tables
from app.core.vector_store import ensure_collections

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered robot camera analytics for industrial inspections. "
        "Mode 1: AI coworker for CMMS & standards queries. "
        "Mode 2: Spot inspection insight generator with human-approval workflow."
    ),
)

# CORS middleware — restrict origins in production via ALLOWED_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
API_PREFIX = "/api/v1"
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(inspection.router, prefix=API_PREFIX)
app.include_router(workflow.router, prefix=API_PREFIX)
app.include_router(xmpro.router, prefix=API_PREFIX)


@app.on_event("startup")
async def startup():
    create_tables()
    ensure_collections()


_FRONTEND = Path(__file__).parent.parent / "frontend"
_IMAGES = Path(__file__).parent.parent / "data" / "sample_images"

# Serve robot images so the UI can display them
app.mount("/images", StaticFiles(directory=str(_IMAGES)), name="images")


@app.get("/ui", include_in_schema=False)
async def serve_ui():
    return FileResponse(_FRONTEND / "index.html")


@app.get("/")
async def root():
    return {
        "message": "Robot Camera Analytics API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "ui": "/ui",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)