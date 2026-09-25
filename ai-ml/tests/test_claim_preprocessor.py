"""
TruthLens AI/ML — Module 11: Text & Claim Preprocessor Tests
Verifies Unicode normalization, whitespace collapsing, control character stripping,
sentence segmentation with character offsets, and deterministic claim hashing.
"""

import pytest
from services.claim.preprocessor import ClaimTextPreprocessor


class TestClaimPreprocessor:

    def test_normalize_text_unicode_nfkc(self):
        # Full-width characters and ligatures
        raw = "Ｔｈｅ  Ｕｎｉｔｅｄ  Ｎａｔｉｏｎｓ\u00a0passed\u2002a\u2003resolution."
        norm = ClaimTextPreprocessor.normalize_text(raw)
        assert norm == "The United Nations passed a resolution."

    def test_normalize_text_collapses_whitespace(self):
        raw = "  The    Prime   \n\n\t  Minister  announced   a    plan.   "
        norm = ClaimTextPreprocessor.normalize_text(raw)
        assert norm == "The Prime Minister announced a plan."

    def test_clean_control_characters(self):
        # String containing null byte and control codes
        raw = "NASA\x00 launched\x07 the\x1b spacecraft\x0c."
        clean = ClaimTextPreprocessor.clean_control_characters(raw)
        assert "\x00" not in clean
        assert "\x07" not in clean
        assert "\x1b" not in clean
        assert "NASA launched the spacecraft" in clean

    def test_punctuation_preservation(self):
        raw = 'Company X (an EU firm) reported: "Revenue grew by 15.5% — exceeding expectations!"'
        norm = ClaimTextPreprocessor.normalize_text(raw)
        assert "(" in norm and ")" in norm
        assert '"' in norm
        assert "%" in norm
        assert "—" in norm or "-" in norm
        assert "15.5%" in norm

    def test_empty_and_whitespace_input(self):
        assert ClaimTextPreprocessor.normalize_text("") == ""
        assert ClaimTextPreprocessor.normalize_text("   \n\t  ") == ""
        assert ClaimTextPreprocessor.clean_control_characters("") == ""
        assert ClaimTextPreprocessor.split_sentences("") == []
        assert ClaimTextPreprocessor.split_sentences("   \t\n  ") == []

    def test_split_sentences_standard_punctuation(self):
        text = "First sentence here. Second sentence follows! Is this the third sentence?"
        sentences = ClaimTextPreprocessor.split_sentences(text)
        assert len(sentences) == 3

        s1, start1, end1 = sentences[0]
        assert s1 == "First sentence here."
        assert text[start1:end1] == s1

        s2, start2, end2 = sentences[1]
        assert s2 == "Second sentence follows!"
        assert text[start2:end2] == s2

        s3, start3, end3 = sentences[2]
        assert s3 == "Is this the third sentence?"
        assert text[start3:end3] == s3

    def test_split_sentences_preserves_abbreviations(self):
        text = "Dr. Jane Smith visited Washington, D.C. yesterday. She met with Prof. Jones."
        sentences = ClaimTextPreprocessor.split_sentences(text)
        # Should not split at Dr. or Prof.
        assert len(sentences) == 2
        assert sentences[0][0].startswith("Dr. Jane Smith")
        assert sentences[1][0].startswith("She met with Prof. Jones")

    def test_split_sentences_preserves_decimals(self):
        text = "Inflation rose by 3.5% this quarter. The previous rate was 2.8%."
        sentences = ClaimTextPreprocessor.split_sentences(text)
        assert len(sentences) == 2
        assert "3.5%" in sentences[0][0]
        assert "2.8%" in sentences[1][0]

    def test_compute_claim_hash_deterministic(self):
        hash1 = ClaimTextPreprocessor.compute_claim_hash(
            "The Federal Reserve cut rates by 25 bps.",
            subject="The Federal Reserve",
            action="cut",
            value="rates by 25 bps",
        )
        hash2 = ClaimTextPreprocessor.compute_claim_hash(
            "The Federal Reserve cut rates by 25 bps.",
            subject="The Federal Reserve",
            action="cut",
            value="rates by 25 bps",
        )
        assert len(hash1) == 64
        assert hash1 == hash2

    def test_compute_claim_hash_case_and_whitespace_invariant(self):
        hash1 = ClaimTextPreprocessor.compute_claim_hash(
            "  The   Federal   Reserve   cut rates. ",
            subject="Federal Reserve",
            action="cut",
            value="rates",
        )
        hash2 = ClaimTextPreprocessor.compute_claim_hash(
            "the federal reserve cut rates.",
            subject="federal reserve",
            action="cut",
            value="rates",
        )
        assert hash1 == hash2

    def test_compute_claim_hash_distinct_for_different_claims(self):
        hash1 = ClaimTextPreprocessor.compute_claim_hash("Company A grew revenue.")
        hash2 = ClaimTextPreprocessor.compute_claim_hash("Company B lost revenue.")
        assert hash1 != hash2
