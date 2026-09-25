package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Suspected audio splicing transition boundary marker (Module 07).
 */
public record AudioSpliceMarkerDto(
        @JsonProperty("timestamp_seconds") double timestampSeconds,
        @JsonProperty("score") double score,
        @JsonProperty("reason") String reason
) {
}
