from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, status, Form
from fastapi.responses import JSONResponse
from .config import settings
from .schemas import HealthResponse, ImageAnalysisResult, ImageAnalysisEvidence
from .utils.image_io import load_image_from_bytes, to_torch_tensor
from .services.model_inference import ModelInferenceService
from .services.ela_generator import ElaGenerator
from .services.noise_analyzer import NoiseAnalyzer
from .services.frequency_analyzer import FrequencyAnalyzer
from .services.local_manipulation import LocalManipulationDetector
from .services.video_pipeline import VideoAnalysisPipeline
from .services.audio_pipeline import AudioAnalysisPipeline
from .services.av_sync_pipeline import AvSyncAnalysisPipeline
from .services.ocr_pipeline import OcrAnalysisPipeline
from .services.transcript_pipeline import TranscriptPipeline
from .services.claim_extractor import ClaimExtractor
from .schemas import (
    HealthResponse,
    ImageAnalysisResult,
    ImageAnalysisEvidence,
    VideoAnalysisResult,
    AudioAnalysisResult,
    AvSyncAnalysisResult,
    OcrAnalysisResult,
    TranscriptResult,
    ClaimAnalysisRequest,
    ClaimAnalysisResult,
)
import tempfile
import os

# Singletons initialized at startup or lazily on demand
model_service: ModelInferenceService | None = None
ela_generator: ElaGenerator | None = None
noise_analyzer: NoiseAnalyzer | None = None
frequency_analyzer: FrequencyAnalyzer | None = None
manipulation_detector: LocalManipulationDetector | None = None
video_pipeline: VideoAnalysisPipeline | None = None
audio_pipeline: AudioAnalysisPipeline | None = None
av_sync_pipeline: AvSyncAnalysisPipeline | None = None
ocr_pipeline: OcrAnalysisPipeline | None = None
transcript_pipeline: TranscriptPipeline | None = None
claim_extractor: ClaimExtractor | None = None


def init_services():
    global model_service, ela_generator, noise_analyzer, frequency_analyzer, manipulation_detector, video_pipeline, audio_pipeline, av_sync_pipeline, ocr_pipeline, transcript_pipeline, claim_extractor
    if model_service is None:
        model_service = ModelInferenceService()
    if ela_generator is None:
        ela_generator = ElaGenerator()
    if noise_analyzer is None:
        noise_analyzer = NoiseAnalyzer()
    if frequency_analyzer is None:
        frequency_analyzer = FrequencyAnalyzer()
    if manipulation_detector is None:
        manipulation_detector = LocalManipulationDetector()
    if video_pipeline is None:
        video_pipeline = VideoAnalysisPipeline()
    if audio_pipeline is None:
        audio_pipeline = AudioAnalysisPipeline()
    if av_sync_pipeline is None:
        av_sync_pipeline = AvSyncAnalysisPipeline()
    if ocr_pipeline is None:
        ocr_pipeline = OcrAnalysisPipeline()
    if transcript_pipeline is None:
        transcript_pipeline = TranscriptPipeline()
    if claim_extractor is None:
        claim_extractor = ClaimExtractor()



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_services()
    yield


app = FastAPI(
    title="TruthLens AI/ML Service",
    description="Multi-Modal Image, Video, Audio, AV Sync & OCR Text Extraction Authenticity Forensics (Modules 05, 06, 07, 08, 09)",
    version="0.5.0",
    lifespan=lifespan
)


@app.get("/api/v1/health", response_model=HealthResponse)
def health_check():
    """Healthcheck endpoint for backend readiness and device telemetry."""
    init_services()
    return HealthResponse(
        status="UP",
        device=str(model_service.device),
        model_loaded=True,
        model_name=model_service.model_name,
        model_version=model_service.model_version
    )


@app.post("/api/v1/analyze/image", response_model=ImageAnalysisResult)
async def analyze_image(file: UploadFile = File(...)):
    """
    Executes dual-engine image authenticity analysis on uploaded image:
    1. AI Generation analysis via PyTorch Diffusion Classifier + Grad-CAM
    2. Localized physical manipulation analysis via ELA, noise inconsistency, FFT, and copy-move clustering
    """
    init_services()
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media content type: '{file.content_type}'. Must be an image."
        )

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

        # 1. Safe image loading and boundary checks
        img_rgb = load_image_from_bytes(content)
        h, w = img_rgb.shape[:2]

        # 2. PyTorch model inference & Grad-CAM attention
        tensor = to_torch_tensor(img_rgb)
        ai_prob, gradcam_base64 = model_service.predict_and_explain(tensor, img_rgb)

        # 3. OpenCV Error Level Analysis (ELA)
        _, ela_base64, ela_stats = ela_generator.generate_ela(img_rgb)

        # 4. Noise variance & spatial inconsistency analysis
        noise_stats = noise_analyzer.analyze_noise(img_rgb)

        # 5. 2D FFT spectral frequency analysis
        freq_stats = frequency_analyzer.analyze_frequency(img_rgb)

        # 6. Local manipulation (Copy-Move & Splicing)
        manip_stats = manipulation_detector.detect_manipulation(
            img_rgb,
            noise_inconsistency=noise_stats["noise_inconsistency_score"],
            ela_max_error=ela_stats["ela_max_error"]
        )

        evidence = ImageAnalysisEvidence(
            noise_variance=noise_stats["noise_variance"],
            noise_inconsistency_score=noise_stats["noise_inconsistency_score"],
            fft_anomaly_score=freq_stats["fft_anomaly_score"],
            copy_move_detected=manip_stats["copy_move_detected"],
            splicing_detected=manip_stats["splicing_detected"],
            image_width=w,
            image_height=h,
            details={
                "ela": ela_stats,
                "noise": noise_stats,
                "frequency": freq_stats,
                "manipulation": manip_stats
            }
        )

        return ImageAnalysisResult(
            ai_prob=round(ai_prob, 4),
            manipulation_prob=manip_stats["manipulation_prob"],
            noise_variance=noise_stats["noise_variance"],
            fft_anomaly_score=freq_stats["fft_anomaly_score"],
            copy_move_detected=manip_stats["copy_move_detected"],
            splicing_detected=manip_stats["splicing_detected"],
            model_name=model_service.model_name,
            model_version=model_service.model_version,
            ela_heatmap_base64=ela_base64,
            gradcam_heatmap_base64=gradcam_base64,
            evidence=evidence,
            status="COMPLETED"
        )

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image analysis pipeline failure: {str(e)}"
        )


@app.post("/api/v1/analyze/video", response_model=VideoAnalysisResult)
async def analyze_video(file: UploadFile = File(...)):
    """
    Executes deepfake and forensic video analysis (Module 06):
    1. Deterministic frame sampling via FFmpeg / OpenCV
    2. RetinaFace face detection and temporal tracking
    3. PyTorch 3D-CNN / EfficientNet deepfake model inference
    4. Temporal frame inconsistency and optical flow analysis
    5. Suspicious timestamp marker generation
    """
    init_services()
    if file.content_type and not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media content type: '{file.content_type}'. Must be a video."
        )

    # Save incoming stream into a secure temporary video file
    suffix = ".mp4"
    if file.filename and "." in file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in [".mp4", ".mov", ".avi", ".webm", ".mkv", ".mpeg"]:
            suffix = ext

    fd, temp_video_path = tempfile.mkstemp(prefix="truthlens_video_upload_", suffix=suffix)
    os.close(fd)

    try:
        total_bytes = 0
        with open(temp_video_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_VIDEO_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Video exceeds maximum allowed size ({settings.MAX_VIDEO_SIZE_BYTES} bytes)."
                    )
                out_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded video file is empty.")

        # Execute analysis pipeline
        result = video_pipeline.analyze_video(temp_video_path)
        return result

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video analysis pipeline failure: {str(e)}"
        )
    finally:
        if os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except OSError:
                pass


@app.post("/api/v1/analyze/audio", response_model=AudioAnalysisResult)
async def analyze_audio(file: UploadFile = File(...)):
    """
    Executes acoustic authenticity and voice forensic analysis (Module 07):
    1. 80-band Mel-spectrogram extraction via Librosa
    2. Fundamental frequency (F0) & pitch variance estimation via YIN
    3. STFT phase discontinuity calculation
    4. Spectral statistics & splice boundary detection
    5. PyTorch AASIST Spectro-Temporal Graph Attention Network classification
    6. Audio authenticity & voice cloning probability generation
    """
    init_services()
    if file.content_type and not (
        file.content_type.startswith("audio/")
        or file.content_type.startswith("video/")
        or file.content_type in ["application/octet-stream"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media content type: '{file.content_type}'. Must be an audio or video format."
        )

    suffix = ".wav"
    if file.filename and "." in file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in [".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".mp4", ".mov", ".mkv"]:
            suffix = ext

    fd, temp_audio_path = tempfile.mkstemp(prefix="truthlens_audio_upload_", suffix=suffix)
    os.close(fd)

    try:
        total_bytes = 0
        with open(temp_audio_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_AUDIO_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Audio exceeds maximum allowed size ({settings.MAX_AUDIO_SIZE_BYTES} bytes)."
                    )
                out_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded audio file is empty.")

        result = audio_pipeline.analyze_audio(temp_audio_path)
        return result

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio analysis pipeline failure: {str(e)}"
        )
    finally:
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except OSError:
                pass


@app.post("/api/v1/analyze/av-sync", response_model=AvSyncAnalysisResult)
async def analyze_av_sync(file: UploadFile = File(...)):
    """
    Executes Audio-Video Synchronization Analysis (Module 08):
    1. Deterministic video frame sampling & MediaPipe lip tracking
    2. Video audio track extraction & acoustic envelope calculation
    3. Audio-visual envelope cross-correlation across temporal shifts
    4. SyncNet dual-stream (visual CNN + audio CNN) cross-modal embedding distance evaluation
    5. Overall sync score, lip_offset_ms, and mismatch segment detection
    """
    init_services()
    if file.content_type and not (
        file.content_type.startswith("video/")
        or file.content_type in ["application/octet-stream"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media content type: '{file.content_type}'. Must be a video format containing audio."
        )

    suffix = ".mp4"
    if file.filename and "." in file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in [".mp4", ".mov", ".avi", ".webm", ".mkv", ".mpeg"]:
            suffix = ext

    fd, temp_video_path = tempfile.mkstemp(prefix="truthlens_avsync_upload_", suffix=suffix)
    os.close(fd)

    try:
        total_bytes = 0
        with open(temp_video_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_VIDEO_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Video exceeds maximum allowed size ({settings.MAX_VIDEO_SIZE_BYTES} bytes)."
                    )
                out_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded video file is empty.")

        result = av_sync_pipeline.analyze_video(temp_video_path)
        return result

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AV sync analysis pipeline failure: {str(e)}"
        )
    finally:
        if os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except OSError:
                pass


@app.post("/api/v1/analyze/ocr", response_model=OcrAnalysisResult)
async def analyze_ocr(file: UploadFile = File(...)):
    """
    Executes Optical Character Recognition & Visual Text Extraction (Module 09):
    1. Binarization & contrast preprocessing (CLAHE, bilateral denoising, deskewing)
    2. Multi-backend OCR inference (EasyOCR, Tesseract, morphological fallback)
    3. Spatial bounding box and polygon coordinate extraction
    4. Temporal tracking & deduplication across video keyframes
    5. Aggregated text strings, confidence scores, and explainable evidence
    """
    init_services()
    if file.content_type and not (
        file.content_type.startswith("image/")
        or file.content_type.startswith("video/")
        or file.content_type in ["application/octet-stream"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media content type: '{file.content_type}'. Must be an image or video format."
        )

    # Determine extension
    suffix = ".png"
    if file.filename and "." in file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".mp4", ".mov", ".avi", ".webm", ".mkv"]:
            suffix = ext

    fd, temp_file_path = tempfile.mkstemp(prefix="truthlens_ocr_upload_", suffix=suffix)
    os.close(fd)

    try:
        total_bytes = 0
        with open(temp_file_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_VIDEO_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Uploaded media exceeds maximum allowed size ({settings.MAX_VIDEO_SIZE_BYTES} bytes)."
                    )
                out_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded media file is empty.")

        # Ingest into OCR pipeline
        result = ocr_pipeline.analyze(temp_file_path)
        return result

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR analysis pipeline failure: {str(e)}"
        )
    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass


@app.post("/api/v1/analyze/speech-to-text", response_model=TranscriptResult)
async def analyze_speech_to_text(
    file: UploadFile = File(...),
    language: str | None = Form(None),
):
    """
    Executes Automated Speech Recognition & Transcript Extraction (Module 10):
    1. Demuxes/standardizes input audio/video into 16kHz mono PCM WAV.
    2. Enforces duration boundaries and detects silent speech tracks.
    3. Runs Faster-Whisper ASR inference with language and word-level timestamps.
    4. Computes normalized segment confidence scores.
    5. Returns structured TranscriptResult JSON.
    """
    init_services()
    if file.content_type and not (
        file.content_type.startswith("audio/")
        or file.content_type.startswith("video/")
        or file.content_type in ["application/octet-stream"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media content type: '{file.content_type}'. Must be an audio or video format."
        )

    # Determine extension
    suffix = ".wav"
    if file.filename and "." in file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".mp4", ".mov", ".avi", ".webm", ".mkv"]:
            suffix = ext

    fd, temp_file_path = tempfile.mkstemp(prefix="truthlens_stt_upload_", suffix=suffix)
    os.close(fd)

    try:
        total_bytes = 0
        with open(temp_file_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_VIDEO_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Uploaded media exceeds maximum allowed size ({settings.MAX_VIDEO_SIZE_BYTES} bytes)."
                    )
                out_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded media file is empty.")

        # Ingest into STT pipeline
        result = transcript_pipeline.analyze(temp_file_path, language=language)
        return result

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech-to-text pipeline failure: {str(e)}"
        )
    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass


@app.post("/api/v1/analyze/claims", response_model=ClaimAnalysisResult)
async def analyze_claims(request: ClaimAnalysisRequest):
    """
    Executes Text & Claim Analysis (Module 11):
    1. Validates input text boundary conditions and character limits.
    2. Runs spaCy Named Entity Recognition (NER) across standard categories.
    3. Segments and classifies statements (FACTUAL_CLAIM, OPINION, QUESTION, NON_CLAIM, UNCERTAIN).
    4. Decomposes claims into semantic Subject, Action, and Value components.
    5. Computes canonical normalized representation and collision-resistant SHA-256 claim hash.
    6. Returns structured ClaimAnalysisResult JSON.
    """
    init_services()
    if request.text is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text field cannot be null.")

    if len(request.text) > settings.CLAIM_MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input text length ({len(request.text)} chars) exceeds maximum allowed limit ({settings.CLAIM_MAX_TEXT_LENGTH} chars)."
        )

    try:
        result = claim_extractor.analyze(
            text=request.text,
            source_type=request.source_type,
            language=request.language,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text & claim analysis pipeline failure: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ai-ml.app.main:app", host=settings.HOST, port=settings.PORT, reload=False)


