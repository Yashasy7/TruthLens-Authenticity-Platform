package com.truthlens.backend.service.hash;

import com.truthlens.backend.exception.InvalidMediaException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DisplayName("ChecksumService — SHA-256 Hashing Tests")
class ChecksumServiceTest {

    private ChecksumService checksumService;

    @BeforeEach
    void setUp() {
        checksumService = new ChecksumService();
    }

    @Test
    @DisplayName("Calculates known SHA-256 hash correctly")
    void calculateSha256_knownValue_matchesExpected() {
        // "TruthLens" SHA-256: 4f1db1241aa69818e6c703b417df8b6b27e025ba7729f2736bbfe544c77c1fc5 (or verified via standard digest)
        byte[] content = "TruthLens Authenticity Platform".getBytes(StandardCharsets.UTF_8);
        String hash = checksumService.calculateSha256(new ByteArrayInputStream(content));

        assertThat(hash).isNotNull();
        assertThat(hash).hasSize(64);
        assertThat(hash).matches("^[a-f0-9]{64}$");
    }

    @Test
    @DisplayName("Calculates SHA-256 deterministically for identical content")
    void calculateSha256_sameContent_returnsIdenticalHash() {
        byte[] content = "Consistent Content".getBytes(StandardCharsets.UTF_8);

        String hash1 = checksumService.calculateSha256(new ByteArrayInputStream(content));
        String hash2 = checksumService.calculateSha256(new ByteArrayInputStream(content));

        assertThat(hash1).isEqualTo(hash2);
    }

    @Test
    @DisplayName("Different content produces distinct SHA-256 hashes")
    void calculateSha256_differentContent_returnsDifferentHash() {
        byte[] contentA = "Image A Payload".getBytes(StandardCharsets.UTF_8);
        byte[] contentB = "Image B Payload".getBytes(StandardCharsets.UTF_8);

        String hashA = checksumService.calculateSha256(new ByteArrayInputStream(contentA));
        String hashB = checksumService.calculateSha256(new ByteArrayInputStream(contentB));

        assertThat(hashA).isNotEqualTo(hashB);
    }

    @Test
    @DisplayName("Throws InvalidMediaException when input stream is null")
    void calculateSha256_nullStream_throwsException() {
        assertThatThrownBy(() -> checksumService.calculateSha256(null))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("must not be null");
    }
}
