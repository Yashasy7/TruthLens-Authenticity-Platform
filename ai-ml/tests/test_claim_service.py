"""
TruthLens AI/ML — Module 11: Claim Analysis Service Tests
Verifies orchestration across OCR inputs (Module 09), Speech Transcripts (Module 10),
source provenance preservation, deterministic deduplication, and factuality separation.
"""

import pytest
from schemas.claim import FastApiClaimRequest
from services.claim.service import ClaimAnalysisService


@pytest.fixture
def claim_service():
    return ClaimAnalysisService()


class TestClaimService:

    def test_direct_text_analysis(self, claim_service):
        req = FastApiClaimRequest(
            text="The European Union approved the landmark Artificial Intelligence Act in Brussels.",
            source_type="DIRECT_TEXT",
            language="en",
        )
        res = claim_service.analyze_claims(req)

        assert res.status == "COMPLETED"
        assert res.source_type == "DIRECT_TEXT"
        assert res.claims_count >= 1
        assert res.claims[0].entity_type in ["EVENT", "ORG", "LOCATION", "GENERAL"]
        assert res.evidence is not None
        assert res.evidence.details.get("factuality_verified") is False

    def test_ocr_input_provenance_attachment(self, claim_service):
        # Emulating visual text regions from Module 09 OCR
        ocr_regions = [
            {
                "text": "Breaking News: Candidate X won the national election in 2024.",
                "confidence": 0.94,
                "bounding_box": {"x": 50, "y": 400, "width": 600, "height": 45},
            }
        ]
        req = FastApiClaimRequest(
            text="",
            source_type="OCR",
            language="en",
            ocr_regions=ocr_regions,
        )
        res = claim_service.analyze_claims(req)

        assert res.status == "COMPLETED"
        assert res.source_type == "OCR"
        assert res.claims_count >= 1
        claim = res.claims[0]
        assert claim.source_type == "OCR"
        assert claim.bounding_box is not None
        assert claim.bounding_box["x"] == 50

    def test_transcript_input_provenance_attachment(self, claim_service):
        # Emulating speech transcript segments from Module 10 STT
        segments = [
            {
                "id": 0,
                "start": 1.25,
                "end": 4.80,
                "text": "The Prime Minister announced a 15 billion euro relief package.",
                "confidence": 0.95,
            }
        ]
        req = FastApiClaimRequest(
            text="",
            source_type="TRANSCRIPT",
            language="en",
            transcript_segments=segments,
        )
        res = claim_service.analyze_claims(req)

        assert res.status == "COMPLETED"
        assert res.source_type == "TRANSCRIPT"
        assert res.claims_count >= 1
        claim = res.claims[0]
        assert claim.source_type == "TRANSCRIPT"
        assert claim.start_time == 1.25
        assert claim.end_time == 4.80

    def test_combined_ocr_deduplication(self, claim_service):
        # Emulating a repeated news ticker in OCR
        text = (
            "Headline: Market reached an all-time high today. "
            "Headline: Market reached an all-time high today. "
            "Headline: Market reached an all-time high today."
        )
        req = FastApiClaimRequest(
            text=text,
            source_type="OCR",
            language="en",
        )
        res = claim_service.analyze_claims(req)

        # Deduplication merges repeated identical ticker headlines
        assert res.claims_count == 1

    def test_empty_request_returns_empty_completed(self, claim_service):
        req = FastApiClaimRequest(text="", source_type="DIRECT_TEXT")
        res = claim_service.analyze_claims(req)
        assert res.status == "COMPLETED"
        assert res.claims_count == 0
        assert res.entities == []
        assert res.claims == []

    def test_oversized_text_raises_value_error(self, claim_service):
        from config.settings import settings
        huge_text = "Word " * (settings.claim_max_text_length // 4 + 10)
        req = FastApiClaimRequest(text=huge_text)

        with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
            claim_service.analyze_claims(req)
