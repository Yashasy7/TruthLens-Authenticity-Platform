package com.truthlens.backend.dto;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * Data transfer object representing a forensic anomaly evaluation report.
 */
public record MetadataAnomalyReportResponse(
        UUID mediaId,
        boolean hasAnomalies,
        int anomalyCount,
        double forensicScore,
        String riskLevel,
        List<ForensicAnomalyDto> anomalies,
        String summary,
        OffsetDateTime evaluatedAt
) {
}
