package com.truthlens.backend.dto;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Client-safe representation of duplicate detection details.
 *
 * <p>Preserves privacy across users by masking sensitive uploader identity,
 * storage keys, and internal accounts while providing verified match provenance.</p>
 */
public record DuplicateDetailResponse(
        UUID mediaId,
        boolean isDuplicate,
        String matchType,
        Double similarityScore,
        UUID duplicateOfMediaId,
        String duplicateOfFilename,
        OffsetDateTime detectedAt
) {
}
