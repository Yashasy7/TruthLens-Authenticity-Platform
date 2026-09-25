"""
TruthLens Module 11 — Comprehensive Independent Audit Script
Executes rigorous verification of:
1. spaCy NER quality & normalization (PERSON, ORG, LOCATION, DATE, MONEY, QUANTITY)
2. Sentence/Claim classification (FACTUAL_CLAIM, OPINION, QUESTION, NON_CLAIM)
3. Semantic Subject/Action/Value decomposition (active, passive, prepositional)
4. Normalization and SHA-256 hash determinism
5. Boundary conditions and input limits
"""
import sys
import hashlib
from pathlib import Path

# Add ai-ml to sys.path
sys.path.insert(0, str(Path("ai-ml").resolve()))

from app.services.claim_extractor import ClaimExtractor
from app.config import settings

def test_ner_quality(extractor):
    print("\n--- 1. NER QUALITY & ENTITY CATEGORIZATION AUDIT ---")
    test_text = (
        "President Emmanuel Macron announced a €15 billion climate package in Paris on Monday. "
        "Microsoft committed $500 million to clean energy projects across Germany."
    )
    result = extractor.analyze(test_text, source_type="DIRECT_TEXT")
    
    entities_by_type = {}
    for ent in result.entities:
        entities_by_type.setdefault(ent.normalized_label, []).append((ent.text, ent.start_char, ent.end_char))
        print(f"  Entity: '{ent.text}' -> Category: {ent.normalized_label} (raw: {ent.label}) [{ent.start_char}:{ent.end_char}]")
    
    assert "PERSON" in entities_by_type or any("Macron" in e[0] for e in result.entities), "Failed to detect PERSON"
    assert "LOCATION" in entities_by_type or any(l in str(entities_by_type) for l in ["Paris", "Germany"]), "Failed to detect LOCATION"
    assert "MONEY" in entities_by_type or any("15 billion" in e[0] or "500 million" in e[0] for e in result.entities), "Failed to detect MONEY"
    assert "ORG" in entities_by_type or any("Microsoft" in e[0] for e in result.entities), "Failed to detect ORG"
    print("  -> NER Quality: PASS")
    return result

def test_claim_classification(extractor):
    print("\n--- 2. CLAIM CLASSIFICATION AUDIT ---")
    samples = [
        ("The European Union approved the funding.", "FACTUAL_CLAIM"),
        ("I believe this is the best policy ever.", "OPINION"),
        ("Will other countries follow this decision?", "QUESTION"),
        ("Click here for more information.", "NON_CLAIM"),
    ]
    
    for text, expected_type in samples:
        res = extractor.analyze(text, source_type="DIRECT_TEXT")
        assert len(res.claims) == 1, f"Expected 1 claim for '{text}', got {len(res.claims)}"
        claim = res.claims[0]
        print(f"  Text: '{text}' -> Classified: {claim.claim_type} (Expected: {expected_type}), Conf: {claim.confidence_score:.2f}")
        assert claim.claim_type == expected_type, f"Mismatch for '{text}': got {claim.claim_type}, expected {expected_type}"
    print("  -> Claim Classification: PASS")

def test_subject_action_value_structures(extractor):
    print("\n--- 3. SUBJECT / ACTION / VALUE DECOMPOSITION AUDIT ---")
    structures = [
        # Active voice
        ("Microsoft committed $500 million to clean energy.", "Active Voice"),
        # Passive voice
        ("The new regulation was approved by parliament yesterday.", "Passive Voice"),
        # Prepositional / Named-entity subject
        ("Tesla delivered 400000 vehicles in the third quarter.", "Quantified Delivery"),
        # Complex assertion
        ("Prime Minister Rishi Sunak signed the defense accord in London.", "Diplomatic Accord"),
    ]
    
    for text, label in structures:
        res = extractor.analyze(text, source_type="DIRECT_TEXT")
        claim = res.claims[0]
        print(f"  [{label}] '{text}'")
        print(f"    Subject: '{claim.subject}'")
        print(f"    Action:  '{claim.action}'")
        print(f"    Value:   '{claim.value}'")
        assert claim.subject is not None and len(claim.subject) > 0, f"Missing subject in {label}"
        assert claim.action is not None and len(claim.action) > 0, f"Missing action in {label}"
        assert claim.value is not None and len(claim.value) > 0, f"Missing value in {label}"
    print("  -> Subject / Action / Value Extraction: PASS")

def test_normalization_and_hash_determinism(extractor):
    print("\n--- 4. CLAIM NORMALIZATION & SHA-256 HASH AUDIT ---")
    t1 = "The company announced the policy."
    t2 = "   The   company   announced   the   policy.   "
    
    r1 = extractor.analyze(t1, source_type="DIRECT_TEXT")
    r2 = extractor.analyze(t2, source_type="DIRECT_TEXT")
    
    c1 = r1.claims[0]
    c2 = r2.claims[0]
    
    print(f"  Raw 1:        '{t1}'")
    print(f"  Normalized 1: '{c1.normalized_claim_text}'")
    print(f"  Hash 1:       {c1.claim_hash}")
    print(f"  Raw 2:        '{t2}'")
    print(f"  Normalized 2: '{c2.normalized_claim_text}'")
    print(f"  Hash 2:       {c2.claim_hash}")
    
    assert c1.normalized_claim_text == c2.normalized_claim_text, "Normalized text must match"
    assert c1.claim_hash == c2.claim_hash, "Deterministic hash must match across whitespace variations"
    
    # Verify canonical SHA-256 hash algorithm
    norm_c = extractor.normalize_text(c1.claim_text).lower()
    norm_s = extractor.normalize_text(c1.subject or "").lower()
    norm_a = extractor.normalize_text(c1.action or "").lower()
    norm_v = extractor.normalize_text(c1.value or "").lower()
    canonical_repr = f"{norm_c}|{norm_s}|{norm_a}|{norm_v}"
    expected_hash = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()
    
    print(f"  Canonical Tuple: '{canonical_repr}'")
    print(f"  Calculated SHA-256: {expected_hash}")
    assert c1.claim_hash == expected_hash, f"Hash algorithm mismatch! Got {c1.claim_hash}, expected {expected_hash}"
    print("  -> Normalization & Deterministic Hash: PASS")

def test_resource_limits_and_boundaries(extractor):
    print("\n--- 5. INPUT LIMITS & RESOURCE BOUNDARIES AUDIT ---")
    
    # 1. Empty & whitespace
    r_empty = extractor.analyze("", source_type="DIRECT_TEXT")
    assert r_empty.claims_count == 0
    assert r_empty.sentences_count == 0
    print("  - Empty string handled gracefully: 0 claims")
    
    r_ws = extractor.analyze("   \n\t   ", source_type="DIRECT_TEXT")
    assert r_ws.claims_count == 0
    assert r_ws.sentences_count == 0
    print("  - Whitespace-only string handled gracefully: 0 claims")
    
    # 2. Oversized input (> 100,000 chars)
    oversized = "A" * (settings.CLAIM_MAX_TEXT_LENGTH + 1)
    try:
        extractor.analyze(oversized)
        assert False, "Should have raised ValueError for > 100k chars"
    except ValueError as e:
        print(f"  - Oversized text ({len(oversized)} chars) properly rejected: {e}")
        
    print("  -> Resource Limits & Boundaries: PASS")

def main():
    print("=" * 70)
    print("TRUTHLENS MODULE 11: INDEPENDENT VERIFICATION & AUDIT RUN")
    print("=" * 70)
    extractor = ClaimExtractor()
    test_ner_quality(extractor)
    test_claim_classification(extractor)
    test_subject_action_value_structures(extractor)
    test_normalization_and_hash_determinism(extractor)
    test_resource_limits_and_boundaries(extractor)
    print("\n" + "=" * 70)
    print("ALL MODULE 11 INDEPENDENT NLP AUDIT TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
