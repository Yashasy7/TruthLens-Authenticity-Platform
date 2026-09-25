import base64
import cv2
import numpy as np
import torch


class GradCamExporter:
    """
    Grad-CAM (Gradient-weighted Class Activation Mapping) attention exporter.
    
    Generates explainable visual localization maps highlighting the specific
    spatial image regions that contributed most strongly to the model's AI-generation prediction.
    """

    def generate_gradcam_overlay(
        self,
        img_rgb: np.ndarray,
        feature_activations: torch.Tensor,
        feature_gradients: torch.Tensor,
        alpha: float = 0.5
    ) -> tuple[np.ndarray, str]:
        """
        Computes Grad-CAM heatmap and overlays it onto the original RGB image.
        
        Args:
            img_rgb: Original image array [H, W, 3] uint8
            feature_activations: Forward activations of target conv layer [1, C, H_feat, W_feat]
            feature_gradients: Backward gradients of target conv layer [1, C, H_feat, W_feat]
            alpha: Heatmap blend weight (0.0 = original only, 1.0 = heatmap only)
            
        Returns:
            overlay_bgr: Overlaid visualization image (BGR uint8)
            overlay_base64: Base64-encoded PNG string
        """
        h_orig, w_orig = img_rgb.shape[:2]

        # 1. Global average pooling of gradients to obtain channel importance weights alpha_k
        # gradients shape: [1, C, H, W] -> weights: [C]
        weights = torch.mean(feature_gradients, dim=[2, 3]).squeeze(0)

        # 2. Linear combination of feature maps weighted by alpha_k
        activations = feature_activations.squeeze(0)  # [C, H, W]
        cam = torch.zeros(activations.shape[1:], dtype=torch.float32, device=activations.device)
        for i, w in enumerate(weights):
            cam += w * activations[i]

        # 3. Apply ReLU: we are only interested in features that positively correlate with the AI class
        cam = torch.relu(cam)

        cam_np = cam.detach().cpu().numpy()
        # Handle zero or near-zero gradient edge cases
        cam_max = np.max(cam_np)
        if cam_max > 1e-7:
            cam_np = cam_np / cam_max
        else:
            cam_np = np.zeros_like(cam_np)

        # 4. Upsample CAM to original image dimensions
        cam_resized = cv2.resize(cam_np, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)
        cam_uint8 = np.uint8(255 * cam_resized)

        # 5. Apply JET pseudo-color map and blend with original image
        heatmap_bgr = cv2.applyColorMap(cam_uint8, cv2.COLORMAP_JET)
        orig_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

        overlay_bgr = cv2.addWeighted(orig_bgr, 1.0 - alpha, heatmap_bgr, alpha, 0)

        # 6. Encode as base64 PNG
        success, encoded_png = cv2.imencode(".png", overlay_bgr)
        overlay_base64 = base64.b64encode(encoded_png.tobytes()).decode("utf-8") if success else ""

        return overlay_bgr, overlay_base64
