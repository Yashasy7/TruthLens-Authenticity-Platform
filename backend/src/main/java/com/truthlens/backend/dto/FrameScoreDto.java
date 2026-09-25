package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * DTO representing granular forensic evaluation metrics for a single sampled video frame.
 */
public record FrameScoreDto(
        @JsonProperty("frame_index") int frameIndex,
        @JsonProperty("timestamp_seconds") double timestampSeconds,
        @JsonProperty("deepfake_score") double deepfakeScore,
        @JsonProperty("temporal_inconsistency") double temporalInconsistency,
        @JsonProperty("faces_detected") int facesDetected,
        @JsonProperty("is_suspicious") boolean isSuspicious
) {
}
