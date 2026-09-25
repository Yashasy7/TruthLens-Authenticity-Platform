package com.truthlens.backend.service.validation;

import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.exception.FileSizeExceededException;
import com.truthlens.backend.exception.InvalidMediaException;
import org.apache.tika.Tika;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * Service responsible for validating uploaded files using Apache Tika magic-byte detection.
 *
 * <p>Enforces:</p>
 * <ul>
 *   <li>Presence and non-empty content.</li>
 *   <li>Maximum file size limits.</li>
 *   <li>Magic-byte content inspection (does not trust client-supplied Content-Type header).</li>
 *   <li>Mapping to TruthLens {@link MediaType} (IMAGE, VIDEO, AUDIO, TEXT).</li>
 *   <li>Filename sanitization to protect against path traversal and injection.</li>
 * </ul>
 */
@Service
public class MediaValidationService {

    private static final Logger log = LoggerFactory.getLogger(MediaValidationService.class);

    private final Tika tika;
    private final long maxFileSizeBytes;

    private static final Map<String, MediaType> MIME_TO_MEDIA_TYPE;

    static {
        Map<String, MediaType> map = new HashMap<>();

        // Image types
        Set.of(
                "image/jpeg",
                "image/png",
                "image/webp",
                "image/gif",
                "image/bmp",
                "image/tiff",
                "image/x-ms-bmp"
        ).forEach(mime -> map.put(mime, MediaType.IMAGE));

        // Video types
        Set.of(
                "video/mp4",
                "video/quicktime",
                "video/x-msvideo",
                "video/webm",
                "video/x-matroska",
                "video/mpeg"
        ).forEach(mime -> map.put(mime, MediaType.VIDEO));

        // Audio types
        Set.of(
                "audio/mpeg",
                "audio/mp3",
                "audio/wav",
                "audio/x-wav",
                "audio/ogg",
                "audio/flac",
                "audio/x-flac",
                "audio/x-m4a",
                "audio/mp4",
                "audio/aac",
                "audio/x-aiff"
        ).forEach(mime -> map.put(mime, MediaType.AUDIO));

        // Text / Document types
        Set.of(
                "text/plain",
                "text/csv",
                "text/tab-separated-values",
                "application/json",
                "application/pdf"
        ).forEach(mime -> map.put(mime, MediaType.TEXT));

        MIME_TO_MEDIA_TYPE = Collections.unmodifiableMap(map);
    }

    public MediaValidationService(
            @Value("${truthlens.media.max-file-size-bytes:104857600}") long maxFileSizeBytes) {
        this.tika = new Tika();
        this.maxFileSizeBytes = maxFileSizeBytes;
    }

    /**
     * Validates a multipart file and returns verified metadata.
     *
     * @param file the uploaded multipart file
     * @return {@link ValidationResult} with verified media category and MIME type
     */
    public ValidationResult validate(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new InvalidMediaException("Upload rejected: File is missing or empty");
        }

        long size = file.getSize();
        if (size <= 0) {
            throw new InvalidMediaException("Upload rejected: File size is 0 bytes");
        }

        if (size > maxFileSizeBytes) {
            log.warn("Upload rejected: File size ({} bytes) exceeds maximum limit ({} bytes)",
                    size, maxFileSizeBytes);
            throw new FileSizeExceededException(String.format(
                    "Upload rejected: File size (%d bytes) exceeds maximum limit of %d bytes",
                    size, maxFileSizeBytes));
        }

        String rawFilename = file.getOriginalFilename();
        String sanitizedFilename = sanitizeFilename(rawFilename);

        // Detect real MIME type using Apache Tika magic bytes
        String detectedMimeType = detectMimeType(file, sanitizedFilename);
        log.debug("Detected MIME type for '{}': {}", sanitizedFilename, detectedMimeType);

        MediaType mediaType = MIME_TO_MEDIA_TYPE.get(detectedMimeType.toLowerCase());
        if (mediaType == null) {
            log.warn("Upload rejected: Unsupported MIME type '{}' for file '{}'",
                    detectedMimeType, sanitizedFilename);
            throw new InvalidMediaException(String.format(
                    "Unsupported file format: '%s'. Supported categories: IMAGE, VIDEO, AUDIO, TEXT.",
                    detectedMimeType));
        }

        return new ValidationResult(mediaType, detectedMimeType, sanitizedFilename, size);
    }

    /**
     * Detects MIME type by inspecting magic bytes of the file stream.
     */
    public String detectMimeType(MultipartFile file, String filename) {
        try (InputStream is = new BufferedInputStream(file.getInputStream())) {
            // Tika inspects magic bytes from the stream, using filename as a secondary hint
            String detected = tika.detect(is, filename);
            if (detected == null || detected.isBlank()) {
                throw new InvalidMediaException("Unable to detect media content type");
            }
            // Strip any parameters (e.g. text/plain; charset=ISO-8859-1 -> text/plain)
            int semicolon = detected.indexOf(';');
            if (semicolon != -1) {
                detected = detected.substring(0, semicolon).trim();
            }
            return detected.toLowerCase();
        } catch (IOException e) {
            throw new InvalidMediaException("Failed to read file content for MIME validation", e);
        }
    }

    /**
     * Sanitizes original filename to prevent path traversal and shell injection.
     */
    public String sanitizeFilename(String filename) {
        if (filename == null || filename.isBlank()) {
            return "unnamed_upload";
        }

        // 1. Remove null bytes and control characters first
        String clean = filename.replaceAll("[\\x00-\\x1F\\x7F]", "");

        // 2. Strip any directory paths (both Unix and Windows separators)
        int lastUnixSlash = clean.lastIndexOf('/');
        if (lastUnixSlash != -1) {
            clean = clean.substring(lastUnixSlash + 1);
        }
        int lastWinSlash = clean.lastIndexOf('\\');
        if (lastWinSlash != -1) {
            clean = clean.substring(lastWinSlash + 1);
        }

        // 3. Remove dangerous characters: / \ : * ? " < > |
        clean = clean.replaceAll("[/\\\\:*?\"<>|]", "_");

        // 4. Trim whitespace
        clean = clean.trim();

        if (clean.isEmpty() || clean.equals(".") || clean.equals("..")) {
            return "unnamed_upload";
        }

        // Limit length to 255 chars
        if (clean.length() > 255) {
            int extIndex = clean.lastIndexOf('.');
            if (extIndex > 0 && extIndex > clean.length() - 10) {
                String ext = clean.substring(extIndex);
                clean = clean.substring(0, 255 - ext.length()) + ext;
            } else {
                clean = clean.substring(0, 255);
            }
        }

        return clean;
    }

    /**
     * Encapsulates the output of a successful file validation.
     */
    public record ValidationResult(
            MediaType mediaType,
            String mimeType,
            String sanitizedFilename,
            long fileSize
    ) {}
}
