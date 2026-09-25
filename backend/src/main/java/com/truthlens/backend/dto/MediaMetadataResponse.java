package com.truthlens.backend.dto;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * Data transfer object representing the complete metadata forensic record for an ingested media item.
 */
public record MediaMetadataResponse(
        UUID id,
        UUID mediaId,
        String cameraMake,
        String cameraModel,
        String lensModel,
        String softwareTag,
        OffsetDateTime capturedAt,
        OffsetDateTime modifiedAt,
        Double gpsLatitude,
        Double gpsLongitude,
        Double gpsAltitude,
        Integer width,
        Integer height,
        Double durationSeconds,
        Long bitrate,
        Double frameRate,
        String videoCodec,
        String audioCodec,
        Integer audioSampleRate,
        Integer audioChannels,
        String containerFormat,
        List<ForensicAnomalyDto> anomalies,
        boolean hasAnomalies,
        int anomalyCount,
        double forensicScore,
        String riskLevel,
        String extractionEngine,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
}
