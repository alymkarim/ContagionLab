# Backend FastAPI application with CORS middleware and health endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers.assets import router as assets_router
from backend.app.routers.networks import router as networks_router
from backend.app.routers.stress_test import router as stress_test_router

# Create FastAPI application instance
app = FastAPI(title="ContagionLab API", version="0.1.0")

# Configure CORS to allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(assets_router)
app.include_router(networks_router)
app.include_router(stress_test_router)


@app.get("/health")
def health_check():
    """
    Health check endpoint to verify API is running.
    Returns a simple status dictionary.
    """
    return {"status": "ok"}