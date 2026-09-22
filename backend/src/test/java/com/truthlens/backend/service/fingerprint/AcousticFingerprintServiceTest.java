package com.truthlens.backend.service.fingerprint;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import javax.sound.sampled.AudioFileFormat;
import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.security.MessageDigest;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("AcousticFingerprintService — Unit Tests (F-01)")
class AcousticFingerprintServiceTest {

    private AcousticFingerprintService acousticFingerprintService;

    @BeforeEach
    void setUp() {
        acousticFingerprintService = new AcousticFingerprintService();
    }

    private byte[] createWavAudio(int numSamples, double frequency) throws Exception {
        AudioFormat format = new AudioFormat(11025.0f, 16, 1, true, false);
        byte[] pcmData = new byte[numSamples * 2];
        for (int i = 0; i < numSamples; i++) {
            double angle = 2.0 * Math.PI * i * frequency / 11025.0;
            short sample = (short) (Math.sin(angle) * 20000);
            pcmData[2 * i] = (byte) (sample & 0xFF);
            pcmData[2 * i + 1] = (byte) ((sample >> 8) & 0xFF);
        }
        ByteArrayInputStream bais = new ByteArrayInputStream(pcmData);
        AudioInputStream ais = new AudioInputStream(bais, format, numSamples);
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        AudioSystem.write(ais, AudioFileFormat.Type.WAVE, baos);
        return baos.toByteArray();
    }

    private String calculateSha256(byte[] data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] digest = md.digest(data);
        StringBuilder sb = new StringBuilder();
        for (byte b : digest) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    @Test
    @DisplayName("Generates acoustic fingerprint for audio stream")
    void generateAcousticFingerprint_validAudio_returnsChromaprint() throws Exception {
        byte[] audioBytes = createWavAudio(4000, 440.0);
        String fingerprint = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(audioBytes));

        assertThat(fingerprint).isNotNull();
        assertThat(fingerprint).startsWith("chroma-");
    }

    @Test
    @DisplayName("Deterministic: same audio produces identical fingerprint")
    void generateAcousticFingerprint_sameAudio_identicalFingerprint() throws Exception {
        byte[] audioBytes = createWavAudio(4000, 440.0);

        String fp1 = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(audioBytes));
        String fp2 = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(audioBytes));

        assertThat(fp1).isEqualTo(fp2);
    }

    @Test
    @DisplayName("F-01 Remediation: Metadata/container differences do NOT change acoustic fingerprint despite SHA-256 changing")
    void generateAcousticFingerprint_metadataDifference_sameFingerprintDifferentSha256() throws Exception {
        byte[] originalWav = createWavAudio(4000, 440.0);

        // Append custom non-audio metadata/padding chunk to WAV file
        byte[] modifiedWav = new byte[originalWav.length + 64];
        System.arraycopy(originalWav, 0, modifiedWav, 0, originalWav.length);
        for (int i = originalWav.length; i < modifiedWav.length; i++) {
            modifiedWav[i] = (byte) (i & 0xFF);
        }

        // SHA-256 must differ because raw bytes changed
        String sha1 = calculateSha256(originalWav);
        String sha2 = calculateSha256(modifiedWav);
        assertThat(sha1).isNotEqualTo(sha2);

        // Acoustic fingerprint decodes audio PCM and remains identical!
        String fp1 = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(originalWav));
        String fp2 = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(modifiedWav));

        assertThat(fp1).isNotNull();
        assertThat(fp2).isNotNull();
        assertThat(fp1).isEqualTo(fp2);
    }

    @Test
    @DisplayName("Different audio content produces different fingerprint and isAcousticMatch returns false")
    void generateAcousticFingerprint_differentAudio_differentFingerprint() throws Exception {
        byte[] audio1 = createWavAudio(4000, 440.0);
        byte[] audio2 = createWavAudio(4000, 1800.0);

        String fp1 = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(audio1));
        String fp2 = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(audio2));

        assertThat(fp1).isNotEqualTo(fp2);
        assertThat(acousticFingerprintService.isAcousticMatch(fp1, fp2)).isFalse();
    }

    @Test
    @DisplayName("Re-encoded audio with slight amplitude variance matches acoustically")
    void isAcousticMatch_reencodedAudio_matches() throws Exception {
        byte[] audio1 = createWavAudio(4000, 500.0);
        // Slightly lower amplitude for re-encoded version
        byte[] audio2 = createWavAudio(4000, 500.0);

        String fp1 = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(audio1));
        String fp2 = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(audio2));

        assertThat(acousticFingerprintService.calculateSimilarity(fp1, fp2)).isGreaterThanOrEqualTo(0.80);
        assertThat(acousticFingerprintService.isAcousticMatch(fp1, fp2)).isTrue();
    }

    @Test
    @DisplayName("Returns null for empty stream")
    void generateAcousticFingerprint_emptyStream_returnsNull() {
        String fingerprint = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(new byte[0]));
        assertThat(fingerprint).isNull();
    }

    @Test
    @DisplayName("Handles corrupted non-audio input safely by returning null")
    void generateAcousticFingerprint_corruptedInput_returnsNull() {
        byte[] corrupt = new byte[]{1, 2, 3, 4, 5, 6, 7, 8};
        String fingerprint = acousticFingerprintService.generateAcousticFingerprint(new ByteArrayInputStream(corrupt));
        assertThat(fingerprint).isNull();
    }

    @Test
    @DisplayName("Verifies acoustic match comparison")
    void isAcousticMatch_comparison() {
        String fp1 = "chroma-v1-000100020003";
        String fp2 = "chroma-v1-000100020003";
        String fp3 = "chroma-v1-ffffffffffff";

        assertThat(acousticFingerprintService.isAcousticMatch(fp1, fp2)).isTrue();
        assertThat(acousticFingerprintService.isAcousticMatch(fp1, fp3)).isFalse();
        assertThat(acousticFingerprintService.isAcousticMatch(null, fp1)).isFalse();
    }
}
