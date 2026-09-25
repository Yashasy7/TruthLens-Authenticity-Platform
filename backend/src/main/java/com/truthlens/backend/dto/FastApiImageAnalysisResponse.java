package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * Internal DTO mapping the FastAPI service response payload.
 */
public record FastApiImageAnalysisResponse(
        @JsonProperty("ai_prob") double aiProb,
        @JsonProperty("manipulation_prob") double manipulationProb,
        @JsonProperty("noise_variance") Double noiseVariance,
        @JsonProperty("fft_anomaly_score") Double fftAnomalyScore,
        @JsonProperty("copy_move_detected") boolean copyMoveDetected,
        @JsonProperty("splicing_detected") boolean splicingDetected,
        @JsonProperty("model_name") String modelName,
        @JsonProperty("model_version") String modelVersion,
        @JsonProperty("ela_heatmap_base64") String elaHeatmapBase64,
        @JsonProperty("gradcam_heatmap_base64") String gradcamHeatmapBase64,
        @JsonProperty("evidence") Map<String, Object> evidence,
        @JsonProperty("status") String status
) {

    public double getAiProb() {
        return aiProb;
    }

    public double getManipulationProb() {
        return manipulationProb;
    }

    public Double getNoiseVariance() {
        return noiseVariance;
    }

    public Double getFftAnomalyScore() {
        return fftAnomalyScore;
    }

    public boolean isCopyMoveDetected() {
        return copyMoveDetected;
    }

    public boolean isSplicingDetected() {
        return splicingDetected;
    }

    public String getModelName() {
        return modelName;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public String getElaHeatmapBase64() {
        return elaHeatmapBase64;
    }

    public String getGradcamHeatmapBase64() {
        return gradcamHeatmapBase64;
    }

    public Map<String, Object> getEvidence() {
        return evidence;
    }

    public String getStatus() {
        return status;
    }
}
