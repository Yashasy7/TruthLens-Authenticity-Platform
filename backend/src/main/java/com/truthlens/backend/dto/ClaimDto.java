package com.truthlens.backend.dto;

import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.ClaimEntityType;
import com.truthlens.backend.entity.ClaimSourceType;
import com.truthlens.backend.entity.ClaimType;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Structured DTO representing an individual claim object (Module 11).
 */
public class ClaimDto {

    private UUID id;
    private UUID mediaId;
    private String claimText;
    private String normalizedClaimText;
    private ClaimType claimType;
    private String subject;
    private String action;
    private String value;
    private ClaimEntityType entityType;
    private double confidenceScore;
    private String claimHash;
    private ClaimSourceType sourceType;
    private int sentenceIndex;
    private int startChar;
    private int endChar;
    private List<ClaimEntityDto> entities = new ArrayList<>();
    private AnalysisStatus analysisStatus;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    public ClaimDto() {
    }

    public ClaimDto(
            UUID id,
            UUID mediaId,
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
            List<ClaimEntityDto> entities,
            AnalysisStatus analysisStatus,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt) {
        this.id = id;
        this.mediaId = mediaId;
        this.claimText = claimText;
        this.normalizedClaimText = normalizedClaimText;
        this.claimType = claimType;
        this.subject = subject;
        this.action = action;
        this.value = value;
        this.entityType = entityType;
        this.confidenceScore = confidenceScore;
        this.claimHash = claimHash;
        this.sourceType = sourceType;
        this.sentenceIndex = sentenceIndex;
        this.startChar = startChar;
        this.endChar = endChar;
        this.entities = entities != null ? entities : new ArrayList<>();
        this.analysisStatus = analysisStatus;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public UUID getMediaId() {
        return mediaId;
    }

    public void setMediaId(UUID mediaId) {
        this.mediaId = mediaId;
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

    public List<ClaimEntityDto> getEntities() {
        return entities;
    }

    public void setEntities(List<ClaimEntityDto> entities) {
        this.entities = entities;
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
}
