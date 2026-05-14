from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import grade, health

app = FastAPI(
    title="PowerBI Vision AI Service",
    description="Claude Vision API integration for PowerBI dashboard analysis",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(grade.router)

@app.get("/")
async def root():
    return {
        "message": "PowerBI Vision AI Service",
        "version": "0.1.0",
        "docs": "/docs"
    }
