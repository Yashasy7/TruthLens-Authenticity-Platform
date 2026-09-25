"""
TruthLens AI/ML — Module 11: Claim Detection Tests
Verifies sentence classification into FACTUAL_CLAIM, OPINION, QUESTION, and NON_CLAIM,
assertiveness detection, and confidence scoring.
"""

import pytest
from services.claim.engine import RuleBasedClaimEngine


@pytest.fixture
def claim_engine():
    return RuleBasedClaimEngine()


class TestClaimDetector:

    def test_classify_factual_declarative_claim(self, claim_engine):
        text = "The Ministry of Health announced 5,000 new medical positions across 12 regions."
        res = claim_engine.analyze(text)

        assert res.claims_count == 1
        claim = res.claims[0]
        assert claim.claim_type == "FACTUAL_CLAIM"
        assert claim.confidence_score >= 0.70
        assert claim.subject is not None
        assert claim.action is not None

    def test_classify_opinion_statement(self, claim_engine):
        text = "In my opinion, this is the worst economic policy in modern history."
        res = claim_engine.analyze(text)

        assert res.claims_count == 1
        claim = res.claims[0]
        assert claim.claim_type == "OPINION"
        assert claim.confidence_score >= 0.70

    def test_classify_question_with_mark(self, claim_engine):
        text = "Why did the committee reject the proposed amendments yesterday?"
        res = claim_engine.analyze(text)

        assert res.claims_count == 1
        claim = res.claims[0]
        assert claim.claim_type == "QUESTION"
        assert claim.confidence_score >= 0.85

    def test_classify_inverted_question_without_mark(self, claim_engine):
        text = "Can you believe what happened to the interest rate"
        res = claim_engine.analyze(text)

        assert res.claims_count == 1
        claim = res.claims[0]
        assert claim.claim_type == "QUESTION"

    def test_classify_imperative_command_as_non_claim(self, claim_engine):
        commands = [
            "Click here now.",
            "Subscribe to the channel.",
            "Look at this screenshot.",
            "Watch this video.",
            "Listen carefully.",
        ]
        for cmd in commands:
            res = claim_engine.analyze(cmd)
            assert res.claims_count == 1
            assert res.claims[0].claim_type == "NON_CLAIM", f"Expected NON_CLAIM for '{cmd}'"

    def test_classify_short_fragments_as_non_claim(self, claim_engine):
        fragments = ["Yes.", "Hello there.", "Okay thanks.", "Good morning."]
        for frag in fragments:
            res = claim_engine.analyze(frag)
            assert res.claims[0].claim_type == "NON_CLAIM"

    def test_multi_sentence_mixed_classification(self, claim_engine):
        text = (
            "The Federal Reserve cut rates by 25 basis points on Wednesday. "
            "In my view, this was a fantastic decision. "
            "Will the market rally tomorrow?"
        )
        res = claim_engine.analyze(text)
        assert res.sentences_count == 3
        assert res.claims_count == 3

        types = [c.claim_type for c in res.claims]
        assert types == ["FACTUAL_CLAIM", "OPINION", "QUESTION"]

    def test_extraction_confidence_is_bounded(self, claim_engine):
        text = "The company reported $15 billion in revenue."
        res = claim_engine.analyze(text)
        for claim in res.claims:
            assert 0.0 <= claim.confidence_score <= 1.0
