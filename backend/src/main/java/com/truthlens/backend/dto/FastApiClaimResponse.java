package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.ArrayList;
import java.util.List;

/**
 * DTO matching response returned by Python FastAPI POST /api/v1/analyze/claims.
 */
public class FastApiClaimResponse {

    private String text;

    @JsonProperty("source_type")
    private String sourceType;

    @JsonProperty("sentences_count")
    private int sentencesCount;

    @JsonProperty("claims_count")
    private int claimsCount;

    private List<FastApiStructuredClaim> claims = new ArrayList<>();
    private List<ClaimEntityDto> entities = new ArrayList<>();
    private ClaimEvidenceDto evidence;
    private String status;

    @JsonProperty("error_message")
    private String errorMessage;

    public FastApiClaimResponse() {
    }

    public FastApiClaimResponse(
            String text,
            String sourceType,
            int sentencesCount,
            int claimsCount,
            List<FastApiStructuredClaim> claims,
            List<ClaimEntityDto> entities,
            ClaimEvidenceDto evidence,
            String status,
            String errorMessage) {
        this.text = text;
        this.sourceType = sourceType;
        this.sentencesCount = sentencesCount;
        this.claimsCount = claimsCount;
        this.claims = claims != null ? claims : new ArrayList<>();
        this.entities = entities != null ? entities : new ArrayList<>();
        this.evidence = evidence;
        this.status = status;
        this.errorMessage = errorMessage;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public String getSourceType() {
        return sourceType;
    }

    public void setSourceType(String sourceType) {
        this.sourceType = sourceType;
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

    public List<FastApiStructuredClaim> getClaims() {
        return claims;
    }

    public void setClaims(List<FastApiStructuredClaim> claims) {
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
