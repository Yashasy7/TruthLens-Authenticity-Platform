package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * DTO representing an anomalous or suspicious timestamp in a video timeline.
 */
public record SuspiciousTimestampDto(
        @JsonProperty("timestamp_seconds") double timestampSeconds,
        @JsonProperty("frame_index") int frameIndex,
        @JsonProperty("score") double score,
        @JsonProperty("reason") String reason
) {
}
