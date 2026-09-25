package com.truthlens.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Objects;
import java.util.UUID;

/**
 * JPA entity representing cryptographic and perceptual fingerprints of ingested media in TruthLens.
 *
 * <p>Mapped to the {@code media_hashes} table. Stores:</p>
 * <ul>
 *   <li>Cryptographic SHA-256 digest for byte-exact duplicate matching.</li>
 *   <li>Perceptual visual hash (pHash/dHash) for near-duplicate image/video detection.</li>
 *   <li>Acoustic chromaprint for audio fingerprinting.</li>
 *   <li>Duplicate detection match results and similarity scores.</li>
 * </ul>
 */
@Entity
@Table(name = "media_hashes")
public class MediaHash {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "media_id", nullable = false, unique = true)
    private Media media;

    @Column(name = "sha256_hash", nullable = false, length = 64)
    private String sha256Hash;

    @Column(name = "phash", length = 64)
    private String phash;

    @Column(name = "phash_vector", length = 128)
    private String phashVector;

    @Column(name = "chromaprint", length = 1000)
    private String chromaprint;

    @Column(name = "chromaprint_hash", length = 64)
    private String chromaprintHash;

    @Column(name = "is_duplicate", nullable = false)
    private boolean isDuplicate = false;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "duplicate_of_id")
    private Media duplicateOf;

    @Column(name = "similarity_score")
    private Double similarityScore;

    @Enumerated(EnumType.STRING)
    @Column(name = "match_type", nullable = false, length = 30)
    private MatchType matchType = MatchType.NONE;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public MediaHash() {
    }

    public MediaHash(Media media, String sha256Hash, String phash, String chromaprint) {
        this(media, sha256Hash, phash, null, chromaprint, null);
    }

    public MediaHash(Media media, String sha256Hash, String phash, String phashVector, String chromaprint, String chromaprintHash) {
        this.media = media;
        this.sha256Hash = sha256Hash;
        this.phash = phash;
        this.phashVector = phashVector;
        this.chromaprint = chromaprint;
        this.chromaprintHash = chromaprintHash;
        this.isDuplicate = false;
        this.matchType = MatchType.NONE;
    }

    public void setDuplicateMatch(Media duplicateOf, MatchType matchType, Double similarityScore) {
        this.isDuplicate = true;
        this.duplicateOf = duplicateOf;
        this.matchType = matchType;
        this.similarityScore = similarityScore;
    }

    @PrePersist
    protected void onCreate() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        if (createdAt == null) {
            createdAt = now;
        }
        if (updatedAt == null) {
            updatedAt = now;
        }
        if (matchType == null) {
            matchType = MatchType.NONE;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = OffsetDateTime.now(ZoneOffset.UTC);
    }

    // -------------------------------------------------------------------------
    // Getters and Setters
    // -------------------------------------------------------------------------

    public UUID getId() {
        return id;
    }

    public Media getMedia() {
        return media;
    }

    public void setMedia(Media media) {
        this.media = media;
    }

    public String getSha256Hash() {
        return sha256Hash;
    }

    public void setSha256Hash(String sha256Hash) {
        this.sha256Hash = sha256Hash;
    }

    public String getPhash() {
        return phash;
    }

    public void setPhash(String phash) {
        this.phash = phash;
    }

    public String getPhashVector() {
        return phashVector;
    }

    public void setPhashVector(String phashVector) {
        this.phashVector = phashVector;
    }

    public String getChromaprint() {
        return chromaprint;
    }

    public void setChromaprint(String chromaprint) {
        this.chromaprint = chromaprint;
    }

    public String getChromaprintHash() {
        return chromaprintHash;
    }

    public void setChromaprintHash(String chromaprintHash) {
        this.chromaprintHash = chromaprintHash;
    }

    public boolean isDuplicate() {
        return isDuplicate;
    }

    public void setDuplicate(boolean duplicate) {
        isDuplicate = duplicate;
    }

    public Media getDuplicateOf() {
        return duplicateOf;
    }

    public void setDuplicateOf(Media duplicateOf) {
        this.duplicateOf = duplicateOf;
    }

    public Double getSimilarityScore() {
        return similarityScore;
    }

    public void setSimilarityScore(Double similarityScore) {
        this.similarityScore = similarityScore;
    }

    public MatchType getMatchType() {
        return matchType;
    }

    public void setMatchType(MatchType matchType) {
        this.matchType = matchType;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof MediaHash other)) return false;
        return id != null && id.equals(other.id);
    }

    @Override
    public int hashCode() {
        return getClass().hashCode();
    }
}
