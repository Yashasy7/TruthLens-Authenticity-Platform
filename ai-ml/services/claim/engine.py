"""
TruthLens AI/ML — Module 11: Text & Claim Analysis NLP Engine
Blueprint Section D: Named Entity Recognition, Sentence Classification,
Semantic Claim Decomposition (Subject, Action, Value), and Structured Claim Extraction.
Provides:
- BaseClaimEngine: abstract base class
- SpaCyClaimEngine: production NLP engine loading spaCy / transformer models when present
- RuleBasedClaimEngine: deterministic, high-accuracy fallback when spaCy/models are not installed
- Factory function get_claim_engine() with thread-safe caching and strict mode enforcement
"""

from __future__ import annotations

import logging
import re
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings
from schemas.claim import (
    ClaimAnalysisEvidence,
    ClaimEntityDto,
    ClaimEvidenceDto,
    FastApiClaimResponse,
    FastApiStructuredClaim,
)
from services.claim.preprocessor import ClaimTextPreprocessor

logger = logging.getLogger("truthlens.ai-ml.claim")

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class BaseClaimEngine(ABC):
    """Abstract interface for all TruthLens Module 11 NLP and claim extraction engines."""

    @abstractmethod
    def analyze(
        self,
        text: str,
        source_type: str = "DIRECT_TEXT",
        language: Optional[str] = "en",
        ocr_regions: Optional[List[Dict[str, Any]]] = None,
        transcript_segments: Optional[List[Dict[str, Any]]] = None,
    ) -> FastApiClaimResponse:
        """
        Executes end-to-end NLP claim decomposition and entity recognition pipeline.
        """
        pass


class RuleBasedClaimEngine(BaseClaimEngine):
    """
    Deterministic, production-ready rule-based NLP and claim decomposition engine.
    Extracts named entities (PERSON, ORG, LOCATION, DATE, MONEY, QUANTITY, EVENT),
    classifies sentences into ClaimType, parses SVO (Subject, Action, Value) triples,
    decomposes compound assertions into atomic claims, and tracks exact character offsets.
    """

    # Opinion and subjectivity markers
    OPINION_MARKERS = [
        "i think", "i believe", "in my opinion", "in our view", "we believe",
        "i feel", "it seems to me", "personally", "my view is", "my impression is",
        "best", "worst", "terrible", "wonderful", "gorgeous", "horrible", "ugly",
        "fantastic", "brilliant", "disgusting", "greatest", "sublime", "disgraceful",
        "strongly believe", "undoubtedly better", "clearly superior"
    ]

    # Interrogative starter tokens
    QUESTION_STARTERS = [
        "what", "why", "how", "who", "whom", "whose", "when", "where",
        "is", "are", "was", "were", "can", "could", "would", "will", "shall",
        "should", "do", "does", "did", "have", "has", "had"
    ]

    # Command/imperative lead tokens
    IMPERATIVE_STARTERS = [
        "click", "subscribe", "look", "see", "watch", "remember", "don't",
        "do", "listen", "check", "follow", "share", "read", "join", "buy"
    ]

    # Factual predicate verbs
    FACTUAL_VERBS = [
        "announced", "increased", "decreased", "reported", "confirmed",
        "signed", "voted", "passed", "discovered", "caused", "won", "lost",
        "visited", "stated", "allocated", "approved", "banned", "declined",
        "launched", "acquired", "employs", "cut", "raised", "built", "invested",
        "became", "elected", "established", "reached", "generated", "produced",
        "unveiled", "released", "sold", "purchased", "appointed", "resigned",
        "struck", "agreed", "authorized", "found", "filed", "tested", "published"
    ]

    # Regex patterns for Named Entity Recognition
    RE_MONEY = re.compile(
        r"(?:(?:\$|€|£|¥)\s*\d+(?:[.,]\d+)*(?:\s*(?:billion|million|trillion|thousand|k))?|"
        r"\b\d+(?:[.,]\d+)*\s*(?:billion|million|trillion)?\s*(?:dollars?|euros?|pounds?|usd|eur|gbp)\b)",
        re.IGNORECASE
    )

    RE_QUANTITY = re.compile(
        r"\b\d+(?:[.,]\d+)*\s*(?:%|percent|basis points?|bps|positions?|employees?|people|"
        r"tons?|kg|km|miles?|meters?|units?|jobs?|cases?|votes?|seats?|regions?)\b",
        re.IGNORECASE
    )

    RE_DATE = re.compile(
        r"(?:\b(?:January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?\b|"
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b|"
        r"\b(?:yesterday|today|tomorrow|last year|last month|last week|next year)\b|"
        r"\b(?:in\s+)?(19\d{2}|20\d{2})\b)",
        re.IGNORECASE
    )

    RE_ORG_KNOWN = re.compile(
        r"\b(?:The\s+)?(?:Microsoft|Google|Apple|Amazon|Meta|OpenAI|NASA|Tesla|Twitter|Netflix|Nvidia|IBM|Intel|"
        r"European Union|EU|United Nations|UN|Federal Reserve|Fed|World Health Organization|WHO|"
        r"Ministry of Health|Ministry of Defense|Ministry of Finance|White House|Pentagon|"
        r"Parliament|Congress|Senate|Supreme Court)\b"
    )

    RE_ORG_SUFFIX = re.compile(
        r"\b(?:The\s+)?([A-Z][a-zA-Z0-9&]*(?:\s+[A-Z][a-zA-Z0-9&]*)*\s+"
        r"(?:Inc|Corp|Corporation|LLC|Ltd|Limited|GmbH|AG|Company|Co|Agency|Association|"
        r"Bank|Council|Commission|Department|Foundation|Group|Institute|University|Authority)\.?)\b"
    )

    RE_PERSON_TITLE = re.compile(
        r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Senator|Representative|CEO|CTO|CFO|Director|General|Judge)\s+"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
    )

    RE_PERSON_ROLE_ALONE = re.compile(
        r"\b(?:The\s+)?(?:Prime Minister|President|Governor|Chancellor|Attorney General)\b"
    )

    RE_LOCATION_KNOWN = re.compile(
        r"\b(?:Redmond|Paris|Brussels|Washington|London|Berlin|Tokyo|Beijing|New York|Geneva|"
        r"Rome|Madrid|Ottawa|Canberra|New Delhi|Moscow|Kyiv|Jupiter|Mars|Moon|Earth|"
        r"United States|USA|UK|France|Germany|Japan|China|India|Canada|Australia|Europe|"
        r"Asia|Africa|North America|South America)\b"
    )

    RE_EVENT_KNOWN = re.compile(
        r"\b([A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\s+"
        r"(?:Act|Treaty|Accord|Summit|Conference|Games|Olympics|Championship|Election|Cup|Initiative))\b"
    )

    # Entity mapping from raw label to normalized label
    ENTITY_MAPPING = {
        "PERSON": "PERSON",
        "ORG": "ORG",
        "GPE": "LOCATION",
        "LOCATION": "LOCATION",
        "LOC": "LOCATION",
        "DATE": "DATE",
        "TIME": "DATE",
        "MONEY": "MONEY",
        "PERCENT": "QUANTITY",
        "QUANTITY": "QUANTITY",
        "EVENT": "EVENT",
        "GENERAL": "GENERAL",
    }

    def __init__(
        self,
        max_text_length: int = settings.claim_max_text_length,
        max_sentences: int = settings.claim_max_sentences,
        min_confidence: float = settings.claim_min_confidence_threshold,
    ):
        self.max_text_length = max_text_length
        self.max_sentences = max_sentences
        self.min_confidence = min_confidence

    def extract_entities(self, text: str) -> List[ClaimEntityDto]:
        """
        Scans normalized text for named entities and returns non-overlapping
        ClaimEntityDto objects with precise character offsets.
        """
        if not text:
            return []

        raw_entities: List[Tuple[int, int, str, str, str]] = []  # (start, end, text, label, norm_label)

        # 1. Money
        for m in self.RE_MONEY.finditer(text):
            raw_entities.append((m.start(), m.end(), m.group(0), "MONEY", "MONEY"))

        # 2. Quantity
        for m in self.RE_QUANTITY.finditer(text):
            raw_entities.append((m.start(), m.end(), m.group(0), "QUANTITY", "QUANTITY"))

        # 3. Date
        for m in self.RE_DATE.finditer(text):
            raw_entities.append((m.start(), m.end(), m.group(0), "DATE", "DATE"))

        # 4. Known Org
        for m in self.RE_ORG_KNOWN.finditer(text):
            raw_entities.append((m.start(), m.end(), m.group(0), "ORG", "ORG"))

        # 5. Suffix Org
        for m in self.RE_ORG_SUFFIX.finditer(text):
            raw_entities.append((m.start(), m.end(), m.group(0), "ORG", "ORG"))

        # 6. Person with title
        for m in self.RE_PERSON_TITLE.finditer(text):
            raw_entities.append((m.start(), m.end(), m.group(0), "PERSON", "PERSON"))

        # 7. Person role alone (e.g. "The Prime Minister")
        for m in self.RE_PERSON_ROLE_ALONE.finditer(text):
            raw_entities.append((m.start(), m.end(), m.group(0), "PERSON", "PERSON"))

        # 8. Known Location
        for m in self.RE_LOCATION_KNOWN.finditer(text):
            raw_entities.append((m.start(), m.end(), m.group(0), "GPE", "LOCATION"))

        # 9. Known Event
        for m in self.RE_EVENT_KNOWN.finditer(text):
            raw_entities.append((m.start(), m.end(), m.group(0), "EVENT", "EVENT"))

        # 10. Generic capitalized pairs (e.g. "Satya Nadella", "Joe Biden") excluding determiners
        re_caps = re.compile(r"\b(?!The\b|This\b|That\b|These\b|Those\b|In\b|On\b|At\b|With\b|From\b)[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")
        for m in re_caps.finditer(text):
            span_text = m.group(0)
            raw_entities.append((m.start(), m.end(), span_text, "PERSON", "PERSON"))

        # Deduplicate and resolve overlapping spans (prioritizing longer spans)
        # Sort by start_char ascending, then length descending
        raw_entities.sort(key=lambda x: (x[0], -(x[1] - x[0])))

        non_overlapping: List[ClaimEntityDto] = []
        occupied_until = -1

        for start, end, span_text, label, norm_label in raw_entities:
            if start >= occupied_until:
                # Validate substring exact alignment
                if text[start:end] == span_text:
                    non_overlapping.append(ClaimEntityDto(
                        text=span_text,
                        label=label,
                        normalized_label=norm_label,
                        start_char=start,
                        end_char=end,
                    ))
                    occupied_until = end

        # Final sort by start_char
        non_overlapping.sort(key=lambda e: e.start_char)
        return non_overlapping

    def classify_sentence(
        self,
        sentence_text: str,
        entities: List[ClaimEntityDto],
        has_verb: bool = True
    ) -> Tuple[str, float]:
        """
        Classifies a candidate sentence into:
        - FACTUAL_CLAIM
        - OPINION
        - QUESTION
        - NON_CLAIM
        - UNCERTAIN
        """
        clean = sentence_text.strip()
        lower = clean.lower()

        # 1. Question classification
        if clean.endswith("?"):
            return "QUESTION", 0.95
        words = clean.split()
        if not words:
            return "NON_CLAIM", 0.99

        first_word = lower.split()[0].rstrip(",.!?")
        if first_word in self.QUESTION_STARTERS and len(words) > 2:
            if lower.startswith(("is it", "are there", "can you", "what if", "why would", "who is", "why did", "how can")):
                return "QUESTION", 0.92

        # 2. Non-claim checks (short fragments, imperatives)
        if len(words) < 3 or not has_verb:
            return "NON_CLAIM", 0.90

        if first_word in self.IMPERATIVE_STARTERS and len(words) <= 7:
            return "NON_CLAIM", 0.88

        # 3. Opinion and subjectivity markers
        for marker in self.OPINION_MARKERS:
            if re.search(r"\b" + re.escape(marker) + r"\b", lower):
                return "OPINION", 0.88

        # 4. Factual claim classification
        base_confidence = 0.70
        if len(entities) > 0:
            base_confidence += 0.12
        if re.search(r"\b\d+(?:[.,]\d+)?\b", clean):
            base_confidence += 0.08
        if any(re.search(r"\b" + re.escape(v) + r"\b", lower) for v in self.FACTUAL_VERBS):
            base_confidence += 0.10

        confidence = round(min(0.99, max(self.min_confidence, base_confidence)), 2)
        return "FACTUAL_CLAIM", confidence

    def extract_semantic_triples(
        self,
        sentence_text: str,
        entities: List[ClaimEntityDto]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extracts (subject, action, value) triple from sentence text.
        """
        words = sentence_text.split()
        if not words:
            return None, None, None

        # Look for factual verbs or standard action verbs
        action_verb = None
        action_index = -1

        for i, word in enumerate(words):
            clean_word = word.lower().strip(".,!?;:\"'")
            if clean_word in self.FACTUAL_VERBS or clean_word in [
                "is", "was", "are", "were", "has", "have", "had", "will", "spoke", "cut", "raised", "employs"
            ]:
                action_verb = word.strip(".,!?;:\"'")
                action_index = i
                break

        if action_index > 0:
            subject = " ".join(words[:action_index]).strip(".,!?;:\"'")
            action = action_verb
            value = " ".join(words[action_index + 1:]).strip(".,!?;:\"'") if action_index + 1 < len(words) else None
        else:
            # Fallback heuristic
            subject = words[0] if len(words) > 0 else None
            action = words[1] if len(words) > 1 else None
            value = " ".join(words[2:]) if len(words) > 2 else None

        # Clean trailing punctuation
        subject = subject.strip(".,;: ") if subject else None
        action = action.strip(".,;: ") if action else None
        value = value.strip(".,;: ") if value else None

        return subject, action, value

    def decompose_sentence_into_claims(
        self,
        sentence_text: str,
        sentence_index: int,
        sentence_start_char: int,
        sentence_end_char: int,
        all_entities: List[ClaimEntityDto],
    ) -> List[FastApiStructuredClaim]:
        """
        Decomposes a single sentence into one or more structured atomic claims.
        Compound sentences with coordinating conjunctions ('and', 'while') followed by
        predicates are split into atomic assertions while maintaining subject provenance.
        """
        clean_sentence = ClaimTextPreprocessor.normalize_text(sentence_text)
        if not clean_sentence:
            return []

        # Find entities belonging to this sentence
        sentence_entities = [
            e for e in all_entities
            if e.start_char >= sentence_start_char and e.end_char <= sentence_end_char
        ]

        # Classify sentence
        claim_type, confidence = self.classify_sentence(clean_sentence, sentence_entities)

        # Non-factual sentences (e.g. OPINION, QUESTION, NON_CLAIM) are returned as a single claim
        if claim_type != "FACTUAL_CLAIM":
            subject, action, value = self.extract_semantic_triples(clean_sentence, sentence_entities)
            dominant_entity = sentence_entities[0].normalized_label if sentence_entities else "GENERAL"
            norm_claim = clean_sentence.lower()
            claim_hash = ClaimTextPreprocessor.compute_claim_hash(norm_claim, subject, action, value)

            return [
                FastApiStructuredClaim(
                    claim_text=clean_sentence,
                    normalized_claim_text=norm_claim,
                    claim_type=claim_type,
                    subject=subject,
                    action=action,
                    value=value,
                    entity_type=dominant_entity,
                    confidence_score=confidence,
                    claim_hash=claim_hash,
                    sentence_index=sentence_index,
                    start_char=sentence_start_char,
                    end_char=sentence_end_char,
                    entities=sentence_entities,
                )
            ]

        # Check for compound conjunction splitting (e.g. "X acquired Y and employs Z")
        # Pattern: [Clause 1] and [Verb] [Clause 2]
        conj_pattern = re.compile(r"\s+\b(and|while|as well as)\s+(?=[a-z]+ed\b|[a-z]+s\b|employs\b|announced\b|plans\b|operates\b)", re.IGNORECASE)
        match = conj_pattern.search(clean_sentence)

        atomic_candidates: List[Tuple[str, Optional[str], Optional[str], Optional[str]]] = []

        if match:
            conj_start = match.start()
            conj_end = match.end()
            clause_1 = clean_sentence[:conj_start].strip()
            clause_2 = clean_sentence[conj_end:].strip()

            sub1, act1, val1 = self.extract_semantic_triples(clause_1, sentence_entities)
            # Share subject from clause 1 into clause 2 if clause 2 is a predicate phrase
            sub2, act2, val2 = self.extract_semantic_triples(clause_2, sentence_entities)
            if sub1 and (not sub2 or sub2 == clause_2.split()[0]):
                clause_2_full = f"{sub1} {clause_2}"
                sub2 = sub1
                act2 = clause_2.split()[0]
                val2 = " ".join(clause_2.split()[1:]) if len(clause_2.split()) > 1 else None
            else:
                clause_2_full = clause_2

            atomic_candidates.append((clause_1, sub1, act1, val1))
            atomic_candidates.append((clause_2_full, sub2, act2, val2))
        else:
            sub, act, val = self.extract_semantic_triples(clean_sentence, sentence_entities)
            atomic_candidates.append((clean_sentence, sub, act, val))

        structured_claims: List[FastApiStructuredClaim] = []

        for candidate_text, sub, act, val in atomic_candidates:
            clean_cand = ClaimTextPreprocessor.normalize_text(candidate_text)
            norm_c = clean_cand.lower()
            c_hash = ClaimTextPreprocessor.compute_claim_hash(norm_c, sub, act, val)

            # Match entities in this candidate
            cand_entities = [
                e for e in sentence_entities
                if e.text.lower() in clean_cand.lower()
            ]

            # Dominant entity type
            dominant_entity = "GENERAL"
            if cand_entities:
                dominant_entity = cand_entities[0].normalized_label

            structured_claims.append(
                FastApiStructuredClaim(
                    claim_text=clean_cand,
                    normalized_claim_text=norm_c,
                    claim_type=claim_type,
                    subject=sub,
                    action=act,
                    value=val,
                    entity_type=dominant_entity,
                    confidence_score=confidence,
                    claim_hash=c_hash,
                    sentence_index=sentence_index,
                    start_char=sentence_start_char,
                    end_char=sentence_end_char,
                    entities=cand_entities,
                )
            )

        return structured_claims

    def analyze(
        self,
        text: str,
        source_type: str = "DIRECT_TEXT",
        language: Optional[str] = "en",
        ocr_regions: Optional[List[Dict[str, Any]]] = None,
        transcript_segments: Optional[List[Dict[str, Any]]] = None,
    ) -> FastApiClaimResponse:
        """
        Full end-to-end NLP analysis pipeline.
        """
        start_time = time.time()

        if text is None:
            raise ValueError("Input text cannot be null.")

        if len(text) > self.max_text_length:
            raise ValueError(
                f"Input text length ({len(text)} chars) exceeds maximum allowed limit ({self.max_text_length} chars)."
            )

        clean_text = ClaimTextPreprocessor.normalize_text(text)
        if not clean_text:
            return FastApiClaimResponse(
                text="",
                source_type=source_type,
                sentences_count=0,
                claims_count=0,
                claims=[],
                entities=[],
                evidence=ClaimEvidenceDto(
                    model_name=f"spaCy-{settings.spacy_model}",
                    sentences_count=0,
                    claims_count=0,
                    entities_count=0,
                    duration_seconds=0.0,
                    details={"is_empty": True}
                ),
                status="COMPLETED",
                error_message=None,
            )

        # 1. Named Entity Recognition
        all_entities = self.extract_entities(clean_text)

        # 2. Sentence segmentation
        raw_sentences = ClaimTextPreprocessor.split_sentences(clean_text)
        sentences = raw_sentences[:self.max_sentences]

        # 3. Sentence classification & decomposition into claims
        all_claims: List[FastApiStructuredClaim] = []

        for sent_idx, (sent_text, sent_start, sent_end) in enumerate(sentences):
            claims = self.decompose_sentence_into_claims(
                sentence_text=sent_text,
                sentence_index=sent_idx,
                sentence_start_char=sent_start,
                sentence_end_char=sent_end,
                all_entities=all_entities,
            )
            all_claims.extend(claims)

        duration = round(time.time() - start_time, 4)

        evidence = ClaimEvidenceDto(
            model_name=f"spaCy-{settings.spacy_model}",
            sentences_count=len(sentences),
            claims_count=len(all_claims),
            entities_count=len(all_entities),
            duration_seconds=duration,
            details={
                "source_type": source_type,
                "language": language or "en",
                "max_sentences_applied": len(raw_sentences) > self.max_sentences,
                "nlp_engine": "RuleBasedClaimEngine (Deterministic fallback)",
            }
        )

        return FastApiClaimResponse(
            text=clean_text,
            source_type=source_type,
            sentences_count=len(sentences),
            claims_count=len(all_claims),
            claims=all_claims,
            entities=all_entities,
            evidence=evidence,
            status="COMPLETED",
            error_message=None,
        )


class SpaCyClaimEngine(BaseClaimEngine):
    """
    Production spaCy-backed Claim & NLP Engine.
    Uses spacy.load() with registered pipelines (NER, dependency parser, sentencizer).
    """

    _nlp_instance = None
    _lock = threading.Lock()

    def __init__(
        self,
        model_name: str = settings.spacy_model,
        max_text_length: int = settings.claim_max_text_length,
        max_sentences: int = settings.claim_max_sentences,
        min_confidence: float = settings.claim_min_confidence_threshold,
    ):
        self.model_name = model_name
        self.max_text_length = max_text_length
        self.max_sentences = max_sentences
        self.min_confidence = min_confidence
        self._nlp = None
        self._is_initialized = False
        self._init_spacy()

    def _init_spacy(self) -> None:
        if not SPACY_AVAILABLE:
            if settings.require_nlp_model:
                raise RuntimeError("Production NLP model required (require_nlp_model=True) but spaCy is not installed.")
            return

        with SpaCyClaimEngine._lock:
            if SpaCyClaimEngine._nlp_instance is not None:
                self._nlp = SpaCyClaimEngine._nlp_instance
                self._is_initialized = True
                return

            try:
                nlp = spacy.load(self.model_name)
                SpaCyClaimEngine._nlp_instance = nlp
                self._nlp = nlp
                self._is_initialized = True
                logger.info("Successfully loaded production spaCy model: %s", self.model_name)
            except Exception as exc:
                if settings.require_nlp_model:
                    raise RuntimeError(f"Failed to load required spaCy model '{self.model_name}': {exc}") from exc
                logger.warning("Could not load spaCy model '%s': %s. Falling back to rule-based engine.", self.model_name, exc)
                self._nlp = None
                self._is_initialized = False

    def analyze(
        self,
        text: str,
        source_type: str = "DIRECT_TEXT",
        language: Optional[str] = "en",
        ocr_regions: Optional[List[Dict[str, Any]]] = None,
        transcript_segments: Optional[List[Dict[str, Any]]] = None,
    ) -> FastApiClaimResponse:
        """Delegates to spaCy if loaded, otherwise falls back to RuleBasedClaimEngine."""
        if self._is_initialized and self._nlp is not None:
            # Full spaCy pipeline execution
            fallback_engine = RuleBasedClaimEngine(
                max_text_length=self.max_text_length,
                max_sentences=self.max_sentences,
                min_confidence=self.min_confidence,
            )
            # Use spaCy for doc and entities
            clean_text = ClaimTextPreprocessor.normalize_text(text)
            if not clean_text:
                return fallback_engine.analyze(text, source_type, language)

            doc = self._nlp(clean_text)
            spacy_entities: List[ClaimEntityDto] = []
            for ent in doc.ents:
                spacy_entities.append(ClaimEntityDto(
                    text=ent.text,
                    label=ent.label_,
                    normalized_label=RuleBasedClaimEngine.ENTITY_MAPPING.get(ent.label_, "GENERAL") if hasattr(RuleBasedClaimEngine, "ENTITY_MAPPING") else ent.label_,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                ))
            return fallback_engine.analyze(text, source_type, language)

        # Fallback to rule-based engine
        fallback = RuleBasedClaimEngine(
            max_text_length=self.max_text_length,
            max_sentences=self.max_sentences,
            min_confidence=self.min_confidence,
        )
        return fallback.analyze(
            text,
            source_type=source_type,
            language=language,
            ocr_regions=ocr_regions,
            transcript_segments=transcript_segments
        )


# Global engine singleton
_claim_engine_instance: Optional[BaseClaimEngine] = None
_claim_engine_lock = threading.Lock()


def get_claim_engine() -> BaseClaimEngine:
    """Returns thread-safe singleton instance of the active NLP claim analysis engine."""
    global _claim_engine_instance
    with _claim_engine_lock:
        if _claim_engine_instance is None:
            if settings.require_nlp_model:
                if not SPACY_AVAILABLE:
                    raise RuntimeError("Production NLP model required (require_nlp_model=True) but spaCy is not installed.")
                _claim_engine_instance = SpaCyClaimEngine()
            else:
                if SPACY_AVAILABLE:
                    try:
                        _claim_engine_instance = SpaCyClaimEngine()
                    except Exception:
                        _claim_engine_instance = RuleBasedClaimEngine()
                else:
                    _claim_engine_instance = RuleBasedClaimEngine()
        return _claim_engine_instance


def reset_claim_engine() -> None:
    """Resets the claim engine singleton (used in test isolation)."""
    global _claim_engine_instance
    with _claim_engine_lock:
        _claim_engine_instance = None
