package com.truthlens.backend.service.fingerprint;

import java.io.InputStream;

/**
 * Strategy interface for generating acoustic fingerprints from audio data.
 */
public interface AcousticFingerprintGenerator {

    /**
     * Generates an acoustic fingerprint string from an audio input stream.
     *
     * @param audioStream stream containing audio content
     * @return acoustic fingerprint string, or null if stream cannot be processed
     */
    String generateFingerprint(InputStream audioStream);

    /**
     * Indicates whether this fingerprint generator is available and ready for execution.
     *
     * @return true if operational
     */
    boolean isAvailable();
}
