import os
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Dict, Any, List, Optional, Union
from ..config import settings
from ..schemas import AudioSpliceMarker


class DecodedAudio:
    """Represents a normalized mono audio signal with metadata."""
    def __init__(self, waveform: np.ndarray, sample_rate: int, duration_seconds: float):
        self.waveform = waveform.astype(np.float32)
        self.sample_rate = int(sample_rate)
        self.duration_seconds = round(float(duration_seconds), 3)

    @property
    def audio(self) -> np.ndarray:
        return self.waveform


class LibrosaAcousticExtractor:
    """
    Acoustic feature extraction service using Librosa.
    
    Adheres to blueprint specification:
    Audio Track -> Librosa Spectrogram Extractor -> PyTorch AASIST Classifier.
    
    Extracts:
    1. Log-scale Mel-spectrograms (80 filter banks)
    2. Fundamental frequency (F0) and pitch variance via YIN
    3. Phase continuity and STFT phase divergence
    4. Spectral statistics (centroid, bandwidth, rolloff, zero-crossing rate)
    5. Audio splicing boundary transitions via spectral flux
    """

    def __init__(
        self,
        target_sample_rate: int = settings.AUDIO_SAMPLE_RATE,
        max_duration_seconds: int = settings.AUDIO_MAX_DURATION_SECONDS,
        max_size_bytes: int = settings.MAX_AUDIO_SIZE_BYTES,
    ):
        self.target_sample_rate = target_sample_rate
        self.max_duration_seconds = max_duration_seconds
        self.max_size_bytes = max_size_bytes

    def _resolve_audio(
        self,
        audio: Union[DecodedAudio, np.ndarray],
        sample_rate: Optional[int] = None,
    ) -> Tuple[np.ndarray, int]:
        """Helper extracting numpy array and sample rate from either DecodedAudio or raw array."""
        if isinstance(audio, DecodedAudio):
            return audio.waveform, audio.sample_rate
        y = np.asarray(audio, dtype=np.float32)
        sr = sample_rate if sample_rate is not None else self.target_sample_rate
        return y, sr

    def load_audio(self, audio_path: str) -> DecodedAudio:
        """
        Safely reads and normalizes audio file into a mono float32 waveform.
        
        Args:
            audio_path: Local filesystem path to audio asset
            
        Returns:
            DecodedAudio containing normalized waveform, sample rate, and duration.
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            raise ValueError("Audio payload is empty (0 bytes).")
        if file_size > self.max_size_bytes:
            raise ValueError(
                f"Audio file size ({file_size} bytes) exceeds maximum limit ({self.max_size_bytes} bytes)."
            )

        try:
            # Load with librosa, resampling to target 16kHz mono
            y, sr = librosa.load(
                audio_path,
                sr=self.target_sample_rate,
                mono=True,
                duration=self.max_duration_seconds
            )
        except Exception as e:
            raise ValueError(f"Failed to decode audio container or codec: {e}")

        if len(y) == 0:
            raise ValueError("Decoded audio stream contains zero audio frames.")

        # Peak normalization
        max_amp = float(np.max(np.abs(y)))
        if max_amp > 1e-6:
            y = y / max_amp

        duration = len(y) / float(sr)
        return DecodedAudio(waveform=y, sample_rate=sr, duration_seconds=duration)

    def decode_audio(
        self,
        audio_path: str,
        target_sr: Optional[int] = None,
        max_duration: Optional[float] = None,
    ) -> DecodedAudio:
        """Alias for load_audio with optional override of sample rate and max duration."""
        original_sr = self.target_sample_rate
        original_dur = self.max_duration_seconds
        if target_sr is not None:
            self.target_sample_rate = target_sr
        if max_duration is not None:
            self.max_duration_seconds = int(max_duration)
        try:
            return self.load_audio(audio_path)
        finally:
            self.target_sample_rate = original_sr
            self.max_duration_seconds = original_dur

    def extract_mel_spectrogram(
        self,
        audio: Union[DecodedAudio, np.ndarray],
        sample_rate: Optional[int] = None,
        n_fft: int = 1024,
        hop_length: int = 512,
        n_mels: int = 80,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts Mel-spectrogram and converts to decibel (dB) scale.
        
        Returns:
            mel: Raw power Mel-spectrogram [n_mels, time_frames]
            mel_db: Log-scaled decibel Mel-spectrogram [n_mels, time_frames]
        """
        y, sr = self._resolve_audio(audio, sample_rate)

        mel = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
            fmax=sr // 2
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)
        return mel, mel_db

    def extract_log_mel_spectrogram(
        self,
        audio: Union[DecodedAudio, np.ndarray],
        sample_rate: Optional[int] = None,
        n_fft: int = 1024,
        hop_length: int = 512,
        n_mels: int = 80,
    ) -> np.ndarray:
        """Returns 80-band log Mel-spectrogram in decibels."""
        _, mel_db = self.extract_mel_spectrogram(
            audio=audio,
            sample_rate=sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
        )
        return mel_db

    def compute_pitch_variance(
        self,
        audio: Union[DecodedAudio, np.ndarray],
        sample_rate: Optional[int] = None,
        fmin: float = 50.0,
        fmax: float = 500.0,
        hop_length: int = 512,
    ) -> Tuple[float, float]:
        """
        Estimates fundamental frequency (F0) trajectory and pitch variance via YIN algorithm.
        
        Returns:
            pitch_mean: Average fundamental frequency across voiced frames (Hz)
            pitch_variance: Variance of fundamental frequency across voiced frames
        """
        y, sr = self._resolve_audio(audio, sample_rate)

        # Guard against very short audio or silence
        if len(y) < 2048 or float(np.max(np.abs(y))) < 1e-5:
            return 0.0, 0.0

        try:
            f0 = librosa.yin(
                y,
                fmin=fmin,
                fmax=fmax,
                sr=sr,
                frame_length=2048,
                hop_length=hop_length
            )
            # Filter unvoiced or invalid estimation frames
            voiced = f0[~np.isnan(f0) & ~np.isinf(f0) & (f0 > fmin) & (f0 < fmax)]
            if len(voiced) == 0:
                return 0.0, 0.0

            pitch_mean = float(np.mean(voiced))
            pitch_var = float(np.var(voiced))
            return round(pitch_mean, 2), round(pitch_var, 2)
        except Exception:
            return 0.0, 0.0

    # Alias for pitch and variance
    compute_pitch_and_variance = compute_pitch_variance

    def compute_phase_discontinuity(
        self,
        audio: Union[DecodedAudio, np.ndarray],
        sample_rate: Optional[int] = None,
        n_fft: int = 1024,
        hop_length: int = 512,
    ) -> float:
        """
        Measures phase incoherence across consecutive STFT frames.
        Neural vocoders and splice seams frequently introduce high second-order phase derivative variance.
        
        Returns:
            Bounded phase discontinuity score in [0.0, 1.0].
        """
        y, _ = self._resolve_audio(audio, sample_rate)
        if len(y) < n_fft:
            return 0.10

        stft = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
        phase = np.angle(stft)

        if phase.shape[1] < 3:
            return 0.10

        # Unwrapped phase differences across temporal frames
        phase_diff = np.diff(phase, axis=1)
        phase_accel = np.diff(phase_diff, axis=1)
        mean_accel = float(np.mean(np.abs(phase_accel)))

        # Normalize metric: typical values range from 1.0 to 3.5
        norm_score = float(np.clip((mean_accel - 1.2) / 1.5, 0.0, 1.0))
        return round(norm_score, 4)

    def extract_spectral_features(
        self,
        audio: Union[DecodedAudio, np.ndarray],
        sample_rate: Optional[int] = None,
        hop_length: int = 512,
    ) -> Dict[str, float]:
        """Extracts statistical summary of spectral shape features."""
        y, sr = self._resolve_audio(audio, sample_rate)

        if len(y) < 1024:
            return {
                "spectral_centroid_mean": 0.0,
                "spectral_bandwidth_mean": 0.0,
                "spectral_rolloff_mean": 0.0,
                "zero_crossing_rate_mean": 0.0,
            }

        centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)
        zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=hop_length)

        return {
            "spectral_centroid_mean": round(float(np.mean(centroid)), 2),
            "spectral_bandwidth_mean": round(float(np.mean(bandwidth)), 2),
            "spectral_rolloff_mean": round(float(np.mean(rolloff)), 2),
            "zero_crossing_rate_mean": round(float(np.mean(zcr)), 4),
        }

    # Alias for spectral features
    compute_spectral_features = extract_spectral_features

    def detect_splice_boundaries(
        self,
        audio: Union[DecodedAudio, np.ndarray],
        sample_rate: Optional[int] = None,
        hop_length: int = 512,
        threshold_quantile: float = 0.96,
    ) -> List[AudioSpliceMarker]:
        """
        Detects suspected audio splice boundaries via spectral flux and energy onset jumps.
        
        Returns:
            List of AudioSpliceMarker sorted chronologically.
        """
        y, sr = self._resolve_audio(audio, sample_rate)

        if len(y) < 2048:
            return []

        # Onset strength represents spectral flux between frames
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        if len(onset_env) == 0:
            return []

        q_val = float(np.quantile(onset_env, threshold_quantile))
        std_val = float(np.std(onset_env))
        min_peak = max(1.5, q_val + 0.5 * std_val)

        # Detect prominent onset peaks
        peaks = librosa.util.peak_pick(
            onset_env,
            pre_max=5,
            post_max=5,
            pre_avg=7,
            post_avg=7,
            delta=min_peak * 0.4,
            wait=10  # Minimum 10 frames (~0.32s) between detected splice boundaries
        )

        markers: List[AudioSpliceMarker] = []
        max_onset = float(np.max(onset_env)) if np.max(onset_env) > 0 else 1.0

        for p in peaks:
            timestamp = float(librosa.frames_to_time(p, sr=sr, hop_length=hop_length))
            score = float(np.clip(onset_env[p] / max_onset, 0.0, 1.0))
            if score >= 0.60:
                markers.append(AudioSpliceMarker(
                    timestamp_seconds=round(timestamp, 3),
                    score=round(score, 4),
                    reason="SPECTRAL_FLUX_JUMP" if score >= 0.75 else "ACOUSTIC_ENERGY_TRANSITION"
                ))

        return markers
