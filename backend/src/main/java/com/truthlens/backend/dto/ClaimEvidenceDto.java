package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.HashMap;
import java.util.Map;

/**
 * Forensic execution metadata for Text & Claim Analysis (Module 11).
 */
public class ClaimEvidenceDto {

    @JsonProperty("model_name")
    private String modelName;

    @JsonProperty("sentences_count")
    private int sentencesCount;

    @JsonProperty("claims_count")
    private int claimsCount;

    @JsonProperty("entities_count")
    private int entitiesCount;

    @JsonProperty("duration_seconds")
    private double durationSeconds;

    private Map<String, Object> details = new HashMap<>();

    public ClaimEvidenceDto() {
    }

    public ClaimEvidenceDto(
            String modelName,
            int sentencesCount,
            int claimsCount,
            int entitiesCount,
            double durationSeconds,
            Map<String, Object> details) {
        this.modelName = modelName;
        this.sentencesCount = sentencesCount;
        this.claimsCount = claimsCount;
        this.entitiesCount = entitiesCount;
        this.durationSeconds = durationSeconds;
        this.details = details != null ? details : new HashMap<>();
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
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

    public int getEntitiesCount() {
        return entitiesCount;
    }

    public void setEntitiesCount(int entitiesCount) {
        this.entitiesCount = entitiesCount;
    }

    public double getDurationSeconds() {
        return durationSeconds;
    }

    public void setDurationSeconds(double durationSeconds) {
        this.durationSeconds = durationSeconds;
    }

    public Map<String, Object> getDetails() {
        return details;
    }

    public void setDetails(Map<String, Object> details) {
        this.details = details;
    }
}
