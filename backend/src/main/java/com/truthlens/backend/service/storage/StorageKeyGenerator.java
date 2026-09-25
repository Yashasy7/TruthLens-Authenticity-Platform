package com.truthlens.backend.service.storage;

import com.truthlens.backend.entity.MediaType;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.UUID;

/**
 * Generates server-controlled, isolated storage keys for quarantined media.
 *
 * <p>Format: {@code quarantine/<media_type>/<yyyyMMdd>/<uuid>.<extension>}</p>
 * <p>Never uses the client's path or raw filename in the storage path.</p>
 */
@Component
public class StorageKeyGenerator {

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.BASIC_ISO_DATE; // yyyyMMdd

    private static final Map<String, String> MIME_TO_EXTENSION = Map.ofEntries(
            // Image
            Map.entry("image/jpeg", "jpg"),
            Map.entry("image/png", "png"),
            Map.entry("image/webp", "webp"),
            Map.entry("image/gif", "gif"),
            Map.entry("image/bmp", "bmp"),
            Map.entry("image/tiff", "tiff"),
            // Video
            Map.entry("video/mp4", "mp4"),
            Map.entry("video/quicktime", "mov"),
            Map.entry("video/x-msvideo", "avi"),
            Map.entry("video/webm", "webm"),
            Map.entry("video/x-matroska", "mkv"),
            // Audio
            Map.entry("audio/mpeg", "mp3"),
            Map.entry("audio/wav", "wav"),
            Map.entry("audio/x-wav", "wav"),
            Map.entry("audio/ogg", "ogg"),
            Map.entry("audio/flac", "flac"),
            Map.entry("audio/x-m4a", "m4a"),
            Map.entry("audio/aac", "aac"),
            // Text
            Map.entry("text/plain", "txt"),
            Map.entry("text/csv", "csv"),
            Map.entry("text/html", "html"),
            Map.entry("application/json", "json"),
            Map.entry("application/pdf", "pdf")
    );

    /**
     * Generates a safe storage key.
     *
     * @param mediaType the validated TruthLens media category
     * @param mimeType  the validated MIME type
     * @return a safe relative path string
     */
    public String generateKey(MediaType mediaType, String mimeType) {
        String datePartition = LocalDate.now().format(DATE_FORMATTER);
        String uuid = UUID.randomUUID().toString();
        String extension = resolveExtension(mimeType);

        String categoryFolder = mediaType != null ? mediaType.name().toLowerCase() : "unknown";

        return String.format("quarantine/%s/%s/%s.%s", categoryFolder, datePartition, uuid, extension);
    }

    private String resolveExtension(String mimeType) {
        if (mimeType == null) {
            return "bin";
        }
        String cleanMime = mimeType.toLowerCase().trim();
        int semicolon = cleanMime.indexOf(';');
        if (semicolon != -1) {
            cleanMime = cleanMime.substring(0, semicolon).trim();
        }
        return MIME_TO_EXTENSION.getOrDefault(cleanMime, "bin");
    }
}
