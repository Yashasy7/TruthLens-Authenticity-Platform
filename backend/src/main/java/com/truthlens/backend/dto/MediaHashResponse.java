package com.truthlens.backend.dto;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Client-safe representation of a media fingerprint record.
 */
public record MediaHashResponse(
        UUID id,
        UUID mediaId,
        String sha256Hash,
        String phash,
        String chromaprint,
        boolean isDuplicate,
        UUID duplicateOfMediaId,
        Double similarityScore,
        String matchType,
        OffsetDateTime createdAt
) {
}
