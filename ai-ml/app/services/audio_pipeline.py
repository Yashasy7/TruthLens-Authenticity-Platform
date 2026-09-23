import os
import numpy as np
from typing import Optional
from ..config import settings
from ..schemas import (
    AudioAnalysisResult,
    AudioEvidence,
    AudioSpliceMarker,
)
from .librosa_extractor import LibrosaAcousticExtractor, DecodedAudio
from .aasist_classifier import AudioAuthenticityInferenceService
from .spectrogram_generator import SpectrogramGenerator


class AudioAnalysisPipeline:
    """
    End-to-end audio authenticity and voice forensic analysis pipeline.

    Adheres to blueprint specification:
    Audio Track -> Librosa Spectrogram Extractor -> PyTorch AASIST Classifier -> Mel-Spectrogram Image + Voice Cloning Probability.
    """

    def __init__(
        self,
        extractor: Optional[LibrosaAcousticExtractor] = None,
        classifier: Optional[AudioAuthenticityInferenceService] = None,
        spectrogram_generator: Optional[SpectrogramGenerator] = None,
    ):
        self.extractor = extractor or LibrosaAcousticExtractor()
        self.classifier = classifier or AudioAuthenticityInferenceService()
        self.spectrogram_generator = spectrogram_generator or SpectrogramGenerator()

    def analyze_audio(self, audio_path: str) -> AudioAnalysisResult:
        """
        Executes complete acoustic feature extraction, AASIST inference, and forensic evaluation.

        Args:
            audio_path: Local file path to audio or video media file.

        Returns:
            AudioAnalysisResult populated with synthetic voice probability, Mel-spectrogram artifact,
            pitch variance, and acoustic evidence.
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

        file_size = os.path.getsize(audio_path)
        if file_size > settings.MAX_AUDIO_SIZE_BYTES:
            raise ValueError(
                f"Audio file size ({file_size} bytes) exceeds maximum permitted limit ({settings.MAX_AUDIO_SIZE_BYTES} bytes)"
            )

        # 1. Decode & normalize audio waveform
        decoded: DecodedAudio = self.extractor.decode_audio(
            audio_path=audio_path,
            target_sr=settings.AUDIO_SAMPLE_RATE,
            max_duration=settings.AUDIO_MAX_DURATION_SECONDS,
        )

        if len(decoded.audio) == 0:
            raise ValueError("Decoded audio contains no audio samples.")

        # 2. Extract 80-band Log Mel-spectrogram
        mel_spectrogram_db = self.extractor.extract_log_mel_spectrogram(
            audio=decoded.audio,
            sample_rate=decoded.sample_rate,
        )

        # 3. Compute Fundamental Frequency (F0) & Pitch Variance via YIN
        f0_mean, f0_variance = self.extractor.compute_pitch_and_variance(
            audio=decoded.audio,
            sample_rate=decoded.sample_rate,
        )

        # 4. Compute Phase Discontinuity Metric from STFT phase derivative
        phase_discontinuity = self.extractor.compute_phase_discontinuity(decoded.audio)

        # 5. Extract Spectral Statistics (Centroid, Rolloff, Bandwidth, ZCR)
        spectral_metrics = self.extractor.compute_spectral_features(
            audio=decoded.audio,
            sample_rate=decoded.sample_rate,
        )

        # 6. Detect Audio Splicing Boundaries from Spectral Flux
        splice_markers = self.extractor.detect_splice_boundaries(
            audio=decoded.audio,
            sample_rate=decoded.sample_rate,
        )

        # 7. Render Mel-Spectrogram Image Artifact
        artifact_path, spectrogram_base64 = self.spectrogram_generator.generate_spectrogram_image(
            mel_spectrogram_db=mel_spectrogram_db,
            filename_prefix="audio_spectrogram",
        )

        # 8. Run PyTorch AASIST Spectro-Temporal Graph Attention Classifier
        aasist_prob, model_details = self.classifier.predict_audio(
            audio_data=decoded.audio,
            sample_rate=decoded.sample_rate,
        )

        # 9. Compute Pitch Anomaly Indicator
        # Natural human speech exhibits rich micro-prosody (pitch variance typically 100 - 2500 Hz^2).
        # Monotone/robotic synthetic voices exhibit unnaturally low pitch variance (< 40 Hz^2),
        # while poorly conditioned neural vocoders display erratic pitch jumps (> 3500 Hz^2).
        pitch_anomaly = 0.20
        if f0_mean > 0:
            if f0_variance < 35.0:
                pitch_anomaly = 0.75  # Monotone synthetic signature
            elif f0_variance > 3500.0:
                pitch_anomaly = 0.70  # Pitch discontinuity / vocoder glitching
            elif f0_variance < 80.0:
                pitch_anomaly = 0.50

        # 10. Synthesize Multi-Modal Voice Cloning Probability
        # Weighted ensemble: AASIST GAT (0.60) + Phase Discontinuity (0.25) + Pitch Anomaly (0.15)
        ensemble_score = (
            0.60 * aasist_prob
            + 0.25 * phase_discontinuity
            + 0.15 * pitch_anomaly
        )

        if splice_markers:
            # Splice penalty if spectral jumps are detected
            splice_penalty = min(0.10, 0.03 * len(splice_markers))
            ensemble_score = min(1.0, ensemble_score + splice_penalty)

        synthetic_voice_prob = float(np.clip(ensemble_score, 0.0, 1.0))

        # 11. Compile Detailed Acoustic Evidence
        evidence = AudioEvidence(
            duration_seconds=round(decoded.duration_seconds, 2),
            pitch_mean=round(f0_mean, 2),
            pitch_variance=round(f0_variance, 4),
            spectral_centroid_mean=round(spectral_metrics["spectral_centroid_mean"], 2),
            spectral_bandwidth_mean=round(spectral_metrics["spectral_bandwidth_mean"], 2),
            spectral_rolloff_mean=round(spectral_metrics["spectral_rolloff_mean"], 2),
            zero_crossing_rate_mean=round(spectral_metrics["zero_crossing_rate_mean"], 4),
            phase_discontinuity_score=round(phase_discontinuity, 4),
            splice_markers=splice_markers,
            details={
                "aasist_synthetic_score": round(aasist_prob, 4),
                "pitch_anomaly_score": round(pitch_anomaly, 4),
                "model_inference": model_details,
                "spectrogram_shape": list(mel_spectrogram_db.shape),
                "artifact_path": artifact_path,
            },
        )

        return AudioAnalysisResult(
            synthetic_voice_prob=round(synthetic_voice_prob, 4),
            spectrogram_url=artifact_path,
            spectrogram_base64=spectrogram_base64,
            pitch_variance=round(f0_variance, 4),
            splice_markers=splice_markers,
            model_name=self.classifier.model_name,
            model_version=self.classifier.model_version,
            evidence=evidence,
            status="COMPLETED",
        )
