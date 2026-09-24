package com.truthlens.backend.dto;

import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.ClaimSourceType;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * REST API response encapsulating structured claim extraction results for a media asset (Module 11).
 */
public class ClaimAnalysisResponse {

    private UUID mediaId;
    private ClaimSourceType sourceType;
    private int analyzedTextLength;
    private int sentencesCount;
    private int claimsCount;
    private List<ClaimDto> claims = new ArrayList<>();
    private List<ClaimEntityDto> entities = new ArrayList<>();
    private ClaimEvidenceDto evidence;
    private AnalysisStatus analysisStatus;
    private OffsetDateTime createdAt;

    public ClaimAnalysisResponse() {
    }

    public ClaimAnalysisResponse(
            UUID mediaId,
            ClaimSourceType sourceType,
            int analyzedTextLength,
            int sentencesCount,
            int claimsCount,
            List<ClaimDto> claims,
            List<ClaimEntityDto> entities,
            ClaimEvidenceDto evidence,
            AnalysisStatus analysisStatus,
            OffsetDateTime createdAt) {
        this.mediaId = mediaId;
        this.sourceType = sourceType;
        this.analyzedTextLength = analyzedTextLength;
        this.sentencesCount = sentencesCount;
        this.claimsCount = claimsCount;
        this.claims = claims != null ? claims : new ArrayList<>();
        this.entities = entities != null ? entities : new ArrayList<>();
        this.evidence = evidence;
        this.analysisStatus = analysisStatus;
        this.createdAt = createdAt;
    }

    public UUID getMediaId() {
        return mediaId;
    }

    public void setMediaId(UUID mediaId) {
        this.mediaId = mediaId;
    }

    public ClaimSourceType getSourceType() {
        return sourceType;
    }

    public void setSourceType(ClaimSourceType sourceType) {
        this.sourceType = sourceType;
    }

    public int getAnalyzedTextLength() {
        return analyzedTextLength;
    }

    public void setAnalyzedTextLength(int analyzedTextLength) {
        this.analyzedTextLength = analyzedTextLength;
    }

    public int getSentencesCount() {
        return sentencesCount;
    }

    public void setSentencesCount(int sentencesCount) {
        this.sentencesCount = sentencesCount;
    }

    public int getClaimsCount() {
        return claimsCount;
    }

    public void setClaimsCount(int claimsCount) {
        this.claimsCount = claimsCount;
    }

    public List<ClaimDto> getClaims() {
        return claims;
    }

    public void setClaims(List<ClaimDto> claims) {
        this.claims = claims;
    }

    public List<ClaimEntityDto> getEntities() {
        return entities;
    }

    public void setEntities(List<ClaimEntityDto> entities) {
        this.entities = entities;
    }

    public ClaimEvidenceDto getEvidence() {
        return evidence;
    }

    public void setEvidence(ClaimEvidenceDto evidence) {
        this.evidence = evidence;
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
}
