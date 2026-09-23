package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Payload mapping the JSON response from internal FastAPI Video Service (Module 06).
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FastApiVideoAnalysisResponse {

    @JsonProperty("deepfake_prob")
    private double deepfakeProb;

    @JsonProperty("face_count")
    private int faceCount;

    @JsonProperty("total_frames_sampled")
    private int totalFramesSampled;

    @JsonProperty("suspicious_timestamps")
    private List<SuspiciousTimestampDto> suspiciousTimestamps;

    @JsonProperty("frame_scores")
    private List<FrameScoreDto> frameScores;

    @JsonProperty("model_name")
    private String modelName;

    @JsonProperty("model_version")
    private String modelVersion;

    @JsonProperty("evidence")
    private VideoEvidenceDto evidence;

    @JsonProperty("status")
    private String status;

    public FastApiVideoAnalysisResponse() {
    }

    public FastApiVideoAnalysisResponse(
            double deepfakeProb,
            int faceCount,
            int totalFramesSampled,
            List<SuspiciousTimestampDto> suspiciousTimestamps,
            List<FrameScoreDto> frameScores,
            String modelName,
            String modelVersion,
            VideoEvidenceDto evidence,
            String status) {
        this.deepfakeProb = deepfakeProb;
        this.faceCount = faceCount;
        this.totalFramesSampled = totalFramesSampled;
        this.suspiciousTimestamps = suspiciousTimestamps;
        this.frameScores = frameScores;
        this.modelName = modelName;
        this.modelVersion = modelVersion;
        this.evidence = evidence;
        this.status = status;
    }

    public double getDeepfakeProb() {
        return deepfakeProb;
    }

    public void setDeepfakeProb(double deepfakeProb) {
        this.deepfakeProb = deepfakeProb;
    }

    public int getFaceCount() {
        return faceCount;
    }

    public void setFaceCount(int faceCount) {
        this.faceCount = faceCount;
    }

    public int getTotalFramesSampled() {
        return totalFramesSampled;
    }

    public void setTotalFramesSampled(int totalFramesSampled) {
        this.totalFramesSampled = totalFramesSampled;
    }

    public List<SuspiciousTimestampDto> getSuspiciousTimestamps() {
        return suspiciousTimestamps;
    }

    public void setSuspiciousTimestamps(List<SuspiciousTimestampDto> suspiciousTimestamps) {
        this.suspiciousTimestamps = suspiciousTimestamps;
    }

    public List<FrameScoreDto> getFrameScores() {
        return frameScores;
    }

    public void setFrameScores(List<FrameScoreDto> frameScores) {
        this.frameScores = frameScores;
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

    public VideoEvidenceDto getEvidence() {
        return evidence;
    }

    public void setEvidence(VideoEvidenceDto evidence) {
        this.evidence = evidence;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
