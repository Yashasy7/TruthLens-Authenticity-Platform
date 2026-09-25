package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * DTO representing an extracted named entity span (Module 11).
 */
public class ClaimEntityDto {

    private String text;
    private String label;

    @JsonProperty("normalized_label")
    private String normalizedLabel;

    @JsonProperty("start_char")
    private int startChar;

    @JsonProperty("end_char")
    private int endChar;

    public ClaimEntityDto() {
    }

    public ClaimEntityDto(String text, String label, String normalizedLabel, int startChar, int endChar) {
        this.text = text;
        this.label = label;
        this.normalizedLabel = normalizedLabel;
        this.startChar = startChar;
        this.endChar = endChar;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public String getLabel() {
        return label;
    }

    public void setLabel(String label) {
        this.label = label;
    }

    public String getNormalizedLabel() {
        return normalizedLabel;
    }

    public void setNormalizedLabel(String normalizedLabel) {
        this.normalizedLabel = normalizedLabel;
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
}
