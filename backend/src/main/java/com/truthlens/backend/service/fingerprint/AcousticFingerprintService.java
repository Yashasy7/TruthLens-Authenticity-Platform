package com.truthlens.backend.service.fingerprint;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * Service generating and comparing acoustic fingerprints for audio files in TruthLens.
 *
 * <p>Employs spectral chroma and sub-band differential analysis to produce invariant
 * acoustic signatures and calculates Bit Error Rate (BER) similarity for resilient duplicate detection.</p>
 */
@Service
public class AcousticFingerprintService {

    private static final Logger log = LoggerFactory.getLogger(AcousticFingerprintService.class);
    public static final double DEFAULT_ACOUSTIC_SIMILARITY_THRESHOLD = 0.80;

    private final AcousticFingerprintGenerator fingerprintGenerator;

    public AcousticFingerprintService() {
        this(new JavaSpectralAcousticFingerprintGenerator());
    }

    @Autowired
    public AcousticFingerprintService(AcousticFingerprintGenerator fingerprintGenerator) {
        this.fingerprintGenerator = fingerprintGenerator != null
                ? fingerprintGenerator
                : new JavaSpectralAcousticFingerprintGenerator();
    }

    /**
     * Generates a spectral acoustic fingerprint from an audio input stream.
     *
     * @param audioStream stream containing raw or containerized audio
     * @return hex-encoded acoustic fingerprint string, or null on error
     */
    public String generateAcousticFingerprint(InputStream audioStream) {
        if (audioStream == null) {
            return null;
        }

        try {
            return fingerprintGenerator.generateFingerprint(audioStream);
        } catch (Exception e) {
            log.warn("Acoustic fingerprint generation failed: {}", e.getMessage());
            return null;
        }
    }

    /**
     * Calculates the normalized similarity score between two acoustic fingerprints
     * based on Bit Error Rate (BER) alignment.
     *
     * @param fp1 first acoustic fingerprint
     * @param fp2 second acoustic fingerprint
     * @return similarity score between 0.0 (unrelated) and 1.0 (identical)
     */
    public double calculateSimilarity(String fp1, String fp2) {
        if (fp1 == null || fp2 == null || fp1.isBlank() || fp2.isBlank()) {
            return 0.0;
        }

        if (fp1.equalsIgnoreCase(fp2)) {
            return 1.0;
        }

        List<Integer> frames1 = parseSubFingerprints(fp1);
        List<Integer> frames2 = parseSubFingerprints(fp2);

        if (frames1.isEmpty() || frames2.isEmpty()) {
            return 0.0;
        }

        int maxOverlap = Math.min(frames1.size(), frames2.size());
        int maxShift = Math.min(5, maxOverlap / 2);
        double maxSimilarity = 0.0;

        for (int shift = -maxShift; shift <= maxShift; shift++) {
            int start1 = Math.max(0, shift);
            int start2 = Math.max(0, -shift);
            int count = Math.min(frames1.size() - start1, frames2.size() - start2);

            if (count < 1) continue;

            int totalBits = count * 16;
            int bitErrors = 0;

            for (int i = 0; i < count; i++) {
                int f1 = frames1.get(start1 + i);
                int f2 = frames2.get(start2 + i);
                bitErrors += Integer.bitCount((f1 ^ f2) & 0xFFFF);
            }

            double sim = 1.0 - ((double) bitErrors / totalBits);
            if (sim > maxSimilarity) {
                maxSimilarity = sim;
            }
        }

        return Math.max(0.0, Math.min(1.0, maxSimilarity));
    }

    /**
     * Determines whether two acoustic fingerprints represent an acoustic match.
     *
     * @param fp1 first acoustic fingerprint
     * @param fp2 second acoustic fingerprint
     * @return true if acoustic similarity &ge; configured threshold (default 80%)
     */
    public boolean isAcousticMatch(String fp1, String fp2) {
        return isAcousticMatch(fp1, fp2, DEFAULT_ACOUSTIC_SIMILARITY_THRESHOLD);
    }

    /**
     * Determines whether two acoustic fingerprints match with a specified threshold.
     *
     * @param fp1       first acoustic fingerprint
     * @param fp2       second acoustic fingerprint
     * @param threshold similarity threshold (e.g. 0.80)
     * @return true if similarity &ge; threshold
     */
    public boolean isAcousticMatch(String fp1, String fp2, double threshold) {
        double similarity = calculateSimilarity(fp1, fp2);
        return similarity >= threshold;
    }

    private List<Integer> parseSubFingerprints(String fingerprint) {
        List<Integer> frames = new ArrayList<>();
        String payload = fingerprint;
        int prefixIdx = payload.indexOf("chroma-");
        if (prefixIdx != -1) {
            payload = payload.substring(prefixIdx + 7);
            if (payload.startsWith("v1-")) {
                payload = payload.substring(3);
            }
        }

        // Each sub-fingerprint is represented by 4 hex characters (16 bits)
        for (int i = 0; i + 4 <= payload.length(); i += 4) {
            try {
                int frame = Integer.parseInt(payload.substring(i, i + 4), 16);
                frames.add(frame);
            } catch (NumberFormatException e) {
                break;
            }
        }
        return frames;
    }
}
