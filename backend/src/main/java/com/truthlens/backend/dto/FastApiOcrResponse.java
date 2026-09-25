package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Collections;
import java.util.List;

/**
 * DTO matching the raw JSON response returned by the Python FastAPI OCR service.
 */
public class FastApiOcrResponse {

    @JsonProperty("extracted_text")
    private String extractedText;

    private String language;

    @JsonProperty("confidence_score")
    private double confidenceScore;

    @JsonProperty("regions_count")
    private int regionsCount;

    private List<OcrTextRegionDto> regions = Collections.emptyList();

    private OcrEvidenceDto evidence;

    private String status;

    @JsonProperty("error_message")
    private String errorMessage;

    public FastApiOcrResponse() {
    }

    public FastApiOcrResponse(
            String extractedText,
            String language,
            double confidenceScore,
            int regionsCount,
            List<OcrTextRegionDto> regions,
            OcrEvidenceDto evidence,
            String status,
            String errorMessage) {
        this.extractedText = extractedText;
        this.language = language;
        this.confidenceScore = confidenceScore;
        this.regionsCount = regionsCount;
        this.regions = regions;
        this.evidence = evidence;
        this.status = status;
        this.errorMessage = errorMessage;
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

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }
}
