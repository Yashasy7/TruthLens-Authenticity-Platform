import os
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Optional
from ..config import settings


class VideoDeepfake3DCNNNet(nn.Module):
    """
    PyTorch 3D-CNN Spatiotemporal Neural Network for face-swap deepfake detection.
    
    Adheres to blueprint specification:
    Video File -> FFmpeg Sampler -> RetinaFace Detector -> PyTorch 3D-CNN -> Video Deepfake Score.
    
    Architecture:
    Operates on 5D spatiotemporal tensors [Batch, Channels, Time, Height, Width].
    Convolves spatial feature boundaries and temporal frame-to-frame continuity simultaneously
    using 3D convolutional kernels (torch.nn.Conv3d).
    """

    def __init__(self):
        super().__init__()
        torch.manual_seed(42)

        # Stage 1: Spatial downsampling while preserving temporal continuity
        self.conv1 = nn.Conv3d(3, 32, kernel_size=(3, 3, 3), stride=1, padding=(1, 1, 1))
        self.bn1 = nn.BatchNorm3d(32)
        self.pool1 = nn.MaxPool3d(kernel_size=(1, 2, 2), stride=(1, 2, 2))  # [B, 32, T, 56, 56]

        # Stage 2: Spatiotemporal feature extraction
        self.conv2 = nn.Conv3d(32, 64, kernel_size=(3, 3, 3), stride=1, padding=(1, 1, 1))
        self.bn2 = nn.BatchNorm3d(64)
        self.pool2 = nn.MaxPool3d(kernel_size=(2, 2, 2), stride=(2, 2, 2))  # [B, 64, T/2, 28, 28]

        # Stage 3: High-level anomaly synthesis
        self.conv3 = nn.Conv3d(64, 128, kernel_size=(3, 3, 3), stride=1, padding=(1, 1, 1))
        self.bn3 = nn.BatchNorm3d(128)
        self.pool3 = nn.MaxPool3d(kernel_size=(2, 2, 2), stride=(2, 2, 2))  # [B, 128, T/4, 14, 14]

        # Stage 4: Deep spatiotemporal representations
        self.conv4 = nn.Conv3d(128, 256, kernel_size=(3, 3, 3), stride=1, padding=(1, 1, 1))
        self.bn4 = nn.BatchNorm3d(256)

        # Spatiotemporal global pooling collapses [B, 256, T', H', W'] -> [B, 256, 1, 1, 1]
        self.global_pool = nn.AdaptiveAvgPool3d((1, 1, 1))

        # Binary deepfake classifier head
        self.fc = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, 1)
        )

        self._init_weights()

    def _init_weights(self):
        torch.manual_seed(42)
        for m in self.modules():
            if isinstance(m, nn.Conv3d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm3d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass over 5D spatiotemporal tensor.
        
        Args:
            x: Tensor of shape [B, 3, T, H, W]
        """
        x = self.pool1(F.relu(self.bn1(self.conv1(x))))
        x = self.pool2(F.relu(self.bn2(self.conv2(x))))
        x = self.pool3(F.relu(self.bn3(self.conv3(x))))
        x = F.relu(self.bn4(self.conv4(x)))
        x = self.global_pool(x)
        x = torch.flatten(x, 1)
        return self.fc(x)


class VideoDeepfakeInferenceService:
    """
    Orchestrates 3D-CNN deepfake inference on temporal sequences of face crops.
    """

    def __init__(
        self,
        model_path: str = settings.VIDEO_MODEL_PATH,
        device_name: str = settings.DEVICE,
        sequence_length: int = settings.VIDEO_SEQUENCE_LENGTH,
    ):
        self.device = torch.device(device_name if torch.cuda.is_available() and device_name == "cuda" else "cpu")
        self.sequence_length = max(2, sequence_length)
        self.model = VideoDeepfake3DCNNNet().to(self.device)
        self.model_name = "TruthLens-PyTorch-3DCNN-DeepfakeClassifier"
        self.model_version = "0.1.0-dev"
        self.is_production_checkpoint = False

        if model_path:
            if not os.path.isfile(model_path):
                raise FileNotFoundError(f"Configured video deepfake model checkpoint not found: {model_path}")
            try:
                state_dict = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.is_production_checkpoint = True
                self.model_version = "1.0.0-prod"
            except Exception as e:
                raise RuntimeError(f"Failed to load video deepfake checkpoint from {model_path}: {e}")

        self.model.eval()

    def score_face_sequence(self, crops_rgb: List[np.ndarray]) -> float:
        """
        Runs PyTorch 3D-CNN inference on a temporal sequence of face crops.
        
        Args:
            crops_rgb: Chronological list of face crop RGB arrays for a single tracked subject.
            
        Returns:
            Spatiotemporal deepfake probability bounded in [0.0, 1.0].
        """
        if not crops_rgb:
            return 0.05

        # Standardize sequence to exact target length T
        standardized_crops: List[np.ndarray] = []
        if len(crops_rgb) >= self.sequence_length:
            # Take most recent T observations
            standardized_crops = crops_rgb[-self.sequence_length:]
        else:
            # Pad deterministically by replicating the latest crop
            standardized_crops = list(crops_rgb)
            last_crop = crops_rgb[-1]
            while len(standardized_crops) < self.sequence_length:
                standardized_crops.append(last_crop)

        # Preprocess each frame into standard dimensions [112, 112]
        processed_frames = []
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)

        for crop in standardized_crops:
            resized = cv2.resize(crop, (112, 112), interpolation=cv2.INTER_AREA)
            norm = (resized.astype(np.float32) / 255.0 - mean) / std
            # Transpose to [C, H, W]
            norm_chw = np.transpose(norm, (2, 0, 1))
            processed_frames.append(norm_chw)

        # Stack into [C, T, H, W] then add batch dimension -> [1, C, T, H, W]
        # Shape of sequence: [T, C, H, W] -> transpose to [C, T, H, W]
        seq_array = np.stack(processed_frames, axis=0)  # [T, C, H, W]
        seq_array = np.transpose(seq_array, (1, 0, 2, 3))  # [C, T, H, W]
        tensor5d = torch.from_numpy(seq_array).unsqueeze(0).to(self.device)  # [1, C, T, H, W]

        with torch.no_grad():
            logit = self.model(tensor5d)
            prob = float(torch.sigmoid(logit).item())

        return float(np.clip(prob, 0.0, 1.0))

    def score_face_crop(self, face_rgb: np.ndarray) -> float:
        """
        Backward-compatible helper evaluating a single frame crop via 3D-CNN spatiotemporal volume.
        """
        return self.score_face_sequence([face_rgb])


# Backward-compatible alias for 3D-CNN architecture
VideoDeepfakeClassifierNet = VideoDeepfake3DCNNNet

