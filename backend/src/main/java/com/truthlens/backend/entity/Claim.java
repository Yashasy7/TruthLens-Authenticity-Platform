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
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Objects;
import java.util.UUID;

/**
 * JPA entity representing a structured claim object (Module 11).
 *
 * <p>Mapped to the {@code claims} table. Stores structured factual assertions,
 * semantic components (Subject, Action, Value), named entities, and deterministic
 * collision-resistant SHA-256 claim hashes.</p>
 */
@Entity
@Table(name = "claims")
public class Claim {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "media_id", nullable = false)
    private Media media;

    @Column(name = "claim_text", nullable = false, columnDefinition = "TEXT")
    private String claimText;

    @Column(name = "normalized_claim_text", nullable = false, columnDefinition = "TEXT")
    private String normalizedClaimText;

    @Enumerated(EnumType.STRING)
    @Column(name = "claim_type", nullable = false, length = 50)
    private ClaimType claimType = ClaimType.FACTUAL_CLAIM;

    @Column(name = "subject", length = 255)
    private String subject;

    @Column(name = "action", length = 255)
    private String action;

    @Column(name = "\"value\"", columnDefinition = "TEXT")
    private String value;

    @Enumerated(EnumType.STRING)
    @Column(name = "entity_type", nullable = false, length = 50)
    private ClaimEntityType entityType = ClaimEntityType.GENERAL;

    @Column(name = "confidence_score", nullable = false)
    private double confidenceScore = 1.0;

    @Column(name = "claim_hash", nullable = false, length = 64)
    private String claimHash;

    @Enumerated(EnumType.STRING)
    @Column(name = "source_type", nullable = false, length = 50)
    private ClaimSourceType sourceType = ClaimSourceType.TRANSCRIPT;

    @Column(name = "sentence_index", nullable = false)
    private int sentenceIndex = 0;

    @Column(name = "start_char", nullable = false)
    private int startChar = 0;

    @Column(name = "end_char", nullable = false)
    private int endChar = 0;

    @Column(name = "entities_json", columnDefinition = "TEXT")
    private String entitiesJson;

    @Enumerated(EnumType.STRING)
    @Column(name = "analysis_status", nullable = false, length = 30)
    private AnalysisStatus analysisStatus = AnalysisStatus.COMPLETED;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public Claim() {
    }

    public Claim(
            Media media,
            String claimText,
            String normalizedClaimText,
            ClaimType claimType,
            String subject,
            String action,
            String value,
            ClaimEntityType entityType,
            double confidenceScore,
            String claimHash,
            ClaimSourceType sourceType,
            int sentenceIndex,
            int startChar,
            int endChar,
            String entitiesJson,
            AnalysisStatus analysisStatus) {
        this.media = media;
        this.claimText = claimText;
        this.normalizedClaimText = normalizedClaimText;
        this.claimType = claimType != null ? claimType : ClaimType.FACTUAL_CLAIM;
        this.subject = subject;
        this.action = action;
        this.value = value;
        this.entityType = entityType != null ? entityType : ClaimEntityType.GENERAL;
        this.confidenceScore = confidenceScore;
        this.claimHash = claimHash;
        this.sourceType = sourceType != null ? sourceType : ClaimSourceType.TRANSCRIPT;
        this.sentenceIndex = sentenceIndex;
        this.startChar = startChar;
        this.endChar = endChar;
        this.entitiesJson = entitiesJson;
        this.analysisStatus = analysisStatus != null ? analysisStatus : AnalysisStatus.COMPLETED;
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
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = OffsetDateTime.now(ZoneOffset.UTC);
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public Media getMedia() {
        return media;
    }

    public void setMedia(Media media) {
        this.media = media;
    }

    public String getClaimText() {
        return claimText;
    }

    public void setClaimText(String claimText) {
        this.claimText = claimText;
    }

    public String getNormalizedClaimText() {
        return normalizedClaimText;
    }

    public void setNormalizedClaimText(String normalizedClaimText) {
        this.normalizedClaimText = normalizedClaimText;
    }

    public ClaimType getClaimType() {
        return claimType;
    }

    public void setClaimType(ClaimType claimType) {
        this.claimType = claimType;
    }

    public String getSubject() {
        return subject;
    }

    public void setSubject(String subject) {
        this.subject = subject;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public String getValue() {
        return value;
    }

    public void setValue(String value) {
        this.value = value;
    }

    public ClaimEntityType getEntityType() {
        return entityType;
    }

    public void setEntityType(ClaimEntityType entityType) {
        this.entityType = entityType;
    }

    public double getConfidenceScore() {
        return confidenceScore;
    }

    public void setConfidenceScore(double confidenceScore) {
        this.confidenceScore = confidenceScore;
    }

    public String getClaimHash() {
        return claimHash;
    }

    public void setClaimHash(String claimHash) {
        this.claimHash = claimHash;
    }

    public ClaimSourceType getSourceType() {
        return sourceType;
    }

    public void setSourceType(ClaimSourceType sourceType) {
        this.sourceType = sourceType;
    }

    public int getSentenceIndex() {
        return sentenceIndex;
    }

    public void setSentenceIndex(int sentenceIndex) {
        this.sentenceIndex = sentenceIndex;
    }

    public int getStartChar() {
        return startChar;
    }

    public void setStartChar(int startChar) {
        this.startChar = startChar;
    }

    public int getEndChar() {
        return endChar;
    }

    public void setEndChar(int endChar) {
        this.endChar = endChar;
    }

    public String getEntitiesJson() {
        return entitiesJson;
    }

    public void setEntitiesJson(String entitiesJson) {
        this.entitiesJson = entitiesJson;
    }

    public AnalysisStatus getAnalysisStatus() {
        return analysisStatus;
    }

    public void setAnalysisStatus(AnalysisStatus analysisStatus) {
        this.analysisStatus = analysisStatus;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(OffsetDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(OffsetDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Claim that)) return false;
        return Objects.equals(id, that.id) ||
                (media != null && that.media != null &&
                 Objects.equals(media.getId(), that.media.getId()) &&
                 Objects.equals(claimHash, that.claimHash));
    }

    @Override
    public int hashCode() {
        return id != null ? id.hashCode() : Objects.hash(media != null ? media.getId() : null, claimHash);
    }
}
