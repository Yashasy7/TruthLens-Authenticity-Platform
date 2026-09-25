"""
TruthLens AI/ML — Module 11: Text & Claim Analysis Service
Blueprint Section D: Ingests OCR visual text, timestamped transcripts, or direct text queries,
performs text normalization, NER, sentence classification, semantic claim decomposition,
provenance preservation, cross-source deduplication, and forensic evidence tracking.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config.settings import settings
from schemas.claim import (
    ClaimAnalysisRequest,
    FastApiClaimRequest,
    FastApiClaimResponse,
    FastApiStructuredClaim,
)
from services.claim.engine import BaseClaimEngine, get_claim_engine
from services.claim.preprocessor import ClaimTextPreprocessor

logger = logging.getLogger("truthlens.ai-ml.claim.service")


class ClaimAnalysisService:
    """
    High-level business service orchestrating Module 11 text and claim analysis pipelines.
    Handles cross-modal inputs (OCR regions, audio transcripts, direct text),
    preserves source provenance (timestamps, bounding boxes), and performs deterministic deduplication.
    """

    def __init__(self, engine: Optional[BaseClaimEngine] = None):
        self._engine = engine or get_claim_engine()

    def analyze_claims(
        self,
        request: FastApiClaimRequest,
    ) -> FastApiClaimResponse:
        """
        Executes claim analysis on the given request.
        """
        raw_text = request.text or ""
        source_type = request.source_type or "DIRECT_TEXT"
        language = request.language or "en"

        # Validate input size
        if len(raw_text) > settings.claim_max_text_length:
            raise ValueError(
                f"Input text length ({len(raw_text)} chars) exceeds maximum allowed limit ({settings.claim_max_text_length} chars)."
            )

        # Handle empty or blank text
        clean_text = ClaimTextPreprocessor.normalize_text(raw_text)
        if not clean_text and not request.ocr_regions and not request.transcript_segments:
            return self._engine.analyze(
                text="",
                source_type=source_type,
                language=language,
            )

        # If transcript segments provided and text is empty, reconstruct from segments
        if not clean_text and request.transcript_segments:
            seg_texts = [s.get("text", "") for s in request.transcript_segments if s.get("text")]
            clean_text = ClaimTextPreprocessor.normalize_text(" ".join(seg_texts))

        # If OCR regions provided and text is empty, reconstruct from regions
        if not clean_text and request.ocr_regions:
            region_texts = [r.get("text", "") for r in request.ocr_regions if r.get("text")]
            clean_text = ClaimTextPreprocessor.normalize_text(" ".join(region_texts))

        # Execute core NLP decomposition
        response = self._engine.analyze(
            text=clean_text,
            source_type=source_type,
            language=language,
            ocr_regions=request.ocr_regions,
            transcript_segments=request.transcript_segments,
        )

        # Enrich provenance if transcript segments or OCR regions were passed
        if request.transcript_segments and response.claims:
            self._attach_transcript_provenance(response.claims, request.transcript_segments)

        if request.ocr_regions and response.claims:
            self._attach_ocr_provenance(response.claims, request.ocr_regions)

        # Cross-source deduplication if requested or combined
        if source_type in ["COMBINED", "OCR"]:
            response.claims = self._deduplicate_claims(response.claims)
            response.claims_count = len(response.claims)
            if response.evidence:
                response.evidence.claims_count = len(response.claims)

        # Explicitly tag that factuality/truth verification is strictly downstream (Module 12)
        if response.evidence:
            response.evidence.details["factuality_verified"] = False
            response.evidence.details["verification_boundary"] = "Extraction confidence only; truth verification belongs to Module 12"

        return response

    def _attach_transcript_provenance(
        self,
        claims: List[FastApiStructuredClaim],
        segments: List[Dict[str, Any]]
    ) -> None:
        """
        Associates speech segment timestamps with extracted claims based on text overlap.
        """
        for claim in claims:
            c_text_lower = claim.claim_text.lower()
            for seg in segments:
                s_text_lower = seg.get("text", "").lower()
                if c_text_lower in s_text_lower or s_text_lower in c_text_lower:
                    claim.start_time = seg.get("start")
                    claim.end_time = seg.get("end")
                    claim.source_type = "TRANSCRIPT"
                    break

    def _attach_ocr_provenance(
        self,
        claims: List[FastApiStructuredClaim],
        regions: List[Dict[str, Any]]
    ) -> None:
        """
        Associates OCR bounding box metadata with extracted claims based on text overlap.
        """
        for claim in claims:
            c_text_lower = claim.claim_text.lower()
            for reg in regions:
                r_text_lower = reg.get("text", "").lower()
                if c_text_lower in r_text_lower or r_text_lower in c_text_lower:
                    claim.bounding_box = reg.get("bounding_box")
                    claim.source_type = "OCR"
                    break

    def _deduplicate_claims(
        self,
        claims: List[FastApiStructuredClaim]
    ) -> List[FastApiStructuredClaim]:
        """
        Performs deterministic deduplication of repeated claims (e.g. repeated news tickers),
        preserving provenance across duplicates.
        """
        seen_hashes = set()
        deduped: List[FastApiStructuredClaim] = []

        for claim in claims:
            if claim.claim_hash not in seen_hashes:
                seen_hashes.add(claim.claim_hash)
                deduped.append(claim)

        return deduped


# Service singleton
_service_instance: Optional[ClaimAnalysisService] = None


def get_claim_service() -> ClaimAnalysisService:
    """Returns singleton instance of ClaimAnalysisService."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ClaimAnalysisService()
    return _service_instance
