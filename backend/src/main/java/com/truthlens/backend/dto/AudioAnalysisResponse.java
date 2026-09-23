package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.truthlens.backend.entity.AnalysisStatus;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * Standard public REST response for audio authenticity & voice forensics queries (Module 07).
 */
public record AudioAnalysisResponse(
        @JsonProperty("id") UUID id,
        @JsonProperty("media_id") UUID mediaId,
        @JsonProperty("synthetic_voice_prob") double syntheticVoiceProb,
        @JsonProperty("spectrogram_url") String spectrogramUrl,
        @JsonProperty("spectrogram_base64") String spectrogramBase64,
        @JsonProperty("pitch_variance") double pitchVariance,
        @JsonProperty("phase_discontinuity") double phaseDiscontinuity,
        @JsonProperty("authenticity_assessment") String authenticityAssessment,
        @JsonProperty("analysis_status") AnalysisStatus analysisStatus,
        @JsonProperty("model_name") String modelName,
        @JsonProperty("model_version") String modelVersion,
        @JsonProperty("splice_markers") List<AudioSpliceMarkerDto> spliceMarkers,
        @JsonProperty("evidence") AudioEvidenceDto evidence,
        @JsonProperty("created_at") OffsetDateTime createdAt,
        @JsonProperty("updated_at") OffsetDateTime updatedAt
) {
}
