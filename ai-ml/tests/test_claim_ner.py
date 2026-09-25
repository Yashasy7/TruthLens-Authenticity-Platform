"""
TruthLens AI/ML — Module 11: Named Entity Recognition Tests
Verifies entity recognition across PERSON, ORG, LOCATION, DATE, MONEY, QUANTITY, EVENT,
character offset precision, and label standardization.
"""

import pytest
from services.claim.engine import RuleBasedClaimEngine


@pytest.fixture
def claim_engine():
    return RuleBasedClaimEngine()


class TestClaimNER:

    def test_ner_persons_and_organizations(self, claim_engine):
        text = "Satya Nadella met with Sundar Pichai at Microsoft headquarters."
        entities = claim_engine.extract_entities(text)

        labels = {e.normalized_label for e in entities}
        texts = {e.text for e in entities}

        assert "PERSON" in labels
        assert "ORG" in labels
        assert "Microsoft" in texts
        assert any("Satya Nadella" in t for t in texts)

    def test_ner_location_and_date(self, claim_engine):
        text = "The summit was held in Paris on Monday, January 15."
        entities = claim_engine.extract_entities(text)

        labels = {e.normalized_label for e in entities}
        texts = {e.text for e in entities}

        assert "LOCATION" in labels
        assert "DATE" in labels
        assert "Paris" in texts
        assert any("Monday" in t or "January 15" in t for t in texts)

    def test_ner_money_and_quantity(self, claim_engine):
        text = "The fund invested $10 billion and cut 5,000 positions, representing 25% of staff."
        entities = claim_engine.extract_entities(text)

        labels = {e.normalized_label for e in entities}
        texts = {e.text for e in entities}

        assert "MONEY" in labels
        assert "QUANTITY" in labels
        assert any("$10 billion" in t for t in texts)
        assert any("25%" in t or "5,000" in t for t in texts)

    def test_ner_event_recognition(self, claim_engine):
        text = "The European Union approved the Artificial Intelligence Act in Brussels."
        entities = claim_engine.extract_entities(text)

        labels = {e.normalized_label for e in entities}
        assert "EVENT" in labels
        assert "ORG" in labels
        assert "LOCATION" in labels
        assert any("Artificial Intelligence Act" in e.text for e in entities)

    def test_ner_character_offsets_exact_substring(self, claim_engine):
        text = (
            "The Federal Reserve cut interest rates by 25 basis points in Washington on Monday. "
            "NASA launched a $2 billion mission with 10,000 people attending the Global Summit."
        )
        entities = claim_engine.extract_entities(text)
        assert len(entities) >= 5

        for ent in entities:
            # Crucial requirement: character offsets must point to exact substring in text
            extracted_sub = text[ent.start_char:ent.end_char]
            assert extracted_sub == ent.text, f"Offset mismatch: expected '{ent.text}' but found '{extracted_sub}'"

    def test_ner_no_overlapping_spans(self, claim_engine):
        text = "The Prime Minister Emmanuel Macron addressed the European Union Parliament in Brussels."
        entities = claim_engine.extract_entities(text)

        # Ensure spans are strictly non-overlapping
        for i in range(len(entities) - 1):
            assert entities[i].end_char <= entities[i + 1].start_char, (
                f"Overlap detected: '{entities[i].text}' ({entities[i].start_char}-{entities[i].end_char}) "
                f"and '{entities[i + 1].text}' ({entities[i + 1].start_char}-{entities[i + 1].end_char})"
            )

    def test_ner_empty_text(self, claim_engine):
        assert claim_engine.extract_entities("") == []
        assert claim_engine.extract_entities("   ") == []
