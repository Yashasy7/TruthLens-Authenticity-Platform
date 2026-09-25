package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Request payload sent to Python FastAPI for Text & Claim Analysis (Module 11).
 */
public class FastApiClaimRequest {

    private String text;

    @JsonProperty("source_type")
    private String sourceType = "DIRECT_TEXT";

    private String language = "en";

    public FastApiClaimRequest() {
    }

    public FastApiClaimRequest(String text, String sourceType, String language) {
        this.text = text;
        this.sourceType = sourceType != null ? sourceType : "DIRECT_TEXT";
        this.language = language != null ? language : "en";
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

    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }
}
