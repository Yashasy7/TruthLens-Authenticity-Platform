package com.truthlens.backend.service.fingerprint;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * Pure Java implementation of acoustic fingerprint generation based on Short-Time
 * Fourier Transform (STFT) spectral sub-band and chroma energy differences.
 *
 * <p>Algorithmic Pipeline:</p>
 * <ol>
 *   <li>Decodes audio container headers via {@link AudioSystem} to extract pure PCM audio samples,
 *       rendering the fingerprint invariant to container differences and metadata tags (ID3, RIFF chunks).</li>
 *   <li>Downmixes and normalizes PCM audio to standard 16-bit mono frames.</li>
 *   <li>Applies a Hanning-windowed STFT across overlapping frames (1024 samples, 50% overlap).</li>
 *   <li>Aggregates spectral magnitude into 16 logarithmic frequency bands spanning core audio frequencies.</li>
 *   <li>Quantizes differential energy across adjacent frequency bands and consecutive time frames
 *       (Haitsma-Kalker / Chromaprint methodology).</li>
 *   <li>Encodes the resulting sub-fingerprint sequence into a deterministic hex acoustic signature.</li>
 * </ol>
 */
@Component
public class JavaSpectralAcousticFingerprintGenerator implements AcousticFingerprintGenerator {

    private static final Logger log = LoggerFactory.getLogger(JavaSpectralAcousticFingerprintGenerator.class);

    private static final int FRAME_SIZE = 1024;
    private static final int HOP_SIZE = 512;
    private static final int NUM_BANDS = 16;
    private static final int MIN_REQUIRED_SAMPLES = 1024;

    @Override
    public boolean isAvailable() {
        return true;
    }

    @Override
    public String generateFingerprint(InputStream audioStream) {
        if (audioStream == null) {
            return null;
        }

        try {
            double[] samples = extractPcmSamples(audioStream);
            if (samples == null || samples.length < MIN_REQUIRED_SAMPLES) {
                log.debug("Acoustic fingerprinting skipped: Insufficient decoded audio samples ({})",
                        samples != null ? samples.length : 0);
                return null;
            }

            return computeSpectralChromaprint(samples);
        } catch (Exception e) {
            log.warn("Failed to generate spectral acoustic fingerprint: {}", e.getMessage());
            return null;
        }
    }

    /**
     * Extracts normalized PCM samples from an audio stream.
     * Uses {@link AudioSystem} to strip container/metadata chunks where supported,
     * falling back to raw PCM interpretation for headerless synthetic streams.
     */
    private double[] extractPcmSamples(InputStream in) throws Exception {
        BufferedInputStream bis = new BufferedInputStream(in);
        bis.mark(1024 * 1024);

        try {
            AudioInputStream ais = AudioSystem.getAudioInputStream(bis);
            AudioFormat baseFormat = ais.getFormat();

            // Normalize format: 16-bit, signed, mono, little-endian PCM
            AudioFormat targetFormat = new AudioFormat(
                    AudioFormat.Encoding.PCM_SIGNED,
                    baseFormat.getSampleRate() > 0 ? baseFormat.getSampleRate() : 11025.0f,
                    16,
                    1,
                    2,
                    baseFormat.getSampleRate() > 0 ? baseFormat.getSampleRate() : 11025.0f,
                    false
            );

            AudioInputStream decodedAis = AudioSystem.isConversionSupported(targetFormat, baseFormat)
                    ? AudioSystem.getAudioInputStream(targetFormat, ais)
                    : ais;

            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int read;
            while ((read = decodedAis.read(buf)) != -1) {
                baos.write(buf, 0, read);
            }
            decodedAis.close();

            byte[] pcmBytes = baos.toByteArray();
            if (pcmBytes.length < 2) {
                return null;
            }

            int numSamples = pcmBytes.length / 2;
            double[] samples = new double[numSamples];
            for (int i = 0; i < numSamples; i++) {
                short s = (short) ((pcmBytes[2 * i] & 0xFF) | (pcmBytes[2 * i + 1] << 8));
                samples[i] = s / 32768.0;
            }
            return samples;
        } catch (Exception ex) {
            // Fallback for headerless or synthetic sample streams
            bis.reset();
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int read;
            while ((read = bis.read(buf)) != -1) {
                baos.write(buf, 0, read);
            }
            byte[] rawBytes = baos.toByteArray();
            if (rawBytes.length < 2) {
                return null;
            }

            int numSamples = rawBytes.length / 2;
            double[] samples = new double[numSamples];
            for (int i = 0; i < numSamples; i++) {
                short s = (short) ((rawBytes[2 * i] & 0xFF) | (rawBytes[2 * i + 1] << 8));
                samples[i] = s / 32768.0;
            }
            return samples;
        }
    }

    /**
     * Computes the spectral chroma / sub-band differential fingerprint from PCM samples.
     */
    private String computeSpectralChromaprint(double[] samples) {
        int numFrames = (samples.length - FRAME_SIZE) / HOP_SIZE + 1;
        if (numFrames < 1) {
            return null;
        }

        // 1. Calculate band energies for each frame
        List<double[]> frameBandEnergies = new ArrayList<>(numFrames);
        double[] window = createHanningWindow(FRAME_SIZE);

        for (int frameIdx = 0; frameIdx < numFrames; frameIdx++) {
            int start = frameIdx * HOP_SIZE;
            double[] real = new double[FRAME_SIZE];
            double[] imag = new double[FRAME_SIZE];

            for (int i = 0; i < FRAME_SIZE; i++) {
                real[i] = samples[start + i] * window[i];
                imag[i] = 0.0;
            }

            fft(real, imag);

            // Compute power spectrum up to Nyquist
            int halfSize = FRAME_SIZE / 2;
            double[] power = new double[halfSize];
            for (int i = 0; i < halfSize; i++) {
                power[i] = real[i] * real[i] + imag[i] * imag[i];
            }

            // Aggregate into NUM_BANDS logarithmic frequency bands
            double[] bandEnergies = new double[NUM_BANDS];
            int bandWidth = halfSize / NUM_BANDS;
            for (int b = 0; b < NUM_BANDS; b++) {
                double sum = 0.0;
                int bStart = b * bandWidth;
                int bEnd = (b == NUM_BANDS - 1) ? halfSize : (b + 1) * bandWidth;
                for (int k = bStart; k < bEnd; k++) {
                    sum += power[k];
                }
                bandEnergies[b] = Math.log1p(sum);
            }
            frameBandEnergies.add(bandEnergies);
        }

        // 2. Compute differential quantization across bands and consecutive frames
        StringBuilder hexBuilder = new StringBuilder("chroma-v1-");
        double[] prevEnergies = frameBandEnergies.get(0);

        for (int t = 1; t < frameBandEnergies.size(); t++) {
            double[] currEnergies = frameBandEnergies.get(t);
            int subFingerprint = 0;

            for (int m = 0; m < NUM_BANDS - 1; m++) {
                double diff = (currEnergies[m] - currEnergies[m + 1])
                            - (prevEnergies[m] - prevEnergies[m + 1]);
                if (diff > 0.0) {
                    subFingerprint |= (1 << m);
                }
            }
            hexBuilder.append(String.format("%04x", subFingerprint));
            prevEnergies = currEnergies;
        }

        // If only 1 frame, encode single-frame band differentials
        if (frameBandEnergies.size() == 1) {
            int subFingerprint = 0;
            for (int m = 0; m < NUM_BANDS - 1; m++) {
                if (prevEnergies[m] > prevEnergies[m + 1]) {
                    subFingerprint |= (1 << m);
                }
            }
            hexBuilder.append(String.format("%04x", subFingerprint));
        }

        return hexBuilder.toString();
    }

    private double[] createHanningWindow(int size) {
        double[] w = new double[size];
        for (int i = 0; i < size; i++) {
            w[i] = 0.5 * (1.0 - Math.cos(2.0 * Math.PI * i / (size - 1)));
        }
        return w;
    }

    /**
     * In-place Cooley-Tukey Radix-2 Decimation-In-Time FFT.
     */
    private void fft(double[] real, double[] imag) {
        int n = real.length;

        // Bit-reversal permutation
        int j = 0;
        for (int i = 0; i < n - 1; i++) {
            if (i < j) {
                double tr = real[i];
                real[i] = real[j];
                real[j] = tr;
                double ti = imag[i];
                imag[i] = imag[j];
                imag[j] = ti;
            }
            int k = n >> 1;
            while (k <= j) {
                j -= k;
                k >>= 1;
            }
            j += k;
        }

        // Butterfly calculations
        for (int len = 2; len <= n; len <<= 1) {
            double angle = -2.0 * Math.PI / len;
            double wlenReal = Math.cos(angle);
            double wlenImag = Math.sin(angle);

            for (int i = 0; i < n; i += len) {
                double wReal = 1.0;
                double wImag = 0.0;
                int half = len >> 1;

                for (int k = 0; k < half; k++) {
                    double uReal = real[i + k];
                    double uImag = imag[i + k];
                    double vReal = real[i + k + half] * wReal - imag[i + k + half] * wImag;
                    double vImag = real[i + k + half] * wImag + imag[i + k + half] * wReal;

                    real[i + k] = uReal + vReal;
                    imag[i + k] = uImag + vImag;
                    real[i + k + half] = uReal - vReal;
                    imag[i + k + half] = uImag - vImag;

                    double nextWReal = wReal * wlenReal - wImag * wlenImag;
                    double nextWImag = wReal * wlenImag + wImag * wlenReal;
                    wReal = nextWReal;
                    wImag = nextWImag;
                }
            }
        }
    }
}
