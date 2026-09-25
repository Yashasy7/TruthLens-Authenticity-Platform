import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.claim_extractor import ClaimExtractor
from app.config import settings


@pytest.fixture
def claim_extractor():
    return ClaimExtractor()


def test_claim_extractor_initialization(claim_extractor):
    """Verifies that spaCy pipeline is properly initialized and cached."""
    assert claim_extractor._is_initialized is True
    assert claim_extractor._nlp is not None


def test_claim_extractor_ner_recognition(claim_extractor):
    """Verifies NER extracts persons, organizations, locations, dates, and currency."""
    text = "Satya Nadella spoke at Microsoft headquarters in Redmond on January 15 regarding a $10 billion investment."
    result = claim_extractor.analyze(text)

    assert result.status == "COMPLETED"
    assert len(result.entities) >= 3

    labels = {e.normalized_label for e in result.entities}
    # Expected standard categories
    assert any(label in labels for label in ["PERSON", "ORG", "LOCATION", "DATE", "MONEY", "QUANTITY"])


def test_claim_extractor_sentence_classification_factual(claim_extractor):
    """Verifies declarative statement with factual predicate is classified as FACTUAL_CLAIM."""
    text = "The Ministry of Health announced 5,000 new medical positions across 12 regions."
    result = claim_extractor.analyze(text)

    assert result.claims_count == 1
    claim = result.claims[0]
    assert claim.claim_type == "FACTUAL_CLAIM"
    assert claim.confidence_score >= 0.70
    assert claim.subject is not None
    assert claim.action is not None


def test_claim_extractor_sentence_classification_opinion(claim_extractor):
    """Verifies that subjective statements are classified as OPINION."""
    text = "In my opinion, this is the worst policy in modern history."
    result = claim_extractor.analyze(text)

    assert result.claims_count == 1
    claim = result.claims[0]
    assert claim.claim_type == "OPINION"
    assert claim.confidence_score >= 0.70


def test_claim_extractor_sentence_classification_question(claim_extractor):
    """Verifies that questions are classified as QUESTION."""
    text = "Why did the committee reject the proposed amendments yesterday?"
    result = claim_extractor.analyze(text)

    assert result.claims_count == 1
    claim = result.claims[0]
    assert claim.claim_type == "QUESTION"


def test_claim_extractor_sentence_classification_non_claim(claim_extractor):
    """Verifies that short commands or conversational fragments are classified as NON_CLAIM."""
    text = "Click here now."
    result = claim_extractor.analyze(text)

    assert result.claims_count == 1
    claim = result.claims[0]
    assert claim.claim_type == "NON_CLAIM"


def test_claim_extractor_semantic_decomposition(claim_extractor):
    """Verifies decomposition into (subject, action, value)."""
    text = "NASA launched the Europa Clipper spacecraft toward Jupiter."
    result = claim_extractor.analyze(text)

    assert result.claims_count == 1
    claim = result.claims[0]
    assert "NASA" in (claim.subject or "")
    assert "launched" in (claim.action or "")
    assert claim.value is not None


def test_claim_extractor_deterministic_hashing(claim_extractor):
    """Verifies claim hash is 64 hex characters (SHA-256) and strictly deterministic."""
    text = "The Federal Reserve raised interest rates by 25 basis points."
    res1 = claim_extractor.analyze(text)
    res2 = claim_extractor.analyze(text)

    hash1 = res1.claims[0].claim_hash
    hash2 = res2.claims[0].claim_hash

    assert len(hash1) == 64
    assert hash1 == hash2


def test_claim_extractor_empty_text_handling(claim_extractor):
    """Verifies empty or whitespace-only text returns empty result without errors."""
    res_empty = claim_extractor.analyze("")
    assert res_empty.claims_count == 0
    assert len(res_empty.claims) == 0
    assert len(res_empty.entities) == 0

    res_whitespace = claim_extractor.analyze("   \n\t  ")
    assert res_whitespace.claims_count == 0


def test_claim_extractor_oversized_text_rejection():
    """Verifies that text exceeding maximum character length raises ValueError."""
    small_extractor = ClaimExtractor(max_text_length=50)
    oversized = "A" * 100

    with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
        small_extractor.analyze(oversized)


def test_api_analyze_claims_success():
    """Tests FastAPI POST /api/v1/analyze/claims endpoint with valid payload."""
    client = TestClient(app)
    payload = {
        "text": "The European Union approved the landmark Artificial Intelligence Act in Brussels.",
        "source_type": "TRANSCRIPT",
        "language": "en"
    }

    response = client.post("/api/v1/analyze/claims", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["source_type"] == "TRANSCRIPT"
    assert data["claims_count"] >= 1
    assert len(data["claims"]) >= 1

    first_claim = data["claims"][0]
    assert "claim_text" in first_claim
    assert "claim_hash" in first_claim
    assert "subject" in first_claim
    assert "action" in first_claim
    assert "value" in first_claim
    assert "entity_type" in first_claim
    assert "confidence_score" in first_claim
    assert len(first_claim["claim_hash"]) == 64


def test_api_analyze_claims_empty_text():
    """Tests FastAPI POST /api/v1/analyze/claims endpoint with empty text payload."""
    client = TestClient(app)
    response = client.post("/api/v1/analyze/claims", json={"text": "", "source_type": "OCR"})
    assert response.status_code == 200
    data = response.json()
    assert data["claims_count"] == 0
    assert data["claims"] == []


def test_api_analyze_claims_oversized_text():
    """Tests FastAPI POST /api/v1/analyze/claims endpoint with text exceeding limit."""
    client = TestClient(app)
    huge_text = "Word " * (settings.CLAIM_MAX_TEXT_LENGTH // 4 + 10)
    response = client.post("/api/v1/analyze/claims", json={"text": huge_text})
    assert response.status_code == 400
    assert "exceeds maximum allowed limit" in response.json()["detail"]
