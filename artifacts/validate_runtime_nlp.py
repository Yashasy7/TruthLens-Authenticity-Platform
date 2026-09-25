"""
TruthLens Module 11 — Real Runtime Validation Script
Runs real NLP claim decomposition and Named Entity Recognition using spaCy 'en_core_web_sm'.
"""
import sys
import json
from pathlib import Path

# Add ai-ml to sys.path
sys.path.insert(0, str(Path("ai-ml").resolve()))

from app.services.claim_extractor import ClaimExtractor

def main():
    print("=" * 70)
    print("TRUTHLENS MODULE 11: RUNTIME NLP INFERENCE VALIDATION")
    print("=" * 70)

    extractor = ClaimExtractor()
    print(f"Loaded NLP Engine: {extractor.model_name}")
    print(f"spaCy Pipeline Components: {extractor._nlp.pipe_names}")

    sample_paragraph = (
        "On Monday, President Emmanuel Macron announced a 15 billion euro climate package in Paris. "
        "The European Union approved the funding following three weeks of negotiations. "
        "I believe this is the most visionary environmental policy in European history! "
        "Will other member states follow France's lead before the December summit? "
        "Microsoft committed $500 million to clean energy projects across Germany."
    )

    print("\nInput Text:")
    print("-" * 50)
    print(sample_paragraph)
    print("-" * 50)

    result = extractor.analyze(sample_paragraph, source_type="TRANSCRIPT")

    print(f"\nExecution Summary:")
    print(f"  Total Sentences Processed: {result.sentences_count}")
    print(f"  Total Claims Extracted:   {result.claims_count}")
    print(f"  Total Named Entities:     {len(result.entities)}")
    print(f"  Processing Latency:       {result.evidence.duration_seconds:.4f} seconds")

    print("\nExtracted Entities:")
    for ent in result.entities:
        print(f"  - '{ent.text}' [{ent.normalized_label} / raw: {ent.label}] ({ent.start_char}:{ent.end_char})")

    print("\nStructured Claims:")
    for idx, c in enumerate(result.claims, 1):
        print(f"\n[Claim #{idx}]")
        print(f"  Text:         '{c.claim_text}'")
        print(f"  Type:         {c.claim_type}")
        print(f"  Subject:      '{c.subject}'")
        print(f"  Action:       '{c.action}'")
        print(f"  Value:        '{c.value}'")
        print(f"  Dominant Ent: {c.entity_type}")
        print(f"  Confidence:   {c.confidence_score:.2f}")
        print(f"  Normalized:   '{c.normalized_claim_text}'")
        print(f"  SHA-256 Hash: {c.claim_hash}")

    output_path = Path("artifacts/runtime_nlp_validation_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2)
    print(f"\nSaved structured validation payload to: {output_path}")

if __name__ == "__main__":
    main()
