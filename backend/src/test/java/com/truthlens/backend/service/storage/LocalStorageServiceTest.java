package com.truthlens.backend.service.storage;

import com.truthlens.backend.exception.StorageException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DisplayName("LocalStorageService — Quarantined Storage Tests")
class LocalStorageServiceTest {

    @TempDir
    Path tempDir;

    private LocalStorageService storageService;

    @BeforeEach
    void setUp() {
        storageService = new LocalStorageService(tempDir.toString());
    }

    @Test
    @DisplayName("Stores and loads media file successfully in quarantine")
    void storeAndLoad_validInput_success() throws Exception {
        String key = "quarantine/image/20260919/test-uuid.jpg";
        byte[] data = "mock-image-data".getBytes(StandardCharsets.UTF_8);

        String savedKey = storageService.store(new ByteArrayInputStream(data), key, "image/jpeg", data.length);
        assertThat(savedKey).isEqualTo(key);
        assertThat(storageService.exists(key)).isTrue();

        try (InputStream loaded = storageService.load(key)) {
            byte[] loadedBytes = loaded.readAllBytes();
            assertThat(loadedBytes).isEqualTo(data);
        }
    }

    @Test
    @DisplayName("Deletes quarantined file successfully")
    void delete_existingFile_removesFile() {
        String key = "quarantine/text/20260919/doc.txt";
        byte[] data = "sample text".getBytes(StandardCharsets.UTF_8);

        storageService.store(new ByteArrayInputStream(data), key, "text/plain", data.length);
        assertThat(storageService.exists(key)).isTrue();

        storageService.delete(key);
        assertThat(storageService.exists(key)).isFalse();
    }

    @Test
    @DisplayName("Rejects path traversal attempts escaping quarantine root")
    void store_pathTraversal_throwsStorageException() {
        String dangerousKey = "../../secret_system_file.txt";
        byte[] data = "malicious payload".getBytes(StandardCharsets.UTF_8);

        assertThatThrownBy(() -> storageService.store(new ByteArrayInputStream(data), dangerousKey, "text/plain", data.length))
                .isInstanceOf(StorageException.class)
                .hasMessageContaining("Path traversal");
    }

    @Test
    @DisplayName("Throws StorageException when loading non-existent file")
    void load_nonExistent_throwsStorageException() {
        assertThatThrownBy(() -> storageService.load("quarantine/non-existent.png"))
                .isInstanceOf(StorageException.class)
                .hasMessageContaining("not found");
    }
}
