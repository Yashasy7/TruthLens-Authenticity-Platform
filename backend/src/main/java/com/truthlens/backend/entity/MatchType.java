package com.truthlens.backend.entity;

/**
 * Represents the classification of duplicate match found during media fingerprinting.
 *
 * <ul>
 *   <li>{@link #NONE} — No duplicate found; media is unique.</li>
 *   <li>{@link #EXACT_SHA256} — Byte-level exact duplicate matching an existing SHA-256 hash.</li>
 *   <li>{@link #NEAR_MATCH_PHASH} — Visual near-duplicate identified via perceptual hashing (pHash/dHash).</li>
 *   <li>{@link #ACOUSTIC_MATCH} — Acoustic near-duplicate identified via audio fingerprinting.</li>
 * </ul>
 */
public enum MatchType {

    /** No duplicate detected. */
    NONE,

    /** Exact cryptographic match via SHA-256 checksum. */
    EXACT_SHA256,

    /** Visual near-duplicate via perceptual image hashing. */
    NEAR_MATCH_PHASH,

    /** Acoustic near-duplicate via audio chromaprint. */
    ACOUSTIC_MATCH
}
