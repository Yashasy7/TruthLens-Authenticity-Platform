"""
TruthLens AI/ML Microservice — FastAPI Application Entry Point
Blueprint Section D:  Python FastAPI AI inference engine
Blueprint Section E:  FastAPI (Async Uvicorn), Python 3.11

This service exposes the AI/ML analysis endpoints consumed internally by the
Spring Boot backend orchestration gateway (Module 19 job worker).

Startup:
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload   (development)
    uvicorn main:app --host 0.0.0.0 --port 8001             (production)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from services.image_analysis.classifier import load_model
from services.image_analysis.router import router as image_router

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.ai-ml")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.
    Runs startup tasks before serving requests and teardown tasks on shutdown.
    """
    # --- Startup ---
    logger.info("TruthLens AI/ML Service starting up …")
    settings.ensure_dirs()           # Create storage/ and models/ directories
    load_model()                     # Pre-load PyTorch model into memory
    logger.info("AI/ML Service ready on %s:%d", settings.host, settings.port)

    yield

    # --- Shutdown ---
    logger.info("TruthLens AI/ML Service shutting down.")


app = FastAPI(
    title="TruthLens AI/ML Service",
    description=(
        "Internal AI inference microservice for the TruthLens platform. "
        "Provides Module 05 (Image Authenticity), and future modules for "
        "video deepfake detection, audio forensics, OCR, and speech-to-text. "
        "Consumed by the Spring Boot backend orchestration gateway."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS: restrict to internal traffic only.
# In production, ALLOWED_ORIGINS should be set to the Spring Boot backend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://backend:8080"],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

# --- Register routers ---
app.include_router(image_router)


@app.get("/", tags=["Root"])
def root() -> dict:
    """Service root — confirms the AI/ML microservice is running."""
    return {
        "service": "TruthLens AI/ML Microservice",
        "version": "0.1.0",
        "modules": ["05-image-authenticity"],
        "docs": "/docs",
    }
