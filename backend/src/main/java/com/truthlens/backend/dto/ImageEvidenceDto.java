package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.Map;

/**
 * Structured explainable forensic evidence DTO for image authenticity analysis.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
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
