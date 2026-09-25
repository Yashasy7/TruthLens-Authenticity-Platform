package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * DTO representing an extracted text region with spatial, confidence, and temporal metadata.
 */
public class OcrTextRegionDto {

    private String text;
    private double confidence;

    @JsonProperty("bounding_box")
    private OcrBoundingBoxDto boundingBox;

    private String language;

    @JsonProperty("frame_index")
    private Integer frameIndex;

    @JsonProperty("timestamp_seconds")
    private Double timestampSeconds;

    @JsonProperty("start_time")
    private Double startTime;

    @JsonProperty("end_time")
    private Double endTime;

    public OcrTextRegionDto() {
    }

    public OcrTextRegionDto(
            String text,
            double confidence,
            OcrBoundingBoxDto boundingBox,
            String language,
            Integer frameIndex,
            Double timestampSeconds,
            Double startTime,
            Double endTime) {
        this.text = text;
        this.confidence = confidence;
        this.boundingBox = boundingBox;
        this.language = language;
        this.frameIndex = frameIndex;
        this.timestampSeconds = timestampSeconds;
        this.startTime = startTime;
        this.endTime = endTime;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public double getConfidence() {
        return confidence;
    }

    public void setConfidence(double confidence) {
        this.confidence = confidence;
    }

    public OcrBoundingBoxDto getBoundingBox() {
        return boundingBox;
    }

    public void setBoundingBox(OcrBoundingBoxDto boundingBox) {
        this.boundingBox = boundingBox;
    }

    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }

    public Integer getFrameIndex() {
        return frameIndex;
    }

    public void setFrameIndex(Integer frameIndex) {
        this.frameIndex = frameIndex;
    }

    public Double getTimestampSeconds() {
        return timestampSeconds;
    }

    public void setTimestampSeconds(Double timestampSeconds) {
        this.timestampSeconds = timestampSeconds;
    }

    public Double getStartTime() {
        return startTime;
    }

    public void setStartTime(Double startTime) {
        this.startTime = startTime;
    }

    public Double getEndTime() {
        return endTime;
    }

    public void setEndTime(Double endTime) {
        this.endTime = endTime;
    }
}
