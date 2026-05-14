import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.database import init_db
from src.routes import auth, chat, dashboards, health, rubric, stateless
from src.services.auth_service import require_auth

# Initialize database
init_db()

app = FastAPI(
    title="PowerBI Vision Chatbot API",
    description="REST API for PowerBI Vision Chatbot",
    version="0.1.0",
)

# CORS middleware - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
os.makedirs(settings.upload_dir, exist_ok=True)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Include routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(
    dashboards.router,
    prefix="/dashboards",
    tags=["dashboards"],
    dependencies=[Depends(require_auth)],
)
app.include_router(chat.router, prefix="/chat", tags=["chat"], dependencies=[Depends(require_auth)])
app.include_router(
    rubric.router,
    prefix="/rubric",
    tags=["rubric"],
    dependencies=[Depends(require_auth)],
)
app.include_router(stateless.router, tags=["stateless"], dependencies=[Depends(require_auth)])

# Vercel serves this FastAPI app below /api. Keep local routes unchanged while also
# exposing the same API under /api/* for the deployed frontend.
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(
    dashboards.router,
    prefix="/api/dashboards",
    tags=["dashboards"],
    dependencies=[Depends(require_auth)],
)
app.include_router(
    chat.router,
    prefix="/api/chat",
    tags=["chat"],
    dependencies=[Depends(require_auth)],
)
app.include_router(
    rubric.router,
    prefix="/api/rubric",
    tags=["rubric"],
    dependencies=[Depends(require_auth)],
)
app.include_router(
    stateless.router,
    prefix="/api",
    tags=["stateless"],
    dependencies=[Depends(require_auth)],
)

@app.get("/")
async def root():
    return {
        "message": "PowerBI Vision Chatbot",
        "version": "0.1.0",
        "docs": "/docs"
    }
