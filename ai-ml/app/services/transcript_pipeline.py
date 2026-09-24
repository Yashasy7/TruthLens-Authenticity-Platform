import os
from typing import Optional
from ..config import settings
from ..schemas import TranscriptResult, TranscriptEvidence
from .speech_preprocessor import SpeechPreprocessor, PreprocessedAudio
from .speech_transcriber import SpeechTranscriber


class TranscriptPipeline:
    """
    End-to-end Automated Speech Recognition & Transcript Pipeline (Module 10).
    
    Coordinates:
    1. Demuxing/Resampling media (Audio or Video) to 16kHz mono WAV.
    2. Silence & duration checking.
    3. Faster-Whisper ASR inference with word-level timestamps.
    4. Segment consolidation and evidence generation.
    5. Clean lifecycle management of temporary WAV assets.
    """

    def __init__(
        self,
        preprocessor: Optional[SpeechPreprocessor] = None,
        transcriber: Optional[SpeechTranscriber] = None,
    ):
        self.preprocessor = preprocessor or SpeechPreprocessor()
        self.transcriber = transcriber or SpeechTranscriber()

    def analyze(
        self,
        media_path: str,
        media_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> TranscriptResult:
        """
        Executes complete speech-to-text pipeline on audio or video asset.
        
        Args:
            media_path: Local filesystem path to the uploaded media file.
            media_type: Explicit media type hint ('AUDIO' or 'VIDEO').
            language: Optional language code hint (e.g. 'en'). Auto-detect if None.
            
        Returns:
            Structured TranscriptResult.
            
        Raises:
            ValueError: If media file is invalid, corrupt, or exceeds limits.
        """
        if not os.path.isfile(media_path):
            raise ValueError(f"Media file not found: {media_path}")

        ext = os.path.splitext(media_path)[1].lower()
        video_exts = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".mpeg", ".flv"}
        inferred_type = "VIDEO" if (media_type == "VIDEO" or ext in video_exts) else "AUDIO"

        preprocessed: Optional[PreprocessedAudio] = None
        try:
            # 1. Preprocess / demux media to 16kHz mono WAV
            preprocessed = self.preprocessor.preprocess(media_path, media_type=inferred_type)

            # 2. Transcribe speech using Faster-Whisper
            full_text, detected_lang, confidence, segments, words_count, details = self.transcriber.transcribe(
                audio_path=preprocessed.wav_path,
                language=language,
                is_silent=preprocessed.is_silent,
            )

            # 3. Assemble forensic evidence
            evidence = TranscriptEvidence(
                model_name="Faster-Whisper",
                model_size=self.transcriber.model_size_or_path,
                compute_type=self.transcriber.compute_type,
                device=self.transcriber.device,
                detected_language=detected_lang,
                language_probability=details.get("language_probability", 1.0),
                duration_seconds=preprocessed.duration_seconds,
                audio_sample_rate=preprocessed.sample_rate,
                media_type=inferred_type,
                details=details,
            )

            return TranscriptResult(
                full_text=full_text,
                language=detected_lang,
                confidence_score=confidence,
                duration_seconds=preprocessed.duration_seconds,
                segments_count=len(segments),
                words_count=words_count,
                segments=segments,
                evidence=evidence,
                status="COMPLETED",
                error_message=None,
            )

        except Exception as e:
            # Re-raise clean error
            raise ValueError(f"Speech-to-text pipeline failure: {str(e)}") from e

        finally:
            if preprocessed is not None:
                preprocessed.cleanup()
