"""
TruthLens AI/ML — Module 11: Claim Router API Tests
Verifies FastAPI endpoints POST /api/v1/analyze/claims, POST /api/claim/analyze,
GET /api/claim/health, GET /, and GET /health.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from config.settings import settings


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestClaimRouter:

    def test_post_claims_v1_success(self, client):
        payload = {
            "text": "The Prime Minister announced a 15 billion euro relief package in Paris on Monday.",
            "source_type": "TRANSCRIPT",
            "language": "en",
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

    def test_post_claims_v1_empty_text(self, client):
        response = client.post("/api/v1/analyze/claims", json={"text": "", "source_type": "OCR"})
        assert response.status_code == 200
        data = response.json()
        assert data["claims_count"] == 0
        assert data["claims"] == []
        assert data["entities"] == []

    def test_post_claims_v1_oversized_text_returns_400(self, client):
        huge_text = "Word " * (settings.claim_max_text_length // 4 + 10)
        response = client.post("/api/v1/analyze/claims", json={"text": huge_text})
        assert response.status_code == 400
        assert "exceeds maximum allowed limit" in response.json()["detail"]

    def test_post_claims_module_route(self, client):
        payload = {
            "text": "NASA launched the Europa Clipper spacecraft toward Jupiter.",
            "source_type": "DIRECT_TEXT",
        }
        response = client.post("/api/claim/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["claims_count"] == 1
        assert "NASA" in data["claims"][0]["subject"]

    def test_claim_health_endpoint(self, client):
        response = client.get("/api/claim/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["module"] == "11-claim-analysis"
        assert "engine" in data

    def test_main_root_includes_module_11(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "11-claim-analysis" in data["modules"]

    def test_main_health_includes_claim_analysis(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["modules"]["claim_analysis"] == "healthy"
