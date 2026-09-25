package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Data transfer object representing a localized temporal mismatch segment (Module 08).
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class MismatchSegmentDto {

    @JsonProperty("start_time")
    private double startTime;

    @JsonProperty("end_time")
    private double endTime;

    @JsonProperty("offset_ms")
    private double offsetMs;

    @JsonProperty("confidence")
    private double confidence;

    @JsonProperty("reason")
    private String reason;

    public MismatchSegmentDto() {
    }

    public MismatchSegmentDto(double startTime, double endTime, double offsetMs, double confidence, String reason) {
        this.startTime = startTime;
        this.endTime = endTime;
        this.offsetMs = offsetMs;
        this.confidence = confidence;
        this.reason = reason;
    }

    public double getStartTime() {
        return startTime;
    }

    public void setStartTime(double startTime) {
        this.startTime = startTime;
    }

    public double getEndTime() {
        return endTime;
    }

    public void setEndTime(double endTime) {
        this.endTime = endTime;
    }

    public double getOffsetMs() {
        return offsetMs;
    }

    public void setOffsetMs(double offsetMs) {
        this.offsetMs = offsetMs;
    }

    public double getConfidence() {
        return confidence;
    }

    public void setConfidence(double confidence) {
        this.confidence = confidence;
    }

    public String getReason() {
        return reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }

    @Override
    public String toString() {
        return "MismatchSegmentDto{" +
                "startTime=" + startTime +
                ", endTime=" + endTime +
                ", offsetMs=" + offsetMs +
                ", confidence=" + confidence +
                ", reason='" + reason + '\'' +
                '}';
    }
}
