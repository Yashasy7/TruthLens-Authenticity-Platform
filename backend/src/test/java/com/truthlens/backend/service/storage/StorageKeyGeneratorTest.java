package com.truthlens.backend.service.storage;

import com.truthlens.backend.entity.MediaType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("StorageKeyGenerator — Storage Key Tests")
class StorageKeyGeneratorTest {

    private StorageKeyGenerator generator;

    @BeforeEach
    void setUp() {
        generator = new StorageKeyGenerator();
    }

    @Test
    @DisplayName("Generates correct quarantined storage key for JPEG image")
    void generateKey_imageJpeg_matchesExpectedFormat() {
        String key = generator.generateKey(MediaType.IMAGE, "image/jpeg");

        assertThat(key).startsWith("quarantine/image/");
        assertThat(key).endsWith(".jpg");
        assertThat(key.split("/")).hasSize(4);
    }

    @Test
    @DisplayName("Generates correct quarantined storage key for MP4 video")
    void generateKey_videoMp4_matchesExpectedFormat() {
        String key = generator.generateKey(MediaType.VIDEO, "video/mp4");

        assertThat(key).startsWith("quarantine/video/");
        assertThat(key).endsWith(".mp4");
    }

    @Test
    @DisplayName("Generates correct quarantined storage key for MP3 audio")
    void generateKey_audioMp3_matchesExpectedFormat() {
        String key = generator.generateKey(MediaType.AUDIO, "audio/mpeg");

        assertThat(key).startsWith("quarantine/audio/");
        assertThat(key).endsWith(".mp3");
    }

    @Test
    @DisplayName("Generates correct quarantined storage key for PDF text")
    void generateKey_applicationPdf_matchesExpectedFormat() {
        String key = generator.generateKey(MediaType.TEXT, "application/pdf");

        assertThat(key).startsWith("quarantine/text/");
        assertThat(key).endsWith(".pdf");
    }

    @Test
    @DisplayName("Handles unknown MIME types with fallback extension")
    void generateKey_unknownMime_usesFallback() {
        String key = generator.generateKey(MediaType.IMAGE, "image/unknown-future");

        assertThat(key).startsWith("quarantine/image/");
        assertThat(key).endsWith(".bin");
    }
}
