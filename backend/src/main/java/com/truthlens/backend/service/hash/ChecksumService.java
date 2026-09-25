package com.truthlens.backend.service.hash;

import com.truthlens.backend.exception.InvalidMediaException;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Service providing cryptographic hashing for ingested multimedia.
 *
 * <p>Generates deterministic SHA-256 fingerprints directly from input streams
 * using a memory-efficient buffer.</p>
 */
@Service
public class ChecksumService {

    private static final String ALGORITHM = "SHA-256";
    private static final int BUFFER_SIZE = 8192;

    /**
     * Calculates the SHA-256 hash of an input stream.
     *
     * @param inputStream the data stream
     * @return 64-character lowercase hexadecimal hash string
     */
    public String calculateSha256(InputStream inputStream) {
        if (inputStream == null) {
            throw new InvalidMediaException("Input stream for SHA-256 calculation must not be null");
        }

        try {
            MessageDigest digest = MessageDigest.getInstance(ALGORITHM);
            byte[] buffer = new byte[BUFFER_SIZE];
            int bytesRead;

            while ((bytesRead = inputStream.read(buffer)) != -1) {
                digest.update(buffer, 0, bytesRead);
            }

            byte[] hashBytes = digest.digest();
            return bytesToHex(hashBytes);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 algorithm not available in JVM", e);
        } catch (IOException e) {
            throw new InvalidMediaException("Failed to read stream for SHA-256 calculation", e);
        }
    }

    /**
     * Converts a byte array to a lowercase hex string.
     */
    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(Character.forDigit((b >> 4) & 0xF, 16));
            sb.append(Character.forDigit(b & 0xF, 16));
        }
        return sb.toString();
    }
}
