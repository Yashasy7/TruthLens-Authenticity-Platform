package com.truthlens.backend.dto;

/**
 * Data transfer object representing an individual forensic anomaly or indicator
 * detected during metadata forensic evaluation.
 */
public record ForensicAnomalyDto(
        String ruleId,
        String category,
        String severity,
        String title,
        String description,
        String evidence,
        Double confidence,
        Double scoreImpact
) {
}
