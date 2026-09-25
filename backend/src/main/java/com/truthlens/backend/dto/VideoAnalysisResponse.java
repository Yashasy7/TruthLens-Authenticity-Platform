package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.truthlens.backend.entity.AnalysisStatus;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * Standard public REST response for video deepfake & forensic authenticity queries (Module 06).
 */
public record VideoAnalysisResponse(
        @JsonProperty("id") UUID id,
        @JsonProperty("media_id") UUID mediaId,
        @JsonProperty("deepfake_prob") double deepfakeProb,
        @JsonProperty("face_count") int faceCount,
        @JsonProperty("total_frames_sampled") int totalFramesSampled,
        @JsonProperty("authenticity_assessment") String authenticityAssessment,
        @JsonProperty("analysis_status") AnalysisStatus analysisStatus,
        @JsonProperty("model_version") String modelVersion,
        @JsonProperty("suspicious_timestamps") List<SuspiciousTimestampDto> suspiciousTimestamps,
        @JsonProperty("evidence") VideoEvidenceDto evidence,
        @JsonProperty("created_at") OffsetDateTime createdAt,
        @JsonProperty("updated_at") OffsetDateTime updatedAt
) {
}
