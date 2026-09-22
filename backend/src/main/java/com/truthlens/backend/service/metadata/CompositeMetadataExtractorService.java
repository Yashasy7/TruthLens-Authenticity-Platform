package com.truthlens.backend.service.metadata;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;

/**
 * Composite metadata extraction service that orchestrates engine execution.
 *
 * <p>Attempts CLI extraction (ExifTool / MediaInfo) if available on the host, and
 * deterministically falls back to the robust built-in {@link JavaMetadataExtractorEngine}.
 * Ensures incoming streams are buffered so fallback never encounters an exhausted stream (FINDING-04-01).</p>
 */
@Service
public class CompositeMetadataExtractorService {

    private static final Logger log = LoggerFactory.getLogger(CompositeMetadataExtractorService.class);

    /**
     * Maximum in-memory buffer for composite stream processing (25 MB).
     * Prevents unbounded heap allocation while comfortably accommodating supported media uploads.
     */
    public static final int MAX_BUFFER_SIZE_BYTES = 25 * 1024 * 1024;

    private final JavaMetadataExtractorEngine javaEngine;
    private final CliMetadataExtractorEngine cliEngine;

    public CompositeMetadataExtractorService(JavaMetadataExtractorEngine javaEngine,
                                            CliMetadataExtractorEngine cliEngine) {
        this.javaEngine = javaEngine;
        this.cliEngine = cliEngine;
    }

    /**
     * Extracts forensic metadata from the media stream using the best available engine.
     * Guarantees that CLI failures or incomplete results fall back to the Java engine
     * with a fresh, unexhausted stream.
     *
     * @param inputStream media data stream
     * @param filename    original filename
     * @param mimeType    MIME type of the media
     * @return populated {@link ExtractedMetadata}
     */
    public ExtractedMetadata extractMetadata(InputStream inputStream, String filename, String mimeType) {
        if (inputStream == null) {
            return new ExtractedMetadata();
        }

        // Fast path: if CLI tools are not available on the host, stream directly to Java engine
        if (!cliEngine.isAvailable()) {
            log.debug("CLI engine unavailable; delegating directly to Java metadata extractor for '{}'", filename);
            return javaEngine.extract(inputStream, filename, mimeType);
        }

        // Buffer the stream up to MAX_BUFFER_SIZE_BYTES so both CLI and fallback Java engines
        // receive complete, unexhausted data without unbounded heap allocation (FINDING-04-01).
        byte[] payload;
        try {
            payload = inputStream.readNBytes(MAX_BUFFER_SIZE_BYTES + 1);
            if (payload.length > MAX_BUFFER_SIZE_BYTES) {
                log.warn("Media stream for '{}' exceeds maximum composite buffer size of {} bytes; metadata extraction aborted",
                        filename, MAX_BUFFER_SIZE_BYTES);
                return new ExtractedMetadata();
            }
        } catch (IOException e) {
            log.warn("Failed to buffer stream for metadata extraction of '{}': {}", filename, e.getMessage());
            return new ExtractedMetadata();
        }

        try {
            log.debug("Attempting CLI metadata extraction for '{}'", filename);
            ExtractedMetadata cliResult = cliEngine.extract(new ByteArrayInputStream(payload), filename, mimeType);
            if (cliResult != null && isUsableResult(cliResult)) {
                return cliResult;
            }
            log.debug("CLI extraction returned incomplete metadata for '{}'; falling back to Java engine", filename);
        } catch (Exception e) {
            log.warn("CLI metadata extraction threw exception for '{}', falling back to Java engine: {}",
                    filename, e.getMessage());
        }

        // Deterministic fallback with fresh ByteArrayInputStream
        log.debug("Executing Java metadata extractor fallback for '{}'", filename);
        return javaEngine.extract(new ByteArrayInputStream(payload), filename, mimeType);
    }

    /**
     * Checks if the CLI result contains substantive metadata worth returning.
     */
    private boolean isUsableResult(ExtractedMetadata result) {
        return result.isExifPresent()
                || result.getWidth() != null
                || result.getDurationSeconds() != null
                || result.getAudioSampleRate() != null
                || (result.getRawMetadataTree() != null && !result.getRawMetadataTree().isEmpty());
    }

    /**
     * Returns the active primary engine name.
     *
     * @return engine name
     */
    public String getActiveEngineName() {
        return cliEngine.isAvailable() ? cliEngine.getEngineName() : javaEngine.getEngineName();
    }
}
