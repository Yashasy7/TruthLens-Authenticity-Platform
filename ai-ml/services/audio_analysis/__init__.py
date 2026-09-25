"""
TruthLens AI/ML — Module 07: Audio Authenticity & Voice Forensics
Blueprint Section D, E, F, G (Audio Pipeline)
"""

from services.audio_analysis.service import (
    analyze_audio_bytes,
    analyze_audio_from_path,
)

__all__ = [
    "analyze_audio_bytes",
    "analyze_audio_from_path",
]
