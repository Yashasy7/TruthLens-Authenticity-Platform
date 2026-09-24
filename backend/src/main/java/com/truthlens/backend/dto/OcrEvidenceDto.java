package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * DTO representing visual preprocessing metadata, detected languages, and extraction parameters.
 */
public class OcrEvidenceDto {

    @JsonProperty("total_regions")
    private int totalRegions;

    @JsonProperty("detected_languages")
    private List<String> detectedLanguages = Collections.emptyList();

    @JsonProperty("image_width")
    private int imageWidth;

    @JsonProperty("image_height")
    private int imageHeight;

    @JsonProperty("engine_used")
    private String engineUsed = "EasyOCR";

    @JsonProperty("preprocessing_applied")
    private List<String> preprocessingApplied = Collections.emptyList();

    @JsonProperty("media_type")
    private String mediaType = "IMAGE";

    @JsonProperty("frames_analyzed")
    private int framesAnalyzed = 1;

    private Map<String, Object> details = Collections.emptyMap();

    public OcrEvidenceDto() {
    }

    public OcrEvidenceDto(
            int totalRegions,
            List<String> detectedLanguages,
            int imageWidth,
            int imageHeight,
            String engineUsed,
            List<String> preprocessingApplied,
            String mediaType,
            int framesAnalyzed,
            Map<String, Object> details) {
        this.totalRegions = totalRegions;
        this.detectedLanguages = detectedLanguages;
        this.imageWidth = imageWidth;
        this.imageHeight = imageHeight;
        this.engineUsed = engineUsed;
        this.preprocessingApplied = preprocessingApplied;
        this.mediaType = mediaType;
        this.framesAnalyzed = framesAnalyzed;
        this.details = details;
    }

    public int getTotalRegions() {
        return totalRegions;
    }

    public void setTotalRegions(int totalRegions) {
        this.totalRegions = totalRegions;
    }

    public List<String> getDetectedLanguages() {
        return detectedLanguages;
    }

    public void setDetectedLanguages(List<String> detectedLanguages) {
        this.detectedLanguages = detectedLanguages;
    }

    public int getImageWidth() {
        return imageWidth;
    }

    public void setImageWidth(int imageWidth) {
        this.imageWidth = imageWidth;
    }

    public int getImageHeight() {
        return imageHeight;
    }

    public void setImageHeight(int imageHeight) {
        this.imageHeight = imageHeight;
    }

    public String getEngineUsed() {
        return engineUsed;
    }

    public void setEngineUsed(String engineUsed) {
        this.engineUsed = engineUsed;
    }

    public List<String> getPreprocessingApplied() {
        return preprocessingApplied;
    }

    public void setPreprocessingApplied(List<String> preprocessingApplied) {
        this.preprocessingApplied = preprocessingApplied;
    }

    public String getMediaType() {
        return mediaType;
    }

    public void setMediaType(String mediaType) {
        this.mediaType = mediaType;
    }

    public int getFramesAnalyzed() {
        return framesAnalyzed;
    }

    public void setFramesAnalyzed(int framesAnalyzed) {
        this.framesAnalyzed = framesAnalyzed;
    }

    public Map<String, Object> getDetails() {
        return details;
    }

    public void setDetails(Map<String, Object> details) {
        this.details = details;
    }
}
