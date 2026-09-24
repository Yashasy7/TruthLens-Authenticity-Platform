package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.ArrayList;
import java.util.List;

/**
 * Data transfer object mapping the JSON response from FastAPI {@code /api/v1/analyze/av-sync}.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FastApiAvSyncResponse {

    @JsonProperty("sync_score")
    private double syncScore;

    @JsonProperty("lip_offset_ms")
    private double lipOffsetMs;

    @JsonProperty("confidence")
    private double confidence;

    @JsonProperty("mismatch_segments")
    private List<MismatchSegmentDto> mismatchSegments = new ArrayList<>();

    @JsonProperty("model_name")
    private String modelName;

    @JsonProperty("model_version")
    private String modelVersion;

    @JsonProperty("evidence")
    private AvSyncEvidenceDto evidence;

    @JsonProperty("status")
    private String status = "COMPLETED";

    public FastApiAvSyncResponse() {
    }

    public double getSyncScore() {
        return syncScore;
    }

    public void setSyncScore(double syncScore) {
        this.syncScore = syncScore;
    }

    public double getLipOffsetMs() {
        return lipOffsetMs;
    }

    public void setLipOffsetMs(double lipOffsetMs) {
        this.lipOffsetMs = lipOffsetMs;
    }

    public double getConfidence() {
        return confidence;
    }

    public void setConfidence(double confidence) {
        this.confidence = confidence;
    }

    public List<MismatchSegmentDto> getMismatchSegments() {
        return mismatchSegments;
    }

    public void setMismatchSegments(List<MismatchSegmentDto> mismatchSegments) {
        this.mismatchSegments = mismatchSegments;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
    }

    public AvSyncEvidenceDto getEvidence() {
        return evidence;
    }

    public void setEvidence(AvSyncEvidenceDto evidence) {
        this.evidence = evidence;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
