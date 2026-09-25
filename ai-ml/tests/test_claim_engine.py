"""
TruthLens AI/ML — Module 11: Claim Engine Tests
Verifies engine factory, singleton management, strict mode enforcement,
and max sentences clipping.
"""

import pytest
from config.settings import settings
from services.claim.engine import (
    RuleBasedClaimEngine,
    SpaCyClaimEngine,
    get_claim_engine,
    reset_claim_engine,
)


class TestClaimEngine:

    def test_get_claim_engine_singleton(self):
        reset_claim_engine()
        e1 = get_claim_engine()
        e2 = get_claim_engine()
        assert e1 is e2

    def test_strict_mode_enforcement(self, monkeypatch):
        reset_claim_engine()
        # Force require_nlp_model to True and make spacy unavailable
        monkeypatch.setattr(settings, "require_nlp_model", True)
        monkeypatch.setattr("services.claim.engine.SPACY_AVAILABLE", False)

        with pytest.raises(RuntimeError, match="Production NLP model required"):
            get_claim_engine()

        reset_claim_engine()

    def test_max_sentences_clipping(self):
        engine = RuleBasedClaimEngine(max_sentences=2)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        res = engine.analyze(text)

        assert res.sentences_count == 2
        assert res.evidence.details.get("max_sentences_applied") is True

    def test_all_claim_confidence_scores_bounded(self):
        engine = RuleBasedClaimEngine()
        text = (
            "The Minister announced 1,000 new jobs. "
            "I think this is great. "
            "Who asked for this?"
        )
        res = engine.analyze(text)
        for claim in res.claims:
            assert 0.0 <= claim.confidence_score <= 1.0
