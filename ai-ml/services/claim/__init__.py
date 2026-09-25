"""
TruthLens AI/ML — Module 11: Text & Claim Analysis Service Package
"""

from .preprocessor import ClaimTextPreprocessor
from .engine import (
    BaseClaimEngine,
    RuleBasedClaimEngine,
    SpaCyClaimEngine,
    get_claim_engine,
)
from .service import ClaimAnalysisService, get_claim_service

__all__ = [
    "ClaimTextPreprocessor",
    "BaseClaimEngine",
    "RuleBasedClaimEngine",
    "SpaCyClaimEngine",
    "get_claim_engine",
    "ClaimAnalysisService",
    "get_claim_service",
]
