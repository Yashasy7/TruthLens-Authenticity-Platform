"""
TruthLens AI/ML — Module 10: Speech-to-Text & Transcript Extraction Package
"""

from services.transcript.service import (
    analyze_speech_to_text_bytes,
    analyze_speech_to_text_from_path,
)

__all__ = [
    "analyze_speech_to_text_bytes",
    "analyze_speech_to_text_from_path",
]
