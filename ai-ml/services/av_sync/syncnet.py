"""
TruthLens AI/ML — Module 08: SyncNet Dual-Stream Audio-Visual Model Architecture
Blueprint: Dual-stream deep visual-acoustic temporal embedding network with Euclidean metric alignment.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from config.settings import get_settings

logger = logging.getLogger(__name__)


class SyncNetVisualNet(nn.Module):
    """
    Visual feature extractor processing 5 contiguous grayscale mouth crops.
    Input: (B, 5, 96, 96) -> Output: (B, 128) normalized embedding.
    """

    def __init__(self, embedding_dim: int = 128):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(5, 32, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 48x48
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 24x24
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 12x12
        )
        self.conv4 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),  # 256x1x1
        )
        self.fc = nn.Linear(256, embedding_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv1(x)
        out = self.conv2(out)
        out = self.conv3(out)
        out = self.conv4(out)
        out = out.flatten(1)
        out = self.fc(out)
        return F.normalize(out, p=2, dim=-1)


class SyncNetAudioNet(nn.Module):
    """
    Acoustic feature extractor processing a 20-frame log-Mel spectrogram window.
    Input: (B, 1, 80, 20) -> Output: (B, 128) normalized embedding.
    """

    def __init__(self, embedding_dim: int = 128):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 40x10
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 20x5
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 10x2
        )
        self.conv4 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),  # 256x1x1
        )
        self.fc = nn.Linear(256, embedding_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv1(x)
        out = self.conv2(out)
        out = self.conv3(out)
        out = self.conv4(out)
        out = out.flatten(1)
        out = self.fc(out)
        return F.normalize(out, p=2, dim=-1)


class SyncNetDualModel(nn.Module):
    """
    Dual-stream SyncNet model projecting synchronized visual and audio representations
    into a joint Euclidean metric space.
    """

    def __init__(self, embedding_dim: int = 128):
        super().__init__()
        self.visual_net = SyncNetVisualNet(embedding_dim=embedding_dim)
        self.audio_net = SyncNetAudioNet(embedding_dim=embedding_dim)

    def forward(
        self, visual_input: torch.Tensor, audio_input: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        v_embed = self.visual_net(visual_input)
        a_embed = self.audio_net(audio_input)
        return v_embed, a_embed

    @staticmethod
    def euclidean_distance(v_embed: torch.Tensor, a_embed: torch.Tensor) -> torch.Tensor:
        """
        Calculate pairwise Euclidean distance between normalized embeddings.
        Values range between 0.0 (identical) and 2.0 (opposite).
        """
        return torch.norm(v_embed - a_embed, p=2, dim=-1)


class SyncNetEvaluator:
    """
    Loads and runs inference with SyncNetDualModel for audio-visual synchronization evaluation.
    """

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        require_checkpoint: bool = False,
        device: Optional[str] = None,
    ):
        settings = get_settings()
        self.model_name = settings.av_sync_model_name
        self.model_version = settings.av_sync_model_version
        self.is_production_checkpoint = False

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Deterministic initialization for dev mode
        torch.manual_seed(42)
        self.model = SyncNetDualModel(embedding_dim=128)
        self.model.to(self.device)
        self.model.eval()

        target_checkpoint = checkpoint_path or settings.av_sync_classifier_checkpoint
        is_required = require_checkpoint or settings.require_av_sync_checkpoint

        if target_checkpoint and os.path.isfile(target_checkpoint):
            try:
                state_dict = torch.load(target_checkpoint, map_location=self.device)
                self.model.load_state_dict(state_dict, strict=True)
                self.is_production_checkpoint = True
                logger.info(f"Loaded production SyncNet checkpoint from {target_checkpoint}")
            except Exception as e:
                logger.error(f"Failed to load SyncNet checkpoint from {target_checkpoint}: {e}")
                if is_required:
                    raise RuntimeError(
                        f"Strict mode enabled: failed to load required SyncNet checkpoint {target_checkpoint}: {e}"
                    )
        elif is_required:
            raise FileNotFoundError(
                f"Strict mode enabled: required SyncNet checkpoint not found at '{target_checkpoint}'"
            )
        else:
            self.model_version = f"{settings.av_sync_model_version}-dev"
            logger.info("Operating in development mode with deterministic untrained SyncNet architecture")

    def evaluate_video_audio(
        self,
        mouth_crops: List[np.ndarray],
        log_mel: np.ndarray,
        fps: float = 25.0,
        max_shift_frames: int = 12,
    ) -> Dict[str, Any]:
        """
        Evaluate audio-visual alignment by sliding the audio stream across shift frames
        and computing pairwise Euclidean distances between visual and audio visemes.

        Args:
            mouth_crops: List of (96, 96) uint8 grayscale mouth crops.
            log_mel: (80, time_frames) log-Mel spectrogram matrix.
            fps: Video frame rate (default: 25.0).
            max_shift_frames: Search shift range in frames (default: 12 frames -> ~480 ms).

        Returns:
            Dict containing:
                best_shift_frames: Best shift in frames.
                best_offset_ms: Best offset in milliseconds.
                min_distance: Minimum Euclidean distance found.
                confidence: Prominence/confidence score [0.0, 1.0].
                shift_distances: Array of mean Euclidean distances per tested shift.
        """
        num_v_frames = len(mouth_crops)
        # Each visual chunk is 5 frames.
        # At 25 fps, 5 frames is 0.20s.
        # With 100 Hz Mel frame rate (e.g. sr=16000, hop=160 or hop=256),
        # 0.2s is 0.2 * (sr / hop) acoustic frames.
        # In M07: sr=16000, hop=256 -> 62.5 frames/sec. 0.20s is ~12-13 acoustic frames.
        # Standard SyncNet expects (80, 20) Mel chunks.
        # Let's derive audio chunks matching the center timestamp of the 5-frame visual window.
        
        if num_v_frames < 5 or log_mel.shape[1] < 20:
            return {
                "best_shift_frames": 0,
                "best_offset_ms": 0.0,
                "min_distance": 1.414,
                "confidence": 0.0,
                "shift_distances": np.array([1.414], dtype=np.float32),
            }

        # Subsample chunks: evaluate every 2 frames
        v_indices = list(range(0, num_v_frames - 5 + 1, 2))
        if not v_indices:
            v_indices = [0]

        # Prepare visual tensors: (N, 5, 96, 96) normalized to [-1, 1]
        v_chunks = []
        for idx in v_indices:
            # 5 frames
            stacked = np.stack(mouth_crops[idx : idx + 5], axis=0).astype(np.float32) / 127.5 - 1.0
            v_chunks.append(stacked)

        v_tensor = torch.from_numpy(np.stack(v_chunks, axis=0)).to(self.device)

        # Audio time resolution:
        # Mel time frames correspond to (n_mel_frames) over duration.
        # Map visual frame index to mel frame index:
        # mel_idx = int(round(v_idx * (mel_frames / v_frames)))
        mel_total = log_mel.shape[1]
        v_total = num_v_frames

        # Standardize log-mel values
        mel_mean = float(np.mean(log_mel))
        mel_std = float(np.std(log_mel)) if float(np.std(log_mel)) > 1e-4 else 1.0
        norm_mel = (log_mel - mel_mean) / mel_std

        # Extract visual embeddings once
        with torch.no_grad():
            v_embeds = self.model.visual_net(v_tensor)  # (N, 128)

        shifts = list(range(-max_shift_frames, max_shift_frames + 1))
        shift_distances = []

        audio_mel_chunk_len = 20  # fixed audio chunk temporal width
        half_mel_chunk = audio_mel_chunk_len // 2

        with torch.no_grad():
            for s in shifts:
                a_chunks = []
                valid_mask = []

                for i, v_idx in enumerate(v_indices):
                    # Center frame of visual window is v_idx + 2
                    center_v = v_idx + 2 + s
                    # Corresponding center in Mel frames:
                    center_mel = int(np.round(center_v * (mel_total / max(1, v_total))))
                    start_mel = center_mel - half_mel_chunk
                    end_mel = start_mel + audio_mel_chunk_len

                    if start_mel >= 0 and end_mel <= mel_total:
                        chunk = norm_mel[:, start_mel:end_mel]  # (80, 20)
                        a_chunks.append(chunk[np.newaxis, :, :])  # (1, 80, 20)
                        valid_mask.append(i)

                if len(a_chunks) >= 2:
                    a_tensor = torch.from_numpy(np.stack(a_chunks, axis=0)).to(self.device)
                    a_embeds = self.model.audio_net(a_tensor)
                    sub_v = v_embeds[valid_mask]
                    dists = self.model.euclidean_distance(sub_v, a_embeds)
                    shift_distances.append(float(dists.mean().cpu().item()))
                else:
                    shift_distances.append(1.414)

        dists_arr = np.array(shift_distances, dtype=np.float32)
        min_idx = int(np.argmin(dists_arr))
        best_shift = shifts[min_idx]
        frame_dur_ms = 1000.0 / fps
        best_offset_ms = round(float(best_shift * frame_dur_ms), 2)
        min_dist = round(float(dists_arr[min_idx]), 4)

        # Prominence of distance trough
        mean_dist = float(np.mean(dists_arr))
        prominence = max(0.0, mean_dist - min_dist)
        confidence = round(float(np.clip(prominence * 2.5, 0.0, 1.0)), 4)

        return {
            "best_shift_frames": best_shift,
            "best_offset_ms": best_offset_ms,
            "min_distance": min_dist,
            "confidence": confidence,
            "shift_distances": dists_arr,
        }
