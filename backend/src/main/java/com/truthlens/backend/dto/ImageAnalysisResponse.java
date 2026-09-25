package com.truthlens.backend.dto;

import com.truthlens.backend.entity.AnalysisStatus;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * REST response DTO for image authenticity analysis (Module 05).
 */
public record ImageAnalysisResponse(
        UUID id,
        UUID mediaId,
        double aiProb,
        double manipulationProb,
        String authenticityAssessment,
        String elaHeatmapUrl,
        String gradcamHeatmapUrl,
        Double noiseVariance,
        Double fftAnomalyScore,
        boolean copyMoveDetected,
        boolean splicingDetected,
        AnalysisStatus analysisStatus,
        String modelVersion,
        ImageEvidenceDto evidence,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
}
