package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * Detailed structured forensic evidence for video deepfake analysis.
 */
public record VideoEvidenceDto(
        @JsonProperty("face_count") int faceCount,
        @JsonProperty("total_frames_sampled") int totalFramesSampled,
        @JsonProperty("duration_seconds") double durationSeconds,
        @JsonProperty("frame_scores") List<FrameScoreDto> frameScores,
        @JsonProperty("suspicious_timestamps") List<SuspiciousTimestampDto> suspiciousTimestamps,
        @JsonProperty("details") Map<String, Object> details
) {
}
