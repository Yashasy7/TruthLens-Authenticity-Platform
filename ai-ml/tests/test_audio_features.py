"""
TruthLens AI/ML — Module 07 Tests: Acoustic Features & Mel-Spectrogram Generation
"""

import base64
import numpy as np
from PIL import Image
import pytest

from services.audio_analysis.features import (
    AcousticFeatures,
    compute_mel_spectrogram,
    compute_mfcc,
    compute_rms_energy,
    compute_spectral_centroid,
    compute_spectral_flux,
    compute_spectral_rolloff,
    compute_stft,
    compute_zero_crossing_rate,
    create_mel_filterbank,
    extract_acoustic_features,
    render_mel_spectrogram_base64,
)


class TestAudioFeatures:
    """Acoustic feature extraction and Mel-spectrogram unit tests."""

    @pytest.fixture
    def sine_wave(self) -> np.ndarray:
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        return (0.7 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

    @pytest.fixture
    def silent_wave(self) -> np.ndarray:
        return np.zeros(16000, dtype=np.float32)

    def test_create_mel_filterbank_shape_and_range(self):
        fb = create_mel_filterbank(sr=16000, n_fft=1024, n_mels=80)
        assert isinstance(fb, np.ndarray)
        assert fb.shape == (80, 513)
        assert fb.min() >= 0.0
        assert fb.max() <= 1.0

    def test_compute_stft(self, sine_wave):
        freqs, times, mag, zxx = compute_stft(sine_wave, sr=16000, n_fft=1024, hop_length=256)
        assert len(freqs) == 513
        assert mag.shape == (513, len(times))
        assert zxx.dtype == np.complex128 or zxx.dtype == np.complex64

    def test_compute_mel_spectrogram(self, sine_wave):
        log_mel, mel_spec, mag_spec, times = compute_mel_spectrogram(
            sine_wave, sr=16000, n_fft=1024, hop_length=256, n_mels=80
        )
        assert log_mel.shape[0] == 80
        assert log_mel.shape[1] == len(times)
        assert mel_spec.shape == log_mel.shape
        # dB scale should be bounded
        assert np.all(np.isfinite(log_mel))

    def test_compute_mfcc(self, sine_wave):
        log_mel, _, _, _ = compute_mel_spectrogram(sine_wave, sr=16000, n_mels=80)
        mfcc = compute_mfcc(log_mel, n_mfcc=20)
        assert mfcc.shape == (20, log_mel.shape[1])
        assert np.all(np.isfinite(mfcc))

    def test_spectral_centroid_and_rolloff(self, sine_wave):
        _, _, mag, _ = compute_stft(sine_wave, sr=16000, n_fft=1024, hop_length=256)
        centroid = compute_spectral_centroid(mag, sr=16000, n_fft=1024)
        rolloff = compute_spectral_rolloff(mag, roll_percent=0.85, sr=16000, n_fft=1024)

        assert len(centroid) == mag.shape[1]
        assert len(rolloff) == mag.shape[1]
        # For a 440 Hz pure tone, centroid should be centered near 440 Hz
        assert 350.0 <= np.mean(centroid) <= 550.0

    def test_zero_crossing_rate_and_rms(self, sine_wave):
        zcr = compute_zero_crossing_rate(sine_wave, frame_length=1024, hop_length=256)
        rms = compute_rms_energy(sine_wave, frame_length=1024, hop_length=256)

        assert len(zcr) > 0
        assert len(rms) > 0
        assert np.all(zcr >= 0.0)
        assert np.all(rms >= 0.0)

    def test_spectral_flux(self, sine_wave):
        _, _, mag, _ = compute_stft(sine_wave, sr=16000)
        flux = compute_spectral_flux(mag)
        assert len(flux) == mag.shape[1]
        assert np.all(flux >= 0.0)

    def test_render_mel_spectrogram_base64_valid_png(self, sine_wave):
        log_mel, _, _, _ = compute_mel_spectrogram(sine_wave, sr=16000, n_mels=80)
        b64 = render_mel_spectrogram_base64(log_mel)

        assert isinstance(b64, str)
        assert len(b64) > 100

        # Decode and verify it's a readable PNG image
        raw_bytes = base64.b64decode(b64)
        assert raw_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    def test_extract_acoustic_features_full_dataclass(self, sine_wave):
        feat = extract_acoustic_features(sine_wave, sr=16000)
        assert isinstance(feat, AcousticFeatures)
        assert feat.duration_seconds == pytest.approx(1.0, abs=0.01)
        assert feat.log_mel.shape[0] == 80
        assert feat.mfcc.shape[0] == 20
        assert feat.spectral_centroid_mean > 0.0
        assert feat.spectral_bandwidth_mean > 0.0
        assert feat.spectral_rolloff_mean > 0.0
        assert feat.zero_crossing_rate_mean > 0.0
        assert feat.rms_energy_mean > 0.0
        assert isinstance(feat.spectrogram_base64, str)

    def test_silent_audio_does_not_crash(self, silent_wave):
        feat = extract_acoustic_features(silent_wave, sr=16000)
        assert feat.duration_seconds == pytest.approx(1.0, abs=0.01)
        assert np.all(np.isfinite(feat.log_mel))
        assert len(feat.spectrogram_base64) > 0
