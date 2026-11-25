package com.truthlens.backend.dto;

import java.io.InputStream;

/**
 * Encapsulates an authorized, streamed resource of quarantined media content
 * along with its content type, original filename, and size.
 */
public record MediaContentResource(
        InputStream inputStream,
        String mimeType,
        String originalFilename,
        long fileSize
) {
}
