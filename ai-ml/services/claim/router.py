"""
TruthLens AI/ML — Module 11: Text & Claim Analysis API Router
Blueprint Section D: Exposes POST /api/v1/analyze/claims consumed internally
by Spring Boot FastApiClaimServiceClient (Module 11 gateway).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from config.settings import settings
from schemas.claim import (
    FastApiClaimRequest,
    FastApiClaimResponse,
)
from services.claim.engine import get_claim_engine
from services.claim.service import get_claim_service

logger = logging.getLogger("truthlens.ai-ml.claim.router")

# Authoritative Spring Boot v1 router
claim_v1_router = APIRouter(prefix="/api/v1/analyze", tags=["Module 11 — Text & Claim Analysis (v1)"])

# Module-scoped legacy / internal router
claim_router = APIRouter(prefix="/api/claim", tags=["Module 11 — Text & Claim Analysis"])


@claim_v1_router.post(
    "/claims",
    response_model=FastApiClaimResponse,
    status_code=status.HTTP_200_OK,
    summary="Decompose text into structured claims and extract named entities (Primary Spring Boot Endpoint)",
    description=(
        "Primary REST endpoint called by Spring Boot FastApiClaimServiceClient. "
        "Accepts raw text (from OCR visual extraction, speech transcripts, or direct user input), "
        "normalizes Unicode text, extracts named entities (NER), classifies sentences into ClaimType, "
        "and decomposes statements into structured SVO claim objects with deterministic SHA-256 hashes."
    ),
)
async def analyze_claims_v1(request: FastApiClaimRequest) -> FastApiClaimResponse:
    """Authoritative API endpoint matching Spring Boot FastApiClaimServiceClient."""
    service = get_claim_service()
    try:
        return service.analyze_claims(request)
    except ValueError as exc:
        logger.warning("Claim analysis validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error("Claim analysis runtime engine failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in claim analysis pipeline: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing text claims.",
        ) from exc


@claim_router.post(
    "/analyze",
    response_model=FastApiClaimResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze claims and named entities (Module route)",
)
async def analyze_claims_module(request: FastApiClaimRequest) -> FastApiClaimResponse:
    """Module-level endpoint alias for internal testing and pipeline integration."""
    return await analyze_claims_v1(request)


@claim_router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check for Module 11 NLP Claim Analysis service",
)
async def claim_health() -> Dict[str, Any]:
    """Module health probe verifying NLP engine readiness."""
    try:
        engine = get_claim_engine()
        return {
            "status": "healthy",
            "module": "11-claim-analysis",
            "engine": type(engine).__name__,
            "spacy_model": settings.spacy_model,
            "max_text_length": settings.claim_max_text_length,
            "max_sentences": settings.claim_max_sentences,
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "module": "11-claim-analysis",
            "error": str(exc),
        }
