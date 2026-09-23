from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, status
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
from .schemas import (
    HealthResponse,
    ImageAnalysisResult,
    ImageAnalysisEvidence,
    VideoAnalysisResult,
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


def init_services():
    global model_service, ela_generator, noise_analyzer, frequency_analyzer, manipulation_detector, video_pipeline
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_services()
    yield


app = FastAPI(
    title="TruthLens AI/ML Service",
    description="Dual-engine Image & Video Authenticity & Digital Forensics Analysis (Modules 05 & 06)",
    version="0.2.0",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ai-ml.app.main:app", host=settings.HOST, port=settings.PORT, reload=False)

