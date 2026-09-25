package com.truthlens.backend.dto;

import com.truthlens.backend.entity.AnalysisStatus;

import java.time.OffsetDateTime;
import java.util.Collections;
import java.util.List;
import java.util.UUID;

/**
 * Client-facing REST response DTO for OCR visual text extraction analysis.
 */
public class OcrResultResponse {

    private UUID id;
    private UUID mediaId;
    private String extractedText;
    private String language;
    private double confidenceScore;
    private int regionsCount;
    private List<OcrTextRegionDto> regions = Collections.emptyList();
    private OcrEvidenceDto evidence;
    private AnalysisStatus analysisStatus;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    public OcrResultResponse() {
    }

    public OcrResultResponse(
            UUID id,
            UUID mediaId,
            String extractedText,
            String language,
            double confidenceScore,
            int regionsCount,
            List<OcrTextRegionDto> regions,
            OcrEvidenceDto evidence,
            AnalysisStatus analysisStatus,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt) {
        this.id = id;
        this.mediaId = mediaId;
        this.extractedText = extractedText;
        this.language = language;
        this.confidenceScore = confidenceScore;
        this.regionsCount = regionsCount;
        this.regions = regions;
        this.evidence = evidence;
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

    public String getExtractedText() {
        return extractedText;
    }

    public void setExtractedText(String extractedText) {
        this.extractedText = extractedText;
    }

    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }

    public double getConfidenceScore() {
        return confidenceScore;
    }

    public void setConfidenceScore(double confidenceScore) {
        this.confidenceScore = confidenceScore;
    }

    public int getRegionsCount() {
        return regionsCount;
    }

    public void setRegionsCount(int regionsCount) {
        this.regionsCount = regionsCount;
    }

    public List<OcrTextRegionDto> getRegions() {
        return regions;
    }

    public void setRegions(List<OcrTextRegionDto> regions) {
        this.regions = regions;
    }

    public OcrEvidenceDto getEvidence() {
        return evidence;
    }

    public void setEvidence(OcrEvidenceDto evidence) {
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

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(OffsetDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
