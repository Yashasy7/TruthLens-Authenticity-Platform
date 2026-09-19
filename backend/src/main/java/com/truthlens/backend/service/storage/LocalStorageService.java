package com.truthlens.backend.service.storage;

import com.truthlens.backend.exception.StorageException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;

/**
 * Local filesystem implementation of {@link StorageService} providing
 * quarantined media isolation with strict path traversal protection.
 */
@Service
public class LocalStorageService implements StorageService {

    private static final Logger log = LoggerFactory.getLogger(LocalStorageService.class);

    private final Path rootLocation;

    public LocalStorageService(@Value("${truthlens.storage.quarantine-dir:./storage/quarantine}") String quarantineDir) {
        this.rootLocation = Paths.get(quarantineDir).toAbsolutePath().normalize();
        init();
    }

    private void init() {
        try {
            Files.createDirectories(rootLocation);
            log.info("Initialized local quarantined storage directory at: {}", rootLocation);
        } catch (IOException e) {
            throw new StorageException("Failed to initialize quarantined storage directory: " + rootLocation, e);
        }
    }

    @Override
    public String store(InputStream inputStream, String storageKey, String contentType, long size) {
        if (storageKey == null || storageKey.isBlank()) {
            throw new StorageException("Storage key must not be null or blank");
        }

        Path destinationPath = resolveAndVerifyPath(storageKey);

        try {
            Path parentDir = destinationPath.getParent();
            if (parentDir != null && !Files.exists(parentDir)) {
                Files.createDirectories(parentDir);
            }

            Files.copy(inputStream, destinationPath, StandardCopyOption.REPLACE_EXISTING);
            log.debug("Stored media file at relative key: {}", storageKey);
            return storageKey;
        } catch (IOException e) {
            throw new StorageException("Failed to store media file in quarantine: " + storageKey, e);
        }
    }

    @Override
    public InputStream load(String storageKey) {
        Path path = resolveAndVerifyPath(storageKey);
        if (!Files.exists(path) || !Files.isReadable(path)) {
            throw new StorageException("Quarantined media file not found or not readable: " + storageKey);
        }

        try {
            return Files.newInputStream(path);
        } catch (IOException e) {
            throw new StorageException("Failed to read quarantined media file: " + storageKey, e);
        }
    }

    @Override
    public void delete(String storageKey) {
        if (storageKey == null || storageKey.isBlank()) {
            return;
        }

        try {
            Path path = resolveAndVerifyPath(storageKey);
            boolean deleted = Files.deleteIfExists(path);
            if (deleted) {
                log.debug("Deleted quarantined file: {}", storageKey);
            }
        } catch (Exception e) {
            log.warn("Failed to delete quarantined media file: {} - {}", storageKey, e.getMessage());
        }
    }

    @Override
    public boolean exists(String storageKey) {
        if (storageKey == null || storageKey.isBlank()) {
            return false;
        }
        try {
            Path path = resolveAndVerifyPath(storageKey);
            return Files.exists(path);
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * Resolves the storage key against the quarantined root and verifies that
     * the path does not escape the root directory (path traversal defense).
     */
    private Path resolveAndVerifyPath(String storageKey) {
        // Strip any leading slashes/backslashes
        String cleanKey = storageKey.replaceAll("^[\\\\/]+", "");
        Path resolved = rootLocation.resolve(cleanKey).normalize();

        if (!resolved.startsWith(rootLocation)) {
            log.error("Path traversal attempt detected with key: {}", storageKey);
            throw new StorageException("Path traversal attempt detected in storage key");
        }

        return resolved;
    }
}
