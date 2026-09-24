package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.ArrayList;
import java.util.List;

/**
 * DTO matching structured claim object returned by Python FastAPI.
 */
public class FastApiStructuredClaim {

    @JsonProperty("claim_text")
    private String claimText;

    @JsonProperty("normalized_claim_text")
    private String normalizedClaimText;

    @JsonProperty("claim_type")
    private String claimType;

    private String subject;
    private String action;
    private String value;

    @JsonProperty("entity_type")
    private String entityType;

    @JsonProperty("confidence_score")
    private double confidenceScore;

    @JsonProperty("claim_hash")
    private String claimHash;

    @JsonProperty("sentence_index")
    private int sentenceIndex;

    @JsonProperty("start_char")
    private int startChar;

    @JsonProperty("end_char")
    private int endChar;

    private List<ClaimEntityDto> entities = new ArrayList<>();

    public FastApiStructuredClaim() {
    }

    public FastApiStructuredClaim(
            String claimText,
            String normalizedClaimText,
            String claimType,
            String subject,
            String action,
            String value,
            String entityType,
            double confidenceScore,
            String claimHash,
            int sentenceIndex,
            int startChar,
            int endChar,
            List<ClaimEntityDto> entities) {
        this.claimText = claimText;
        this.normalizedClaimText = normalizedClaimText;
        this.claimType = claimType;
        this.subject = subject;
        this.action = action;
        this.value = value;
        this.entityType = entityType;
        this.confidenceScore = confidenceScore;
        this.claimHash = claimHash;
        this.sentenceIndex = sentenceIndex;
        this.startChar = startChar;
        this.endChar = endChar;
        this.entities = entities != null ? entities : new ArrayList<>();
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

    public String getClaimType() {
        return claimType;
    }

    public void setClaimType(String claimType) {
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

    public String getEntityType() {
        return entityType;
    }

    public void setEntityType(String entityType) {
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
}
