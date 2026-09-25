import os
import torch
import torch.nn as nn
import numpy as np
from ..config import settings
from .gradcam_exporter import GradCamExporter


class DiffusionClassifierNet(nn.Module):
    """
    Convolutional Neural Network architecture designed for synthetic image discrimination.
    Extracts spatial frequency and convolutional edge features characteristic of Diffusion/GAN models.
    """

    def __init__(self):
        super().__init__()
        # Establish deterministic generator for reproducible development baseline weights
        torch.manual_seed(42)

        # Initial receptive field
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.relu1 = nn.ReLU(inplace=True)
        self.pool1 = nn.MaxPool2d(2, 2)  # 224 -> 112

        # Mid-level features
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.relu2 = nn.ReLU(inplace=True)
        self.pool2 = nn.MaxPool2d(2, 2)  # 112 -> 56

        # Deep high-level feature extraction (Target layer for Grad-CAM)
        self.target_conv = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.relu3 = nn.ReLU(inplace=True)
        self.pool3 = nn.MaxPool2d(2, 2)  # 56 -> 28

        # Global pooling & classification head
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(64, 1)
        )

        self._init_weights()

    def _init_weights(self):
        # Seed generator for reproducible development baseline weights
        torch.manual_seed(42)
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool1(self.relu1(self.bn1(self.conv1(x))))
        x = self.pool2(self.relu2(self.bn2(self.conv2(x))))
        x = self.pool3(self.relu3(self.bn3(self.target_conv(x))))
        x = self.global_pool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x


class ModelInferenceService:
    """
    Encapsulates PyTorch vision model inference, tensor lifecycle, and Grad-CAM extraction.
    """

    def __init__(self, model_path: str = settings.MODEL_PATH, device_name: str = settings.DEVICE):
        self.device = torch.device(device_name if torch.cuda.is_available() and device_name == "cuda" else "cpu")
        self.model = DiffusionClassifierNet().to(self.device)
        self.gradcam_exporter = GradCamExporter()

        self.model_name = "TruthLens-DiffusionClassifier"
        self.model_version = "0.1.0-dev"
        self.is_production_checkpoint = False

        if model_path and os.path.isfile(model_path):
            try:
                state_dict = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.is_production_checkpoint = True
                self.model_version = "1.0.0-prod"
            except Exception as e:
                # Log error and maintain functional dev baseline
                print(f"Warning: Failed to load model weights from {model_path}: {e}")

        self.model.eval()

        # Hooks storage for Grad-CAM
        self.activations: torch.Tensor | None = None
        self.gradients: torch.Tensor | None = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0]

        self.model.target_conv.register_forward_hook(forward_hook)
        self.model.target_conv.register_full_backward_hook(backward_hook)

    def predict_and_explain(self, tensor: torch.Tensor, img_rgb: np.ndarray) -> tuple[float, str]:
        """
        Runs model inference to compute AI probability and generates Grad-CAM attention heatmap.
        
        Args:
            tensor: Preprocessed normalized tensor [1, 3, 224, 224]
            img_rgb: Original image array for heatmap overlay
            
        Returns:
            ai_prob: Probability in [0.0, 1.0] that image is AI-generated
            gradcam_base64: Base64-encoded PNG attention heatmap
        """
        tensor = tensor.to(self.device).requires_grad_(True)
        self.model.zero_grad()

        # Forward pass
        logit = self.model(tensor)
        prob = float(torch.sigmoid(logit).item())
        ai_prob = float(np.clip(prob, 0.0, 1.0))

        # Backward pass with respect to logit to obtain gradients on target_conv
        logit.backward()

        gradcam_base64 = ""
        if self.activations is not None and self.gradients is not None:
            _, gradcam_base64 = self.gradcam_exporter.generate_gradcam_overlay(
                img_rgb=img_rgb,
                feature_activations=self.activations,
                feature_gradients=self.gradients
            )

        return ai_prob, gradcam_base64
