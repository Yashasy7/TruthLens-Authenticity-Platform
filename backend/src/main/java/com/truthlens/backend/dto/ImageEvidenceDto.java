package com.truthlens.backend.dto;

import java.util.Map;

/**
 * Structured explainable forensic evidence DTO for image authenticity analysis.
 */
public record ImageEvidenceDto(
        Double noiseVariance,
        Double noiseInconsistencyScore,
        Double fftAnomalyScore,
        boolean copyMoveDetected,
        boolean splicingDetected,
        Integer imageWidth,
        Integer imageHeight,
        Map<String, Object> details
) {
}
