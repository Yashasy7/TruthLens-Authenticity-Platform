package com.truthlens.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Request payload for ad-hoc text and claim decomposition (Module 11).
 */
public class AdHocTextClaimRequest {

    @NotBlank(message = "Text cannot be blank")
    @Size(max = 100000, message = "Text exceeds maximum allowed length of 100000 characters")
    private String text;

    private String sourceType = "DIRECT_TEXT";
    private String language = "en";

    public AdHocTextClaimRequest() {
    }

    public AdHocTextClaimRequest(String text, String sourceType, String language) {
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
