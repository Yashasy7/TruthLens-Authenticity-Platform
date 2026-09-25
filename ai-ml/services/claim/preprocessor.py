"""
TruthLens AI/ML — Module 11: Text & Claim Preprocessor
Blueprint Section D: Text normalization, Unicode canonicalization, sentence segmentation,
and deterministic claim hashing for truth/evidence deduplication.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import List, Optional, Tuple


class ClaimTextPreprocessor:
    """
    Deterministic, explainable text normalization and sentence segmentation engine.
    Ensures safe, canonical processing of arbitrary text from OCR, audio transcripts, or user input.
    """

    # Non-printable control characters (excluding newline \n and tab \t if needed before collapsing)
    _CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

    # Whitespace collapsing pattern
    _WHITESPACE_REGEX = re.compile(r"\s+")

    # Abbreviations that should not trigger sentence boundaries
    _COMMON_ABBREVIATIONS = {
        "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "rep.", "sen.",
        "gen.", "col.", "gov.", "pres.", "st.", "ave.", "blvd.", "dept.",
        "u.s.", "u.k.", "e.u.", "u.n.", "f.b.i.", "c.i.a.", "i.e.", "e.g.",
        "inc.", "corp.", "ltd.", "co.", "vs.", "etc.", "approx.", "est."
    }

    @classmethod
    def clean_control_characters(cls, text: str) -> str:
        """Removes unsafe non-printable control characters from text."""
        if not text:
            return ""
        return cls._CONTROL_CHAR_REGEX.sub("", text)

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Applies Unicode NFKC normalization, safe control-character removal,
        and collapses whitespace into single space while preserving punctuation.
        """
        if not text:
            return ""
        # 1. Clean control characters
        cleaned = cls.clean_control_characters(text)
        # 2. Unicode NFKC normalization
        normalized = unicodedata.normalize("NFKC", cleaned)
        # 3. Collapse multiple whitespace characters into a single space
        collapsed = cls._WHITESPACE_REGEX.sub(" ", normalized)
        return collapsed.strip()

    @classmethod
    def compute_claim_hash(
        cls,
        normalized_claim: str,
        subject: Optional[str] = None,
        action: Optional[str] = None,
        value: Optional[str] = None,
    ) -> str:
        """
        Computes deterministic, collision-resistant 64-character SHA-256 hash
        over canonical claim representation.
        Formula: SHA-256(norm_claim | norm_subject | norm_action | norm_value)
        """
        norm_c = cls.normalize_text(normalized_claim or "").lower()
        norm_s = cls.normalize_text(subject or "").lower()
        norm_a = cls.normalize_text(action or "").lower()
        norm_v = cls.normalize_text(value or "").lower()

        canonical_tuple = f"{norm_c}|{norm_s}|{norm_a}|{norm_v}"
        return hashlib.sha256(canonical_tuple.encode("utf-8")).hexdigest()

    @classmethod
    def split_sentences(cls, text: str) -> List[Tuple[str, int, int]]:
        """
        Segments normalized text into sentences, preserving character offsets (start_char, end_char).
        Handles standard terminal punctuation (. ! ?) while respecting common abbreviations,
        acronyms, decimal points, and URLs.
        
        Returns:
            List of tuples: (sentence_text, start_char, end_char)
        """
        clean_text = cls.normalize_text(text)
        if not clean_text:
            return []

        # Find potential sentence boundaries
        sentences: List[Tuple[str, int, int]] = []
        n = len(clean_text)
        start_idx = 0
        i = 0

        while i < n:
            char = clean_text[i]

            # Terminal punctuation candidates
            if char in ".!?":
                # Check for multiple consecutive punctuation marks (e.g., "...", "!?")
                end_punct = i
                while end_punct + 1 < n and clean_text[end_punct + 1] in ".!?":
                    end_punct += 1

                is_boundary = False

                if end_punct == n - 1:
                    # End of string is always a boundary
                    is_boundary = True
                elif end_punct + 1 < n and clean_text[end_punct + 1] == " ":
                    # Check if this period is part of a number (e.g. "3.14")
                    is_numeric = False
                    if char == "." and i > 0 and clean_text[i - 1].isdigit():
                        if end_punct + 2 < n and clean_text[end_punct + 2].isdigit():
                            is_numeric = True

                    if not is_numeric:
                        # Check abbreviation candidate
                        candidate_token = clean_text[start_idx:end_punct + 1].split()[-1].lower().strip(" ,;:") if clean_text[start_idx:end_punct + 1].split() else ""
                        is_abbreviation = (
                            candidate_token in cls._COMMON_ABBREVIATIONS
                            or bool(re.match(r"^[a-z](\.[a-z])+\.?$", candidate_token))
                            or bool(re.match(r"^[a-z]\.$", candidate_token))
                        )

                        # Look ahead to next word's initial character
                        next_char_idx = end_punct + 1
                        while next_char_idx < n and clean_text[next_char_idx] == " ":
                            next_char_idx += 1

                        if is_abbreviation:
                            is_boundary = False
                        elif next_char_idx < n and clean_text[next_char_idx].islower():
                            # Next word begins with lowercase; unlikely sentence boundary
                            is_boundary = False
                        else:
                            is_boundary = True

                if is_boundary:
                    sent = clean_text[start_idx:end_punct + 1].strip()
                    if sent:
                        # Compute actual start_char after leading spaces
                        actual_start = start_idx
                        while actual_start <= end_punct and clean_text[actual_start] == " ":
                            actual_start += 1
                        actual_end = actual_start + len(sent)
                        sentences.append((sent, actual_start, actual_end))
                    
                    # Advance past following spaces
                    next_start = end_punct + 1
                    while next_start < n and clean_text[next_start] == " ":
                        next_start += 1
                    start_idx = next_start
                    i = next_start
                    continue

            i += 1

        # Residual sentence fragment at end of text
        if start_idx < n:
            sent = clean_text[start_idx:].strip()
            if sent:
                actual_start = start_idx
                while actual_start < n and clean_text[actual_start] == " ":
                    actual_start += 1
                actual_end = actual_start + len(sent)
                sentences.append((sent, actual_start, actual_end))

        return sentences
