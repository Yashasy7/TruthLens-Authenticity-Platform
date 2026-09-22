package com.truthlens.backend.service.fingerprint;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.imageio.ImageIO;
import java.awt.Graphics2D;
import java.awt.Image;
import java.awt.image.BufferedImage;
import java.io.InputStream;

/**
 * Service generating perceptual visual difference hashes (dHash) for images in TruthLens.
 *
 * <p>Algorithm Overview (64-bit dHash):</p>
 * <ol>
 *   <li>Decode image stream to grayscale.</li>
 *   <li>Downsample image to 9 pixels wide by 8 pixels high (72 pixels).</li>
 *   <li>Compare each pixel to its right-hand neighbor: if {@code left > right}, set bit to 1; else 0.</li>
 *   <li>Produces 64 bits (8 rows x 8 comparisons) represented as a 16-character hexadecimal string.</li>
 *   <li>Visual similarity is measured using the Hamming distance between two 64-bit hashes.</li>
 * </ol>
 *
 * <p>A Hamming distance of 0 indicates an identical visual rendering. A distance &le; 10
 * indicates a near-duplicate image (rescaled, compressed, or slight color adjustment).</p>
 */
@Service
public class PerceptualHashService {

    private static final Logger log = LoggerFactory.getLogger(PerceptualHashService.class);

    public static final int DEFAULT_HAMMING_THRESHOLD = 10;
    public static final int TOTAL_BITS = 64;

    private final int hammingThreshold;

    public PerceptualHashService(
            @Value("${truthlens.fingerprint.hamming-threshold:10}") int hammingThreshold) {
        this.hammingThreshold = hammingThreshold;
    }

    /**
     * Generates a 64-bit difference hash (dHash) from an image input stream.
     *
     * @param imageStream the input stream containing image data
     * @return 16-character hexadecimal string representing the 64-bit hash, or null if image cannot be decoded
     */
    public String generateDHash(InputStream imageStream) {
        if (imageStream == null) {
            return null;
        }

        try {
            BufferedImage original = ImageIO.read(imageStream);
            if (original == null) {
                log.debug("Perceptual hashing skipped: Input stream is not decodable as a standard image");
                return null;
            }

            return calculateDHash(original);
        } catch (Exception e) {
            log.warn("Failed to generate perceptual hash for image stream: {}", e.getMessage());
            return null;
        }
    }

    /**
     * Calculates the 64-bit dHash directly from a {@link BufferedImage}.
     *
     * @param original the decoded image
     * @return 16-character hexadecimal string
     */
    public String calculateDHash(BufferedImage original) {
        // Step 1 & 2: Resize to 9x8 grayscale
        BufferedImage resized = new BufferedImage(9, 8, BufferedImage.TYPE_BYTE_GRAY);
        Graphics2D g = resized.createGraphics();
        try {
            Image scaled = original.getScaledInstance(9, 8, Image.SCALE_SMOOTH);
            g.drawImage(scaled, 0, 0, 9, 8, null);
        } finally {
            g.dispose();
        }

        // Check sample variance across the 9x8 raster
        int minSample = 255;
        int maxSample = 0;
        long sumSample = 0;
        for (int y = 0; y < 8; y++) {
            for (int x = 0; x < 9; x++) {
                int sample = resized.getRaster().getSample(x, y, 0);
                if (sample < minSample) minSample = sample;
                if (sample > maxSample) maxSample = sample;
                sumSample += sample;
            }
        }

        // Remediate uniform image collision (F-04):
        // If image has near-zero variance across all pixels (e.g. solid black, white, or red),
        // standard gradient comparison left > right yields all zeros for any uniform color.
        // We encode the average luminance level across the 64-bit hash so solid black (0),
        // solid white (255), and solid red (~76) have large Hamming distances from each other,
        // while identical uniform images produce identical hashes with distance 0.
        if (maxSample - minSample <= 2) {
            int avgLuminance = (int) (sumSample / 72);
            long byteVal = avgLuminance & 0xFFL;
            long hash = 0L;
            for (int i = 0; i < 8; i++) {
                hash |= (byteVal << (i * 8));
            }
            return String.format("%016x", hash);
        }

        // Step 3: Compute difference gradient bits for non-uniform images
        long hash = 0L;
        for (int y = 0; y < 8; y++) {
            for (int x = 0; x < 8; x++) {
                int leftPixel = resized.getRaster().getSample(x, y, 0);
                int rightPixel = resized.getRaster().getSample(x + 1, y, 0);

                if (leftPixel > rightPixel) {
                    hash |= (1L << (y * 8 + x));
                }
            }
        }

        // Step 4: Format as 16 hex characters, zero-padded
        return String.format("%016x", hash);
    }

    /**
     * Converts a 16-character hex hash into a 64-character binary vector representation,
     * suitable for vector similarity search (blueprint phash_vector).
     *
     * @param hexHash 16-character hex hash
     * @return 64-character binary string, or null if invalid
     */
    public String toVectorRepresentation(String hexHash) {
        if (hexHash == null || hexHash.length() != 16) {
            return null;
        }
        try {
            long val = Long.parseUnsignedLong(hexHash, 16);
            StringBuilder sb = new StringBuilder(64);
            for (int i = 63; i >= 0; i--) {
                sb.append((val >>> i) & 1L);
            }
            return sb.toString();
        } catch (NumberFormatException e) {
            return null;
        }
    }

    /**
     * Calculates the Hamming distance (number of differing bits) between two 64-bit hex hashes.
     *
     * @param hash1 16-character hex hash
     * @param hash2 16-character hex hash
     * @return Hamming distance (0 to 64), or -1 if invalid
     */
    public int calculateHammingDistance(String hash1, String hash2) {
        if (hash1 == null || hash2 == null || hash1.length() != 16 || hash2.length() != 16) {
            return -1;
        }

        try {
            long val1 = Long.parseUnsignedLong(hash1, 16);
            long val2 = Long.parseUnsignedLong(hash2, 16);
            return Long.bitCount(val1 ^ val2);
        } catch (NumberFormatException e) {
            log.warn("Failed to parse perceptual hash for distance calculation: '{}' vs '{}'", hash1, hash2);
            return -1;
        }
    }

    /**
     * Calculates the normalized similarity score between two perceptual hashes.
     *
     * @param hash1 16-character hex hash
     * @param hash2 16-character hex hash
     * @return normalized score between 0.0 (completely dissimilar) and 1.0 (identical)
     */
    public double calculateSimilarity(String hash1, String hash2) {
        int distance = calculateHammingDistance(hash1, hash2);
        if (distance < 0) {
            return 0.0;
        }
        return Math.max(0.0, 1.0 - ((double) distance / TOTAL_BITS));
    }

    /**
     * Determines whether two perceptual hashes represent a visual near-duplicate.
     *
     * @param hash1 first perceptual hash
     * @param hash2 second perceptual hash
     * @return true if Hamming distance &le; configured threshold
     */
    public boolean isNearMatch(String hash1, String hash2) {
        int distance = calculateHammingDistance(hash1, hash2);
        return distance >= 0 && distance <= hammingThreshold;
    }

    public int getHammingThreshold() {
        return hammingThreshold;
    }
}
