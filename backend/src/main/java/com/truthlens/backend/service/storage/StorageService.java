package com.truthlens.backend.service.storage;

import java.io.InputStream;

/**
 * Storage service abstraction for quarantined media files in TruthLens.
 *
 * <p>Decouples the ingestion layer from the underlying storage mechanism
 * (e.g. local disk quarantine or MinIO/S3 object storage).</p>
 */
public interface StorageService {

    /**
     * Stores an input stream in quarantined storage at the specified key.
     *
     * @param inputStream the data stream to store
     * @param storageKey  the relative storage identifier / object key
     * @param contentType the MIME type of the content
     * @param size        expected size in bytes
     * @return the resolved storage key / reference
     */
    String store(InputStream inputStream, String storageKey, String contentType, long size);

    /**
     * Loads a stored media object as an input stream.
     *
     * @param storageKey the storage identifier / object key
     * @return InputStream to read the media content
     */
    InputStream load(String storageKey);

    /**
     * Deletes a stored media object from quarantined storage.
     * Typically used for compensating cleanup if database persistence fails.
     *
     * @param storageKey the storage identifier / object key
     */
    void delete(String storageKey);

    /**
     * Checks if a stored object exists.
     *
     * @param storageKey the storage identifier / object key
     * @return true if the object exists in storage
     */
    boolean exists(String storageKey);
}
