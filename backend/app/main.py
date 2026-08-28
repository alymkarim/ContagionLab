# Backend FastAPI application with CORS middleware and health endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.assets import router as assets_router
from app.routers.networks import router as networks_router
from app.routers.stress_test import router as stress_test_router
from app.routers.crisis import router as crisis_router
from app.routers.fragility import router as fragility_router

# Create FastAPI application instance
app = FastAPI(title="ContagionLab API", version="0.2.0")

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
app.include_router(crisis_router)
app.include_router(fragility_router)


@app.get("/health")
def health_check():
    """
    Health check endpoint to verify API is running.
    Returns a simple status dictionary.
    """
    return {"status": "ok"}