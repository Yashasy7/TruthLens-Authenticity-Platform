import hashlib
import re
import threading
import time
import unicodedata
from typing import List, Dict, Any, Tuple, Optional

from ..config import settings
from ..schemas import (
    EntitySpan,
    StructuredClaim,
    ClaimAnalysisEvidence,
    ClaimAnalysisResult,
)

try:
    import spacy
    from spacy.tokens import Doc, Span
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class ClaimExtractor:
    """
    Automated Text & Claim Analysis Engine (Module 11).
    
    Adheres strictly to TruthLens Blueprint Module 11:
    Raw Transcript & OCR Text -> spaCy / HuggingFace NER -> Sentence Classifier -> Structured Claim Objects.
    
    Responsibilities:
    1. Named Entity Recognition (NER) across PERSON, ORG, LOCATION, DATE, MONEY, QUANTITY, EVENT.
    2. Sentence segmentation and classification (FACTUAL_CLAIM, OPINION, QUESTION, NON_CLAIM, UNCERTAIN).
    3. Semantic claim decomposition into Subject, Action, and Value components.
    4. Canonical claim normalization (NFKC, whitespace collapsing, casing).
    5. Deterministic, collision-resistant cryptographic claim hashing (SHA-256).
    6. Thread-safe lazy model initialization with process-level caching.
    """

    _cached_nlp = None
    _model_lock = threading.Lock()

    # Heuristic markers for opinion and subjectivity
    OPINION_MARKERS = [
        "i think", "i believe", "in my opinion", "in our view", "we believe",
        "i feel", "it seems to me", "personally", "my view is", "my impression is",
        "best", "worst", "terrible", "wonderful", "gorgeous", "horrible", "ugly",
        "fantastic", "brilliant", "disgusting", "greatest", "sublime", "disgraceful"
    ]

    # Question lead patterns
    QUESTION_STARTERS = [
        "what", "why", "how", "who", "whom", "whose", "when", "where",
        "is", "are", "was", "were", "can", "could", "would", "will", "shall",
        "should", "do", "does", "did", "have", "has", "had"
    ]

    # Standard TruthLens entity type mapping from spaCy labels
    ENTITY_MAPPING = {
        "PERSON": "PERSON",
        "NORP": "ORG",
        "ORG": "ORG",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "FAC": "LOCATION",
        "DATE": "DATE",
        "TIME": "DATE",
        "MONEY": "MONEY",
        "PERCENT": "QUANTITY",
        "QUANTITY": "QUANTITY",
        "CARDINAL": "QUANTITY",
        "ORDINAL": "QUANTITY",
        "EVENT": "EVENT",
        "LAW": "EVENT",
        "PRODUCT": "GENERAL",
        "WORK_OF_ART": "GENERAL",
        "LANGUAGE": "GENERAL",
    }

    def __init__(
        self,
        model_name: str = settings.SPACY_MODEL,
        max_text_length: int = settings.CLAIM_MAX_TEXT_LENGTH,
        max_sentences: int = settings.CLAIM_MAX_SENTENCES,
        min_confidence: float = settings.CLAIM_MIN_CONFIDENCE_THRESHOLD,
    ):
        self.model_name = model_name
        self.max_text_length = max_text_length
        self.max_sentences = max_sentences
        self.min_confidence = min_confidence

        self._nlp = None
        self._is_initialized = False
        self._init_model()

    def _init_model(self):
        """Thread-safe lazy initialization of spaCy English model."""
        if not SPACY_AVAILABLE:
            return

        with ClaimExtractor._model_lock:
            if ClaimExtractor._cached_nlp is not None:
                self._nlp = ClaimExtractor._cached_nlp
                self._is_initialized = True
                return

            try:
                nlp = spacy.load(self.model_name)
                ClaimExtractor._cached_nlp = nlp
                self._nlp = nlp
                self._is_initialized = True
            except Exception:
                try:
                    # Fallback to blank model if full pipeline not found
                    nlp = spacy.blank("en")
                    if "sentencizer" not in nlp.pipe_names:
                        nlp.add_pipe("sentencizer")
                    ClaimExtractor._cached_nlp = nlp
                    self._nlp = nlp
                    self._is_initialized = True
                except Exception:
                    self._nlp = None
                    self._is_initialized = False

    def normalize_text(self, text: str) -> str:
        """Applies Unicode NFKC normalization and collapses redundant whitespaces."""
        if not text:
            return ""
        norm = unicodedata.normalize("NFKC", text)
        norm = re.sub(r"\s+", " ", norm)
        return norm.strip()

    def compute_claim_hash(
        self,
        normalized_claim: str,
        subject: Optional[str] = None,
        action: Optional[str] = None,
        value: Optional[str] = None,
    ) -> str:
        """
        Computes deterministic, collision-resistant SHA-256 hash over canonical claim representation.
        
        Formula: SHA-256(norm_claim | norm_subject | norm_action | norm_value)
        """
        norm_s = self.normalize_text(subject or "").lower()
        norm_a = self.normalize_text(action or "").lower()
        norm_v = self.normalize_text(value or "").lower()
        norm_c = self.normalize_text(normalized_claim).lower()

        canonical_tuple = f"{norm_c}|{norm_s}|{norm_a}|{norm_v}"
        return hashlib.sha256(canonical_tuple.encode("utf-8")).hexdigest()

    def classify_sentence(self, sent_text: str, has_entities: bool, has_verb: bool) -> Tuple[str, float]:
        """
        Classifies candidate sentence into:
        - FACTUAL_CLAIM: Declarative sentence with subject, predicate, and factual elements.
        - OPINION: Subjective or sentiment-laden assertions.
        - QUESTION: Interrogative expressions.
        - NON_CLAIM: Imperatives, conversational fillers, or short non-assertive phrases.
        - UNCERTAIN: Borderline cases.
        """
        clean = sent_text.strip()
        lower = clean.lower()

        # 1. Question detection
        if clean.endswith("?"):
            return "QUESTION", 0.95
        first_word = lower.split()[0] if lower.split() else ""
        if first_word in self.QUESTION_STARTERS and len(lower.split()) > 2 and clean.endswith((".", "?", "")):
            # Check if likely inverted question
            if lower.startswith(("is it", "are there", "can you", "what if", "why would", "who is")):
                return "QUESTION", 0.90

        # 2. Non-claim: length and structure checks
        words = clean.split()
        if len(words) < 3 or not has_verb:
            return "NON_CLAIM", 0.90

        # Imperative commands (e.g., "Click here", "Subscribe now", "Look at this")
        if first_word in ["click", "subscribe", "look", "see", "watch", "remember", "don't", "do", "listen"]:
            if len(words) <= 6:
                return "NON_CLAIM", 0.85

        # 3. Opinion and subjectivity detection
        for marker in self.OPINION_MARKERS:
            if re.search(r"\b" + re.escape(marker) + r"\b", lower):
                return "OPINION", 0.88

        # 4. Factual claim classification
        base_confidence = 0.70
        if has_entities:
            base_confidence += 0.15
        if re.search(r"\b\d+(?:[\.,]\d+)?\b", clean):  # Contains numerical figures
            base_confidence += 0.10
        if any(w in lower for w in [
            "announced", "increased", "decreased", "reported", "confirmed",
            "signed", "voted", "passed", "discovered", "caused", "won", "lost",
            "visited", "stated", "allocated", "approved", "banned", "declined"
        ]):
            base_confidence += 0.10

        confidence = round(min(0.99, max(0.50, base_confidence)), 2)
        return "FACTUAL_CLAIM", confidence

    def extract_semantic_components(self, sent_span: Any) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Decomposes sentence into (subject, action, value) using dependency parsing when available.
        """
        if not hasattr(sent_span, "root"):
            # Fallback heuristic if dependency parsing not loaded
            words = sent_span.text.split()
            subject = words[0] if len(words) > 0 else None
            action = words[1] if len(words) > 1 else None
            value = " ".join(words[2:]) if len(words) > 2 else None
            return subject, action, value

        root = sent_span.root
        subject_tokens = []
        action_tokens = []
        value_tokens = []

        # Find subject
        for token in sent_span:
            if token.dep_ in ["nsubj", "nsubjpass", "csubj", "csubjpass"]:
                # Collect full noun chunk or subtree for subject
                subject_tokens = [t.text for t in token.subtree if t.dep_ not in ["punct"]]
                break

        # Action (root verb and associated auxiliaries/negations)
        action_parts = []
        for token in sent_span:
            if token.head == root and token.dep_ in ["aux", "auxpass", "neg", "prt"]:
                if token.i < root.i:
                    action_parts.append(token.text)
        action_parts.append(root.text)
        for token in sent_span:
            if token.head == root and token.dep_ in ["prt"]:
                if token.i > root.i:
                    action_parts.append(token.text)
        action_tokens = action_parts

        # Value / Complement (direct object, prepositional object, attribute, complement)
        for token in sent_span:
            if token.dep_ in ["dobj", "attr", "pobj", "dative", "acomp"]:
                value_tokens = [t.text for t in token.subtree if t.dep_ not in ["punct"]]
                break

        subject = " ".join(subject_tokens).strip() if subject_tokens else None
        action = " ".join(action_tokens).strip() if action_tokens else root.text
        value = " ".join(value_tokens).strip() if value_tokens else None

        # Fallback if value not found via primary object
        if not value and len(sent_span) > 2:
            remaining = [t.text for t in sent_span if t.text not in (subject or "") and t.text not in action and not t.is_punct]
            if remaining:
                value = " ".join(remaining[:8]).strip()

        return subject, action, value

    def analyze(
        self,
        text: str,
        source_type: str = "DIRECT_TEXT",
        language: Optional[str] = "en",
    ) -> ClaimAnalysisResult:
        """
        Executes complete text and claim analysis pipeline.
        
        Args:
            text: Raw input text from OCR, speech transcript, or ad-hoc query.
            source_type: Identifier of source ('OCR', 'TRANSCRIPT', 'COMBINED', 'DIRECT_TEXT').
            language: Language hint (defaults to 'en').
            
        Returns:
            Structured ClaimAnalysisResult with extracted entities and claims.
        """
        start_time = time.time()

        if text is None:
            raise ValueError("Input text cannot be null.")

        if len(text) > self.max_text_length:
            raise ValueError(
                f"Input text length ({len(text)} chars) exceeds maximum allowed limit ({self.max_text_length} chars)."
            )

        clean_text = self.normalize_text(text)
        if not clean_text:
            return ClaimAnalysisResult(
                text="",
                source_type=source_type,
                sentences_count=0,
                claims_count=0,
                claims=[],
                entities=[],
                evidence=ClaimAnalysisEvidence(
                    model_name=f"spaCy-{self.model_name}",
                    sentences_count=0,
                    claims_count=0,
                    entities_count=0,
                    duration_seconds=0.0,
                    details={"is_empty": True}
                ),
                status="COMPLETED",
                error_message=None
            )

        # Process with spaCy if initialized
        doc = self._nlp(clean_text) if (self._is_initialized and self._nlp is not None) else None

        all_entities: List[EntitySpan] = []
        if doc and doc.ents:
            for ent in doc.ents:
                raw_label = ent.label_
                norm_label = self.ENTITY_MAPPING.get(raw_label, "GENERAL")
                all_entities.append(EntitySpan(
                    text=ent.text,
                    label=raw_label,
                    normalized_label=norm_label,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                ))

        # Sentence extraction
        sentences = list(doc.sents) if (doc and doc.has_annotation("SENT_START")) else [clean_text]
        sentences = sentences[:self.max_sentences]

        claims: List[StructuredClaim] = []

        for sent_idx, sent in enumerate(sentences):
            sent_text = sent.text if hasattr(sent, "text") else str(sent)
            sent_text = self.normalize_text(sent_text)
            if not sent_text:
                continue

            sent_start = sent.start_char if hasattr(sent, "start_char") else 0
            sent_end = sent.end_char if hasattr(sent, "end_char") else len(sent_text)

            # Entities in this specific sentence
            sent_entities = [
                e for e in all_entities
                if e.start_char >= sent_start and e.end_char <= sent_end
            ]

            has_verb = any(t.pos_ == "VERB" for t in sent) if hasattr(sent, "pos_") else True
            has_ents = len(sent_entities) > 0

            # Classification
            claim_type, confidence = self.classify_sentence(sent_text, has_entities=has_ents, has_verb=has_verb)

            # Decomposition
            subject, action, value = self.extract_semantic_components(sent)

            # Dominant entity type
            dominant_entity_type = "GENERAL"
            if sent_entities:
                dominant_entity_type = sent_entities[0].normalized_label

            # Normalization and Hash
            norm_claim = self.normalize_text(sent_text)
            claim_hash = self.compute_claim_hash(norm_claim, subject, action, value)

            claims.append(StructuredClaim(
                claim_text=sent_text,
                normalized_claim_text=norm_claim,
                claim_type=claim_type,
                subject=subject,
                action=action,
                value=value,
                entity_type=dominant_entity_type,
                confidence_score=confidence,
                claim_hash=claim_hash,
                sentence_index=sent_idx,
                start_char=sent_start,
                end_char=sent_end,
                entities=sent_entities,
            ))

        duration = round(time.time() - start_time, 4)

        evidence = ClaimAnalysisEvidence(
            model_name=f"spaCy-{self.model_name}",
            sentences_count=len(sentences),
            claims_count=len(claims),
            entities_count=len(all_entities),
            duration_seconds=duration,
            details={
                "source_type": source_type,
                "language": language or "en",
                "max_sentences_applied": len(sentences) >= self.max_sentences,
            }
        )

        return ClaimAnalysisResult(
            text=clean_text,
            source_type=source_type,
            sentences_count=len(sentences),
            claims_count=len(claims),
            claims=claims,
            entities=all_entities,
            evidence=evidence,
            status="COMPLETED",
            error_message=None,
        )
