package com.truthlens.backend.service.fingerprint;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("PerceptualHashService — Unit Tests")
class PerceptualHashServiceTest {

    private PerceptualHashService perceptualHashService;

    @BeforeEach
    void setUp() {
        perceptualHashService = new PerceptualHashService(10);
    }

    private byte[] createTestImageBytes(int width, int height, Color color) throws Exception {
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = image.createGraphics();
        g.setColor(color);
        g.fillRect(0, 0, width, height);
        // Add a gradient so pixels differ
        for (int i = 0; i < width; i++) {
            g.setColor(new Color((i * 2) % 256, (i * 3) % 256, (i * 5) % 256));
            g.drawLine(i, 0, i, height);
        }
        g.dispose();

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(image, "png", baos);
        return baos.toByteArray();
    }

    @Test
    @DisplayName("Generates 16-character hex dHash from valid image stream")
    void generateDHash_validImage_returns16CharHex() throws Exception {
        byte[] imageBytes = createTestImageBytes(100, 100, Color.BLUE);
        String hash = perceptualHashService.generateDHash(new ByteArrayInputStream(imageBytes));

        assertThat(hash).isNotNull();
        assertThat(hash).hasSize(16);
        assertThat(hash).matches("^[0-9a-fA-F]{16}$");
    }

    @Test
    @DisplayName("Deterministic: identical images produce identical dHash")
    void generateDHash_identicalImages_sameHash() throws Exception {
        byte[] imageBytes = createTestImageBytes(80, 80, Color.RED);
        String hash1 = perceptualHashService.generateDHash(new ByteArrayInputStream(imageBytes));
        String hash2 = perceptualHashService.generateDHash(new ByteArrayInputStream(imageBytes));

        assertThat(hash1).isEqualTo(hash2);
    }

    @Test
    @DisplayName("Calculates Hamming distance correctly")
    void calculateHammingDistance_knownValues() {
        String hashA = "0000000000000000";
        String hashB = "0000000000000001"; // 1 bit different
        String hashC = "ffffffffffffffff"; // 64 bits different

        assertThat(perceptualHashService.calculateHammingDistance(hashA, hashA)).isEqualTo(0);
        assertThat(perceptualHashService.calculateHammingDistance(hashA, hashB)).isEqualTo(1);
        assertThat(perceptualHashService.calculateHammingDistance(hashA, hashC)).isEqualTo(64);
    }

    @Test
    @DisplayName("Determines near-match when Hamming distance is within threshold")
    void isNearMatch_withinThreshold_returnsTrue() {
        String hash1 = "0000000000000000";
        String hash2 = "0000000000000007"; // 3 bits different (0111 in binary) <= 10 threshold

        assertThat(perceptualHashService.isNearMatch(hash1, hash2)).isTrue();
    }

    @Test
    @DisplayName("Rejects near-match when Hamming distance exceeds threshold")
    void isNearMatch_exceedsThreshold_returnsFalse() {
        String hash1 = "0000000000000000";
        String hash2 = "0000ffff00000000"; // 16 bits different > 10 threshold

        assertThat(perceptualHashService.isNearMatch(hash1, hash2)).isFalse();
    }

    @Test
    @DisplayName("Computes normalized similarity score correctly")
    void calculateSimilarity_proportionalScore() {
        String hashA = "0000000000000000";
        String hashB = "0000000000000000"; // distance 0 -> score 1.0
        String hashC = "ffffffffffffffff"; // distance 64 -> score 0.0

        assertThat(perceptualHashService.calculateSimilarity(hashA, hashB)).isEqualTo(1.0);
        assertThat(perceptualHashService.calculateSimilarity(hashA, hashC)).isEqualTo(0.0);
    }

    @Test
    @DisplayName("Handles corrupted or non-image stream safely by returning null")
    void generateDHash_nonImageStream_returnsNull() {
        byte[] garbage = "not an image content".getBytes();
        String hash = perceptualHashService.generateDHash(new ByteArrayInputStream(garbage));

        assertThat(hash).isNull();
    }

    private byte[] createSolidColorImageBytes(int width, int height, Color color) throws Exception {
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = image.createGraphics();
        g.setColor(color);
        g.fillRect(0, 0, width, height);
        g.dispose();

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(image, "png", baos);
        return baos.toByteArray();
    }

    @Test
    @DisplayName("F-04 Remediation: Visually different uniform images do not collide")
    void generateDHash_uniformImages_doNotCollide() throws Exception {
        byte[] blackBytes = createSolidColorImageBytes(50, 50, Color.BLACK);
        byte[] whiteBytes = createSolidColorImageBytes(50, 50, Color.WHITE);
        byte[] redBytes = createSolidColorImageBytes(50, 50, Color.RED);

        String blackHash = perceptualHashService.generateDHash(new ByteArrayInputStream(blackBytes));
        String whiteHash = perceptualHashService.generateDHash(new ByteArrayInputStream(whiteBytes));
        String redHash = perceptualHashService.generateDHash(new ByteArrayInputStream(redBytes));

        // Hashes must be 16-hex characters
        assertThat(blackHash).hasSize(16);
        assertThat(whiteHash).hasSize(16);
        assertThat(redHash).hasSize(16);

        // Black vs White must not match
        assertThat(perceptualHashService.isNearMatch(blackHash, whiteHash)).isFalse();
        assertThat(perceptualHashService.calculateHammingDistance(blackHash, whiteHash)).isGreaterThan(10);

        // Black vs Red must not match
        assertThat(perceptualHashService.isNearMatch(blackHash, redHash)).isFalse();
        assertThat(perceptualHashService.calculateHammingDistance(blackHash, redHash)).isGreaterThan(10);

        // White vs Red must not match
        assertThat(perceptualHashService.isNearMatch(whiteHash, redHash)).isFalse();
        assertThat(perceptualHashService.calculateHammingDistance(whiteHash, redHash)).isGreaterThan(10);
    }

    @Test
    @DisplayName("F-04 Remediation: Identical uniform images produce identical hashes with distance 0")
    void generateDHash_identicalUniformImages_match() throws Exception {
        byte[] red1 = createSolidColorImageBytes(50, 50, Color.RED);
        byte[] red2 = createSolidColorImageBytes(80, 80, Color.RED);

        String redHash1 = perceptualHashService.generateDHash(new ByteArrayInputStream(red1));
        String redHash2 = perceptualHashService.generateDHash(new ByteArrayInputStream(red2));

        assertThat(redHash1).isEqualTo(redHash2);
        assertThat(perceptualHashService.calculateHammingDistance(redHash1, redHash2)).isEqualTo(0);
        assertThat(perceptualHashService.isNearMatch(redHash1, redHash2)).isTrue();
    }

    @Test
    @DisplayName("Vector representation converts 16-hex hash to 64-char binary vector")
    void toVectorRepresentation_validHex_produces64CharVector() {
        String hex = "0000000000000001";
        String vector = perceptualHashService.toVectorRepresentation(hex);

        assertThat(vector).hasSize(64);
        assertThat(vector).endsWith("1");
        assertThat(vector.substring(0, 63)).doesNotContain("1");
    }
}
