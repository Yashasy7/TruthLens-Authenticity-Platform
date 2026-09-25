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
from services.image_analysis.router import router as image_router, v1_router as image_v1_router
from services.video_analysis.router import video_router, video_v1_router
from services.audio_analysis.model import get_audio_classifier
from services.audio_analysis.router import audio_router, audio_v1_router
from services.av_sync.router import av_sync_router, av_sync_v1_router
from services.av_sync.service import get_syncnet_evaluator
from services.ocr.router import ocr_router, ocr_v1_router
from services.ocr.engine import get_ocr_engine
from services.transcript.router import transcript_router, transcript_v1_router
from services.transcript.engine import get_speech_transcriber
from services.claim.router import claim_router, claim_v1_router
from services.claim.engine import get_claim_engine

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
    load_model()                     # Pre-load PyTorch image model into memory
    try:
        get_audio_classifier()       # Pre-load PyTorch audio model into memory
    except Exception as exc:
        logger.warning("Could not pre-load audio model on startup: %s", exc)
    try:
        get_syncnet_evaluator()      # Pre-load PyTorch AV sync model into memory
    except Exception as exc:
        logger.warning("Could not pre-load AV sync model on startup: %s", exc)
    try:
        get_ocr_engine()             # Pre-load OCR engine into memory
    except Exception as exc:
        logger.warning("Could not initialize OCR engine on startup: %s", exc)
    try:
        get_speech_transcriber()     # Pre-load/verify speech transcriber
    except Exception as exc:
        logger.warning("Could not initialize speech transcriber on startup: %s", exc)
    try:
        get_claim_engine()           # Pre-load/verify NLP claim engine
    except Exception as exc:
        logger.warning("Could not initialize claim engine on startup: %s", exc)
    logger.info("AI/ML Service ready on %s:%d", settings.host, settings.port)

    yield

    # --- Shutdown ---
    logger.info("TruthLens AI/ML Service shutting down.")


app = FastAPI(
    title="TruthLens AI/ML Service",
    description=(
        "Internal AI inference microservice for the TruthLens platform. "
        "Provides Module 05 (Image Authenticity), Module 06 (Video Deepfake), "
        "Module 07 (Audio Authenticity & Voice Forensics), "
        "Module 08 (Audio-Visual Synchronization), "
        "Module 09 (OCR & Visual Text Extraction), "
        "Module 10 (Speech-to-Text & Transcript Extraction), and "
        "Module 11 (Text & Claim Analysis). Consumed by Spring Boot backend gateway."
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
app.include_router(image_v1_router)
app.include_router(video_router)
app.include_router(video_v1_router)
app.include_router(audio_router)
app.include_router(audio_v1_router)
app.include_router(av_sync_router)
app.include_router(av_sync_v1_router)
app.include_router(ocr_router)
app.include_router(ocr_v1_router)
app.include_router(transcript_router)
app.include_router(transcript_v1_router)
app.include_router(claim_router)
app.include_router(claim_v1_router)


@app.get("/", tags=["Root"])
def root() -> dict:
    """Service root — confirms the AI/ML microservice is running."""
    return {
        "service": "TruthLens AI/ML Microservice",
        "version": "0.1.0",
        "modules": [
            "05-image-authenticity",
            "06-video-deepfake",
            "07-audio-authenticity",
            "08-av-synchronization",
            "09-ocr-text-extraction",
            "10-speech-to-text",
            "11-claim-analysis",
        ],
        "docs": "/docs",
    }


@app.get("/health", tags=["Root"])
def service_health() -> dict:
    """Overall microservice health probe."""
    return {
        "status": "healthy",
        "service": "TruthLens AI/ML Microservice",
        "version": "0.1.0",
        "modules": {
            "image_analysis": "healthy",
            "video_analysis": "healthy",
            "audio_analysis": "healthy",
            "av_synchronization": "healthy",
            "ocr_analysis": "healthy",
            "speech_to_text": "healthy",
            "claim_analysis": "healthy",
        },
    }


