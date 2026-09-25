"""
TruthLens AI/ML — Grad-CAM Attention Exporter
Blueprint: Module 05 — "Grad-CAM attention exporter"
           Module 16 — React HTML Canvas heatmap overlay renderer (consumer)

Grad-CAM (Gradient-weighted Class Activation Mapping) produces a spatial
attention map that highlights the image regions most influential for the
model's synthetic-probability prediction.  This feeds Module 16
(Explainable Dashboard) as a PNG overlay.

Implementation note:
  We use a manual gradient hook approach (no external grad-cam library) to
  stay within the blueprint-approved dependency list.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class GradCAMHook:
    """
    Context-manager that registers forward and backward hooks on a target layer
    to capture activations and gradients for Grad-CAM computation.
    """

    def __init__(self, layer: nn.Module) -> None:
        self.activations: Optional[torch.Tensor] = None
        self.gradients: Optional[torch.Tensor] = None
        self._forward_hook = layer.register_forward_hook(self._save_activation)
        self._backward_hook = layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(
        self,
        _module: nn.Module,
        _input: Tuple,
        output: torch.Tensor,
    ) -> None:
        self.activations = output.detach()

    def _save_gradient(
        self,
        _module: nn.Module,
        _grad_input: Tuple,
        grad_output: Tuple,
    ) -> None:
        self.gradients = grad_output[0].detach()

    def remove(self) -> None:
        self._forward_hook.remove()
        self._backward_hook.remove()


def _get_last_conv_layer(model: nn.Module) -> Optional[nn.Module]:
    """
    Find the last Conv2d layer in the model graph.
    This is the default Grad-CAM target layer for EfficientNet/ResNet backbones.
    """
    last_conv: Optional[nn.Module] = None
    for module in model.modules():
        if isinstance(module, nn.Conv2d):
            last_conv = module
    return last_conv


def generate_gradcam(
    model: nn.Module,
    image_tensor: torch.Tensor,
    original_size: Tuple[int, int],
    target_layer: Optional[nn.Module] = None,
) -> np.ndarray:
    """
    Generate a Grad-CAM attention overlay for the given image tensor.

    Args:
        model:          PyTorch model in eval mode.
        image_tensor:   (1, 3, H, W) preprocessed tensor.
        original_size:  (width, height) of the original image for upsampling.
        target_layer:   nn.Module to hook. Defaults to the last Conv2d layer.

    Returns:
        uint8 numpy array (H, W, 3) BGR colour-mapped Grad-CAM overlay
        resized to original_size.

    Raises:
        RuntimeError: if no Conv2d layer is found or gradients are unavailable.
    """
    if target_layer is None:
        target_layer = _get_last_conv_layer(model)
    if target_layer is None:
        raise RuntimeError("No Conv2d layer found in model for Grad-CAM.")

    hook = GradCAMHook(target_layer)

    # Enable grad temporarily (model is normally in no_grad / eval mode)
    model.eval()
    tensor = image_tensor.clone().requires_grad_(True)

    try:
        output: torch.Tensor = model(tensor)   # (1, 1) sigmoid output
        model.zero_grad()
        output.backward(torch.ones_like(output))  # backprop synthetic class

        if hook.activations is None or hook.gradients is None:
            raise RuntimeError("Grad-CAM hooks did not capture activations/gradients.")

        # Global average pooling of gradients → channel weights
        weights = hook.gradients.mean(dim=(2, 3), keepdim=True)   # (1, C, 1, 1)
        cam = (weights * hook.activations).sum(dim=1, keepdim=False)  # (1, H', W')
        cam = cam.squeeze(0)  # (H', W')

        # ReLU: keep only positive contributions
        cam = torch.clamp(cam, min=0.0)

        cam_np = cam.cpu().numpy()
        max_val = cam_np.max()
        if max_val > 0:
            cam_np = cam_np / max_val
        cam_uint8 = (cam_np * 255).astype(np.uint8)

        # Upsample to original image size (W, H)
        orig_w, orig_h = original_size
        cam_resized = cv2.resize(cam_uint8, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

        # Apply JET colour map for consistency with ELA heatmap
        cam_colour = cv2.applyColorMap(cam_resized, cv2.COLORMAP_JET)

        logger.debug("Grad-CAM generated | output_size=(%d, %d)", orig_w, orig_h)
        return cam_colour

    finally:
        hook.remove()
