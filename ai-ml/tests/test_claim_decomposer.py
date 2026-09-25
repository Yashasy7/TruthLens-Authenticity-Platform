"""
TruthLens AI/ML — Module 11: Claim Decomposition Tests
Verifies decomposition of compound assertions into atomic claims,
semantic triples (Subject, Action, Value), and provenance tracking.
"""

import pytest
from services.claim.engine import RuleBasedClaimEngine


@pytest.fixture
def claim_engine():
    return RuleBasedClaimEngine()


class TestClaimDecomposer:

    def test_single_atomic_assertion_decomposition(self, claim_engine):
        text = "NASA launched the Europa Clipper spacecraft toward Jupiter."
        res = claim_engine.analyze(text)

        assert res.claims_count == 1
        claim = res.claims[0]
        assert "NASA" in (claim.subject or "")
        assert "launched" in (claim.action or "")
        assert claim.value is not None
        assert "Europa Clipper" in claim.value or "Jupiter" in claim.value

    def test_compound_sentence_conjunction_decomposition(self, claim_engine):
        text = "Company X acquired Company Y in 2024 and employs 10,000 people."
        res = claim_engine.analyze(text)

        # Decomposed into 2 atomic assertions
        assert res.claims_count == 2
        claim1, claim2 = res.claims[0], res.claims[1]

        assert "Company X" in (claim1.subject or "")
        assert "acquired" in (claim1.action or "")
        assert "Company Y" in (claim1.value or "")

        assert "Company X" in (claim2.subject or "")
        assert "employs" in (claim2.action or "")
        assert "10,000 people" in (claim2.value or "")

    def test_sentence_index_and_character_offsets_preserved(self, claim_engine):
        text = "First claim was reported here. Second claim happened there."
        res = claim_engine.analyze(text)

        assert res.claims_count == 2
        c1, c2 = res.claims[0], res.claims[1]

        assert c1.sentence_index == 0
        assert c2.sentence_index == 1
        assert c1.start_char == 0
        assert c2.start_char > c1.end_char

    def test_claim_hash_uniqueness_and_determinism(self, claim_engine):
        text = "The Prime Minister announced a 15 billion euro relief package in Paris on Monday."
        res1 = claim_engine.analyze(text)
        res2 = claim_engine.analyze(text)

        h1 = res1.claims[0].claim_hash
        h2 = res2.claims[0].claim_hash

        assert len(h1) == 64
        assert h1 == h2

        # Hash must differ for different text
        res3 = claim_engine.analyze("The President signed an executive order on Tuesday.")
        h3 = res3.claims[0].claim_hash
        assert h1 != h3

    def test_dominant_entity_type_assignment(self, claim_engine):
        text = "The fund invested $500 million in clean energy."
        res = claim_engine.analyze(text)
        assert res.claims_count == 1
        assert res.claims[0].entity_type == "MONEY"
