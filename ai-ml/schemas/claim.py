"""
TruthLens AI/ML — Module 11: Text & Claim Analysis Schemas
Blueprint Section D & Module 11: Core NLP, Named Entity Recognition, Sentence Classification,
and Semantic Claim Decomposition into structured claim objects (Entity, Action, Value).
Matches Spring Boot FastApiClaimRequest, FastApiClaimResponse, FastApiStructuredClaim,
ClaimEntityDto, ClaimEvidenceDto, ClaimType, ClaimEntityType, and ClaimSourceType.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ClaimType(str, Enum):
    """Categorization of analyzed text segments according to verifiable assertiveness."""
    FACTUAL_CLAIM = "FACTUAL_CLAIM"
    OPINION = "OPINION"
    QUESTION = "QUESTION"
    NON_CLAIM = "NON_CLAIM"
    UNCERTAIN = "UNCERTAIN"


class ClaimEntityType(str, Enum):
    """Standardized named entity classification categories supported in TruthLens."""
    PERSON = "PERSON"
    ORG = "ORG"
    LOCATION = "LOCATION"
    DATE = "DATE"
    MONEY = "MONEY"
    QUANTITY = "QUANTITY"
    EVENT = "EVENT"
    GENERAL = "GENERAL"


class ClaimSourceType(str, Enum):
    """Origin modality of analyzed text for claim decomposition."""
    OCR = "OCR"
    TRANSCRIPT = "TRANSCRIPT"
    COMBINED = "COMBINED"
    DIRECT_TEXT = "DIRECT_TEXT"


class ClaimEntityDto(BaseModel):
    """
    Extracted named entity span with character offsets in normalized text.
    Directly aligns with Spring Boot ClaimEntityDto.java.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    text: str = Field(..., description="Entity surface substring")
    label: str = Field(..., description="Raw NLP label assigned by NER model")
    normalized_label: str = Field(
        default="GENERAL",
        description="Standardized TruthLens entity label (PERSON, ORG, LOCATION, DATE, MONEY, QUANTITY, EVENT, GENERAL)"
    )
    start_char: int = Field(..., ge=0, description="0-indexed start character offset in normalized text")
    end_char: int = Field(..., ge=0, description="0-indexed end character offset in normalized text")


# Alias for backward and internal naming compatibility
EntitySpan = ClaimEntityDto


class FastApiStructuredClaim(BaseModel):
    """
    Structured claim object with semantic decomposition, provenance, and hash.
    Directly aligns with Spring Boot FastApiStructuredClaim.java.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    claim_text: str = Field(..., description="Surface sentence or decomposed atomic claim string")
    normalized_claim_text: str = Field(..., description="Canonical normalized claim representation")
    claim_type: str = Field(default="FACTUAL_CLAIM", description="Claim classification category")
    subject: Optional[str] = Field(default=None, description="Extracted grammatical/semantic subject")
    action: Optional[str] = Field(default=None, description="Extracted predicate verb or event action")
    value: Optional[str] = Field(default=None, description="Extracted object, attribute, or complement value")
    entity_type: str = Field(default="GENERAL", description="Dominant entity category associated with the claim")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="NLP extraction and classification confidence")
    claim_hash: str = Field(..., description="Deterministic SHA-256 hash of canonical claim tuple")
    sentence_index: int = Field(default=0, ge=0, description="Sequential sentence index in parent document")
    start_char: int = Field(default=0, ge=0, description="Start character offset in parent source text")
    end_char: int = Field(default=0, ge=0, description="End character offset in parent source text")
    entities: List[ClaimEntityDto] = Field(default_factory=list, description="Named entities enclosed within this claim")

    # Optional cross-modal provenance metadata (retained for M09/M10 explainability)
    source_type: Optional[str] = Field(default=None, description="Origin modality (OCR, TRANSCRIPT, DIRECT_TEXT)")
    start_time: Optional[float] = Field(default=None, description="Audio/Video start timestamp in seconds if from transcript")
    end_time: Optional[float] = Field(default=None, description="Audio/Video end timestamp in seconds if from transcript")
    bounding_box: Optional[Dict[str, Any]] = Field(default=None, description="Spatial coordinates if from visual OCR")


# Alias for backward and internal naming compatibility
StructuredClaim = FastApiStructuredClaim


class ClaimEvidenceDto(BaseModel):
    """
    Forensic execution metadata, model attribution, and diagnostic counts.
    Directly aligns with Spring Boot ClaimEvidenceDto.java.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())

    model_name: str = Field("spaCy-en_core_web_sm", description="NLP engine or checkpoint identifier")
    sentences_count: int = Field(0, ge=0, description="Total sentences identified and analyzed")
    claims_count: int = Field(0, ge=0, description="Total structured claims extracted")
    entities_count: int = Field(0, ge=0, description="Total named entities recognized")
    duration_seconds: float = Field(0.0, ge=0.0, description="Execution duration in seconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic and processing telemetry")


# Alias for backward and internal naming compatibility
ClaimAnalysisEvidence = ClaimEvidenceDto


class FastApiClaimResponse(BaseModel):
    """
    Consolidated response returned by POST /api/v1/analyze/claims.
    Directly aligns with Spring Boot FastApiClaimResponse.java.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    text: str = Field(..., description="Normalized analyzed input text")
    source_type: str = Field(default="DIRECT_TEXT", description="Origin source modality")
    sentences_count: int = Field(0, ge=0, description="Total segmented sentences")
    claims_count: int = Field(0, ge=0, description="Total extracted claims")
    claims: List[FastApiStructuredClaim] = Field(default_factory=list, description="List of structured claims")
    entities: List[ClaimEntityDto] = Field(default_factory=list, description="List of all extracted named entities")
    evidence: Optional[ClaimEvidenceDto] = Field(default=None, description="Extraction forensic metadata")
    status: str = Field(default="COMPLETED", description="Analysis execution status: COMPLETED or FAILED")
    error_message: Optional[str] = Field(default=None, description="Error message if analysis failed")


# Aliases for backward and internal naming compatibility
ClaimAnalysisResult = FastApiClaimResponse
BackendClaimResponse = FastApiClaimResponse


class FastApiClaimRequest(BaseModel):
    """
    Request payload sent to POST /api/v1/analyze/claims.
    Directly aligns with Spring Boot FastApiClaimRequest.java.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    text: Optional[str] = Field(default="", description="Input text from OCR, speech transcript, or ad-hoc query")
    source_type: str = Field(default="DIRECT_TEXT", description="Origin modality: DIRECT_TEXT, OCR, TRANSCRIPT, COMBINED")
    language: Optional[str] = Field(default="en", description="Source language hint (defaults to 'en')")

    # Optional multi-modal ingestion payloads
    ocr_regions: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional list of OCR text regions with bounding boxes from Module 09"
    )
    transcript_segments: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional list of transcript phrase segments with timestamps from Module 10"
    )


# Alias
ClaimAnalysisRequest = FastApiClaimRequest
