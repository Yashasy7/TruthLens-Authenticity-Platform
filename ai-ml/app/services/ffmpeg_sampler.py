import os
import shutil
import subprocess
import tempfile
import cv2
import numpy as np
from typing import List, Tuple
from ..config import settings


class SampledFrame:
    """Represents a deterministically sampled video frame."""
    def __init__(self, frame_index: int, timestamp_seconds: float, image_bgr: np.ndarray):
        self.frame_index = frame_index
        self.timestamp_seconds = round(timestamp_seconds, 3)
        self.image_bgr = image_bgr
        self.height, self.width = image_bgr.shape[:2]

    @property
    def image_rgb(self) -> np.ndarray:
        return cv2.cvtColor(self.image_bgr, cv2.COLOR_BGR2RGB)


class FFmpegVideoSampler:
    """
    FFmpeg-based deterministic video frame extraction pipeline.
    
    Adheres to blueprint specification:
    Video File -> FFmpeg Sampler -> Ordered Frame Array with Timestamps.
    
    Security controls:
    - Enforces argument arrays with no shell execution (prevents shell injection)
    - Validates path existence, permissions, and file size limits
    - Enforces process timeouts and resource boundaries
    - Gracefully falls back to OpenCV VideoCapture if ffmpeg binary is unavailable
    """

    def __init__(
        self,
        ffmpeg_path: str = settings.FFMPEG_PATH,
        sample_fps: float = settings.VIDEO_SAMPLE_FPS,
        max_frames: int = settings.VIDEO_MAX_FRAMES,
        max_duration_seconds: int = settings.VIDEO_MAX_DURATION_SECONDS,
        timeout_seconds: int = settings.VIDEO_PROCESSING_TIMEOUT_SECONDS,
    ):
        self.ffmpeg_path = ffmpeg_path
        self.sample_fps = max(0.1, sample_fps)
        self.max_frames = max_frames
        self.max_duration_seconds = max_duration_seconds
        self.timeout_seconds = timeout_seconds

    def sample_video(self, video_path: str) -> Tuple[List[SampledFrame], float]:
        """
        Extracts sampled frames from a video file in strict chronological order.
        
        Args:
            video_path: Local filesystem path to the video file
            
        Returns:
            frames: Chronologically sorted list of SampledFrame instances
            duration_seconds: Total duration of the analyzed video
        """
        if not os.path.isfile(video_path):
            raise ValueError(f"Video file not found: {video_path}")

        file_size = os.path.getsize(video_path)
        if file_size == 0:
            raise ValueError("Uploaded video payload is empty (0 bytes).")
        if file_size > settings.MAX_VIDEO_SIZE_BYTES:
            raise ValueError(
                f"Video file size ({file_size} bytes) exceeds maximum limit ({settings.MAX_VIDEO_SIZE_BYTES} bytes)."
            )

        # Attempt extraction via FFmpeg subprocess if available; fallback to OpenCV
        if self._is_ffmpeg_available():
            try:
                return self._sample_with_ffmpeg(video_path)
            except Exception as e:
                # Log and fallback to OpenCV
                return self._sample_with_opencv(video_path)
        else:
            return self._sample_with_opencv(video_path)

    def _is_ffmpeg_available(self) -> bool:
        if shutil.which(self.ffmpeg_path) is not None:
            return True
        return os.path.isfile(self.ffmpeg_path) and os.access(self.ffmpeg_path, os.X_OK)

    def _sample_with_ffmpeg(self, video_path: str) -> Tuple[List[SampledFrame], float]:
        """Executes FFmpeg with argument array into an isolated temporary folder."""
        temp_dir = tempfile.mkdtemp(prefix="truthlens_ffmpeg_")
        try:
            output_pattern = os.path.join(temp_dir, "frame_%05d.png")
            # Safe argument array without shell=True
            cmd = [
                self.ffmpeg_path,
                "-nostdin",
                "-hide_banner",
                "-loglevel", "error",
                "-i", os.path.abspath(video_path),
                "-t", str(self.max_duration_seconds),
                "-vf", f"fps={self.sample_fps}",
                "-vframes", str(self.max_frames),
                output_pattern
            ]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False
            )

            if process.returncode != 0:
                err_msg = process.stderr.decode("utf-8", errors="ignore").strip()
                raise RuntimeError(f"FFmpeg process error (code {process.returncode}): {err_msg}")

            # Collect extracted PNG frames
            files = sorted([f for f in os.listdir(temp_dir) if f.startswith("frame_") and f.endswith(".png")])
            if not files:
                raise ValueError("FFmpeg extracted 0 frames. Video may be corrupt or unreadable.")

            frames: List[SampledFrame] = []
            interval = 1.0 / self.sample_fps
            for idx, fname in enumerate(files):
                fpath = os.path.join(temp_dir, fname)
                img_bgr = cv2.imread(fpath)
                if img_bgr is not None:
                    timestamp = idx * interval
                    frames.append(SampledFrame(frame_index=idx, timestamp_seconds=timestamp, image_bgr=img_bgr))

            duration = len(frames) * interval
            return frames, round(duration, 3)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _sample_with_opencv(self, video_path: str) -> Tuple[List[SampledFrame], float]:
        """Fallback decoder using OpenCV VideoCapture."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Failed to open video file. Container or codec may be corrupt.")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0 or np.isnan(fps):
                fps = 25.0

            total_frames_in_video = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration_seconds = total_frames_in_video / fps if total_frames_in_video > 0 else 0.0

            # Calculate frame step for desired sampling rate
            frame_step = max(1, int(round(fps / self.sample_fps)))
            frames: List[SampledFrame] = []
            frame_idx = 0
            sample_idx = 0

            while cap.isOpened() and len(frames) < self.max_frames:
                ret, frame_bgr = cap.read()
                if not ret or frame_bgr is None:
                    break

                timestamp = frame_idx / fps
                if timestamp > self.max_duration_seconds:
                    break

                if frame_idx % frame_step == 0:
                    frames.append(SampledFrame(
                        frame_index=sample_idx,
                        timestamp_seconds=timestamp,
                        image_bgr=frame_bgr
                    ))
                    sample_idx += 1

                frame_idx += 1

            if not frames:
                raise ValueError("Could not extract any valid video frames. Video may be empty or corrupt.")

            actual_duration = round(duration_seconds if duration_seconds > 0 else (frame_idx / fps), 3)
            return frames, actual_duration

        finally:
            cap.release()
