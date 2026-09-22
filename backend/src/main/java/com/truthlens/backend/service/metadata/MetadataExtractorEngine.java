package com.truthlens.backend.service.metadata;

import java.io.InputStream;

/**
 * Interface defining a metadata extraction engine capable of reading EXIF, IPTC, XMP,
 * container headers, and multimedia stream properties from an input stream.
 */
public interface MetadataExtractorEngine {

    /**
     * Extracts normalized metadata and raw directory trees from the media stream.
     *
     * @param inputStream data stream of the media asset
     * @param filename    the original or sanitized filename
     * @param mimeType    the detected MIME type of the media
     * @return populated {@link ExtractedMetadata}
     */
    ExtractedMetadata extract(InputStream inputStream, String filename, String mimeType);

    /**
     * Returns true if this engine is available and functional in the current environment.
     *
     * @return availability flag
     */
    boolean isAvailable();

    /**
     * Returns the identifying name of the extraction engine.
     *
     * @return engine name
     */
    String getEngineName();
}
