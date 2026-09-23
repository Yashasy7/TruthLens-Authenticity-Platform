package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * Granular acoustic evidence metrics for audio authenticity analysis (Module 07).
 */
public record AudioEvidenceDto(
        @JsonProperty("duration_seconds") double durationSeconds,
        @JsonProperty("pitch_mean") double pitchMean,
        @JsonProperty("pitch_variance") double pitchVariance,
        @JsonProperty("spectral_centroid_mean") double spectralCentroidMean,
        @JsonProperty("spectral_bandwidth_mean") double spectralBandwidthMean,
        @JsonProperty("spectral_rolloff_mean") double spectralRolloffMean,
        @JsonProperty("zero_crossing_rate_mean") double zeroCrossingRateMean,
        @JsonProperty("phase_discontinuity_score") double phaseDiscontinuityScore,
        @JsonProperty("splice_markers") List<AudioSpliceMarkerDto> spliceMarkers,
        @JsonProperty("details") Map<String, Object> details
) {
}
