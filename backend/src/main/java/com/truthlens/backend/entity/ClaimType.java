package com.truthlens.backend.entity;

/**
 * Categorization of analyzed text segments according to verifiable assertiveness (Module 11).
 */
public enum ClaimType {
    FACTUAL_CLAIM,
    OPINION,
    QUESTION,
    NON_CLAIM,
    UNCERTAIN
}
