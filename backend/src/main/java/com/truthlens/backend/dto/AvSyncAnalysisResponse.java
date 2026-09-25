package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.truthlens.backend.entity.AnalysisStatus;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Top-level response DTO representing Audio-Video Synchronization Analysis findings (Module 08).
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AvSyncAnalysisResponse {

    private UUID id;
    private UUID mediaId;
    private double syncScore;
    private double lipOffsetMs;
    private double confidence;
    private String assessment;
    private AnalysisStatus analysisStatus;
    private String modelName;
    private String modelVersion;
    private List<MismatchSegmentDto> mismatchSegments = new ArrayList<>();
    private AvSyncEvidenceDto evidence;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    public AvSyncAnalysisResponse() {
    }

    public AvSyncAnalysisResponse(
            UUID id,
            UUID mediaId,
            double syncScore,
            double lipOffsetMs,
            double confidence,
            String assessment,
            AnalysisStatus analysisStatus,
            String modelName,
            String modelVersion,
            List<MismatchSegmentDto> mismatchSegments,
            AvSyncEvidenceDto evidence,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt) {
        this.id = id;
        this.mediaId = mediaId;
        this.syncScore = syncScore;
        this.lipOffsetMs = lipOffsetMs;
        this.confidence = confidence;
        this.assessment = assessment;
        this.analysisStatus = analysisStatus;
        this.modelName = modelName;
        this.modelVersion = modelVersion;
        this.mismatchSegments = mismatchSegments != null ? mismatchSegments : new ArrayList<>();
        this.evidence = evidence;
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

    public double getSyncScore() {
        return syncScore;
    }

    public void setSyncScore(double syncScore) {
        this.syncScore = syncScore;
    }

    public double getLipOffsetMs() {
        return lipOffsetMs;
    }

    public void setLipOffsetMs(double lipOffsetMs) {
        this.lipOffsetMs = lipOffsetMs;
    }

    public double getConfidence() {
        return confidence;
    }

    public void setConfidence(double confidence) {
        this.confidence = confidence;
    }

    public String getAssessment() {
        return assessment;
    }

    public void setAssessment(String assessment) {
        this.assessment = assessment;
    }

    public AnalysisStatus getAnalysisStatus() {
        return analysisStatus;
    }

    public void setAnalysisStatus(AnalysisStatus analysisStatus) {
        this.analysisStatus = analysisStatus;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
    }

    public List<MismatchSegmentDto> getMismatchSegments() {
        return mismatchSegments;
    }

    public void setMismatchSegments(List<MismatchSegmentDto> mismatchSegments) {
        this.mismatchSegments = mismatchSegments;
    }

    public AvSyncEvidenceDto getEvidence() {
        return evidence;
    }

    public void setEvidence(AvSyncEvidenceDto evidence) {
        this.evidence = evidence;
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
