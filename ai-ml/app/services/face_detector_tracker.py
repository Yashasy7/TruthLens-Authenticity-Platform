import os
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from ..config import settings


class DetectedFace:
    """Represents a localized facial detection with bounding box, confidence, and landmarks."""
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        confidence: float,
        track_id: int = -1,
        landmarks: Optional[List[Tuple[float, float]]] = None
    ):
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.confidence = round(float(confidence), 4)
        self.track_id = int(track_id)
        self.landmarks = landmarks  # [(x1, y1), (x2, y2), ...] 5 key facial points

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height

    @property
    def center(self) -> Tuple[float, float]:
        return self.x + self.width / 2.0, self.y + self.height / 2.0

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "track_id": self.track_id,
        }
        if self.landmarks is not None:
            data["landmarks"] = [[round(pt[0], 2), round(pt[1], 2)] for pt in self.landmarks]
        return data


# =============================================================================
# PyTorch RetinaFace Model Architecture (MobileNet0.25 Backbone + FPN + SSH)
# =============================================================================

def conv_bn(inp: int, oup: int, stride: int = 1, leaky: float = 0.1) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(inp, oup, 3, stride, 1, bias=False),
        nn.BatchNorm2d(oup),
        nn.LeakyReLU(negative_slope=leaky, inplace=True)
    )


def conv_dw(inp: int, oup: int, stride: int, leaky: float = 0.1) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(inp, inp, 3, stride, 1, groups=inp, bias=False),
        nn.BatchNorm2d(inp),
        nn.LeakyReLU(negative_slope=leaky, inplace=True),
        nn.Conv2d(inp, oup, 1, 1, 0, bias=False),
        nn.BatchNorm2d(oup),
        nn.LeakyReLU(negative_slope=leaky, inplace=True),
    )


class MobileNetV1(nn.Module):
    """MobileNet-0.25 feature extractor backbone for RetinaFace."""
    def __init__(self):
        super().__init__()
        self.stage1 = nn.Sequential(
            conv_bn(3, 8, 2, leaky=0.1),
            conv_dw(8, 16, 1),
            conv_dw(16, 32, 2),
            conv_dw(32, 32, 1),
            conv_dw(32, 64, 2),
            conv_dw(64, 64, 1),
        )
        self.stage2 = nn.Sequential(
            conv_dw(64, 128, 2),
            conv_dw(128, 128, 1),
            conv_dw(128, 128, 1),
            conv_dw(128, 128, 1),
            conv_dw(128, 128, 1),
            conv_dw(128, 128, 1),
        )
        self.stage3 = nn.Sequential(
            conv_dw(128, 256, 2),
            conv_dw(256, 256, 1),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        out1 = self.stage1(x)
        out2 = self.stage2(out1)
        out3 = self.stage3(out2)
        return out1, out2, out3


class FPN(nn.Module):
    """Feature Pyramid Network fusing multi-scale feature hierarchies."""
    def __init__(self, in_channels_list: List[int], out_channels: int = 64):
        super().__init__()
        self.output1 = nn.Conv2d(in_channels_list[0], out_channels, 1, 1, 0)
        self.output2 = nn.Conv2d(in_channels_list[1], out_channels, 1, 1, 0)
        self.output3 = nn.Conv2d(in_channels_list[2], out_channels, 1, 1, 0)
        self.merge1 = nn.Conv2d(out_channels, out_channels, 3, 1, 1)
        self.merge2 = nn.Conv2d(out_channels, out_channels, 3, 1, 1)

    def forward(self, input_features: Tuple[torch.Tensor, torch.Tensor, torch.Tensor]) -> List[torch.Tensor]:
        output1 = self.output1(input_features[0])
        output2 = self.output2(input_features[1])
        output3 = self.output3(input_features[2])

        up3 = F.interpolate(output3, size=output2.shape[2:], mode="nearest")
        output2 = output2 + up3
        output2 = self.merge2(output2)

        up2 = F.interpolate(output2, size=output1.shape[2:], mode="nearest")
        output1 = output1 + up2
        output1 = self.merge1(output1)

        return [output1, output2, output3]


class SSH(nn.Module):
    """Single Stage Head context module extending receptive fields."""
    def __init__(self, in_channel: int = 64, out_channel: int = 64):
        super().__init__()
        assert out_channel % 4 == 0
        self.conv3X3 = nn.Sequential(
            nn.Conv2d(in_channel, out_channel // 2, 3, 1, 1),
            nn.BatchNorm2d(out_channel // 2)
        )
        self.conv5X5_1 = nn.Sequential(
            nn.Conv2d(in_channel, out_channel // 4, 3, 1, 1),
            nn.BatchNorm2d(out_channel // 4),
            nn.LeakyReLU(negative_slope=0.1, inplace=True)
        )
        self.conv5X5_2 = nn.Sequential(
            nn.Conv2d(out_channel // 4, out_channel // 4, 3, 1, 1),
            nn.BatchNorm2d(out_channel // 4)
        )
        self.conv7X7_2 = nn.Sequential(
            nn.Conv2d(out_channel // 4, out_channel // 4, 3, 1, 1),
            nn.BatchNorm2d(out_channel // 4),
            nn.LeakyReLU(negative_slope=0.1, inplace=True)
        )
        self.conv7X7_3 = nn.Sequential(
            nn.Conv2d(out_channel // 4, out_channel // 4, 3, 1, 1),
            nn.BatchNorm2d(out_channel // 4)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        conv3X3 = self.conv3X3(x)
        conv5X5_1 = self.conv5X5_1(x)
        conv5X5 = self.conv5X5_2(conv5X5_1)
        conv7X7_2 = self.conv7X7_2(conv5X5_1)
        conv7X7 = self.conv7X7_3(conv7X7_2)
        out = torch.cat([conv3X3, conv5X5, conv7X7], dim=1)
        return F.relu(out)


class ClassHead(nn.Module):
    def __init__(self, in_channels: int = 64, num_anchors: int = 2):
        super().__init__()
        self.conv1x1 = nn.Conv2d(in_channels, num_anchors * 2, 1, 1, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv1x1(x)
        out = out.permute(0, 2, 3, 1).contiguous()
        return out.view(out.shape[0], -1, 2)


class BboxHead(nn.Module):
    def __init__(self, in_channels: int = 64, num_anchors: int = 2):
        super().__init__()
        self.conv1x1 = nn.Conv2d(in_channels, num_anchors * 4, 1, 1, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv1x1(x)
        out = out.permute(0, 2, 3, 1).contiguous()
        return out.view(out.shape[0], -1, 4)


class LandmarkHead(nn.Module):
    def __init__(self, in_channels: int = 64, num_anchors: int = 2):
        super().__init__()
        self.conv1x1 = nn.Conv2d(in_channels, num_anchors * 10, 1, 1, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv1x1(x)
        out = out.permute(0, 2, 3, 1).contiguous()
        return out.view(out.shape[0], -1, 10)


class RetinaFaceNet(nn.Module):
    """
    RetinaFace PyTorch Neural Network.
    
    Implements Deng et al., 'RetinaFace: Single-stage Multi-box Face Localisation in the Wild'.
    Outputs multi-scale bounding box regressions, classification confidences, and 5-point facial landmarks.
    """
    def __init__(self):
        super().__init__()
        self.body = MobileNetV1()
        self.fpn = FPN([64, 128, 256], 64)
        self.ssh1 = SSH(64, 64)
        self.ssh2 = SSH(64, 64)
        self.ssh3 = SSH(64, 64)
        self.ClassHead = nn.ModuleList([ClassHead(64, 2), ClassHead(64, 2), ClassHead(64, 2)])
        self.BboxHead = nn.ModuleList([BboxHead(64, 2), BboxHead(64, 2), BboxHead(64, 2)])
        self.LandmarkHead = nn.ModuleList([LandmarkHead(64, 2), LandmarkHead(64, 2), LandmarkHead(64, 2)])
        self._init_weights()

    def _init_weights(self):
        torch.manual_seed(42)
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        features = self.body(x)
        fpn = self.fpn(features)
        pyramid = [self.ssh1(fpn[0]), self.ssh2(fpn[1]), self.ssh3(fpn[2])]
        bbox_reg = torch.cat([self.BboxHead[i](feat) for i, feat in enumerate(pyramid)], dim=1)
        class_reg = torch.cat([self.ClassHead[i](feat) for i, feat in enumerate(pyramid)], dim=1)
        landm_reg = torch.cat([self.LandmarkHead[i](feat) for i, feat in enumerate(pyramid)], dim=1)
        return bbox_reg, class_reg, landm_reg


# =============================================================================
# Anchor Generation, Box Decoding, and Non-Maximum Suppression (NMS)
# =============================================================================

def generate_prior_boxes(image_height: int, image_width: int) -> torch.Tensor:
    """Generates dense multi-scale anchor boxes across 3 pyramid levels."""
    min_sizes = [[16, 32], [64, 128], [256, 512]]
    steps = [8, 16, 32]
    anchors = []
    for k, step in enumerate(steps):
        feature_h = int(np.ceil(image_height / step))
        feature_w = int(np.ceil(image_width / step))
        for i in range(feature_h):
            for j in range(feature_w):
                for min_size in min_sizes[k]:
                    s_kx = min_size / image_width
                    s_ky = min_size / image_height
                    dense_cx = (j + 0.5) * step / image_width
                    dense_cy = (i + 0.5) * step / image_height
                    anchors.append([dense_cx, dense_cy, s_kx, s_ky])
    return torch.tensor(anchors, dtype=torch.float32)


def decode_boxes(loc: torch.Tensor, priors: torch.Tensor) -> torch.Tensor:
    """Decodes bounding box offsets into normalized [x1, y1, x2, y2] coordinates."""
    variances = [0.1, 0.2]
    boxes = torch.cat((
        priors[:, :2] + loc[:, :2] * variances[0] * priors[:, 2:],
        priors[:, 2:] * torch.exp(loc[:, 2:] * variances[1])
    ), 1)
    x1y1 = boxes[:, :2] - (boxes[:, 2:] / 2)
    x2y2 = x1y1 + boxes[:, 2:]
    return torch.cat([x1y1, x2y2], dim=1)


def decode_landmarks(landms: torch.Tensor, priors: torch.Tensor) -> torch.Tensor:
    """Decodes 5-point facial landmark offsets into normalized coordinates."""
    variances = [0.1, 0.2]
    pts = []
    for i in range(5):
        pt_x = priors[:, 0] + landms[:, 2 * i] * variances[0] * priors[:, 2]
        pt_y = priors[:, 1] + landms[:, 2 * i + 1] * variances[0] * priors[:, 3]
        pts.extend([pt_x.unsqueeze(1), pt_y.unsqueeze(1)])
    return torch.cat(pts, dim=1)


def py_nms(boxes: torch.Tensor, scores: torch.Tensor, iou_threshold: float = 0.40) -> List[int]:
    """Pure PyTorch vectorized Non-Maximum Suppression (NMS)."""
    if boxes.numel() == 0:
        return []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1).clamp(min=0) * (y2 - y1).clamp(min=0)
    order = scores.argsort(descending=True)
    keep = []
    while order.numel() > 0:
        i = order[0].item()
        keep.append(i)
        if order.numel() == 1:
            break
        xx1 = x1[order[1:]].clamp(min=x1[i])
        yy1 = y1[order[1:]].clamp(min=y1[i])
        xx2 = x2[order[1:]].clamp(max=x2[i])
        yy2 = y2[order[1:]].clamp(max=y2[i])
        w = (xx2 - xx1).clamp(min=0)
        h = (yy2 - yy1).clamp(min=0)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        inds = (ovr <= iou_threshold).nonzero().squeeze()
        if inds.numel() == 0:
            break
        if inds.dim() == 0:
            order = order[inds.item() + 1].unsqueeze(0)
        else:
            order = order[inds + 1]
    return keep


# =============================================================================
# RetinaFace Detector Service & Tracker
# =============================================================================

class RetinaFaceDetector:
    """
    RetinaFace PyTorch Face Detector.
    
    Executes genuine multi-scale face detection, bounding box regression,
    confidence scoring, and 5-point facial landmark localization.
    """
    def __init__(
        self,
        model_path: str = settings.RETINAFACE_MODEL_PATH,
        device_name: str = settings.DEVICE,
        confidence_threshold: float = 0.50,
        nms_threshold: float = 0.40,
    ):
        self.device = torch.device(device_name if torch.cuda.is_available() and device_name == "cuda" else "cpu")
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.detector_name = "RetinaFace-MobileNet0.25-PyTorch"
        self.model_version = "0.1.0-dev"
        self.is_production_checkpoint = False

        self.model = RetinaFaceNet().to(self.device)

        if model_path:
            # Check for illegal path traversal or non-existent files
            if not os.path.isfile(model_path):
                raise FileNotFoundError(f"Configured RetinaFace model checkpoint not found: {model_path}")
            try:
                state_dict = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.is_production_checkpoint = True
                self.model_version = "1.0.0-prod"
            except Exception as e:
                raise RuntimeError(f"Failed to load RetinaFace checkpoint from {model_path}: {e}")

        self.model.eval()

    def detect_faces(self, image_bgr: np.ndarray) -> List[DetectedFace]:
        """
        Executes genuine RetinaFace PyTorch inference on an image frame.
        
        Args:
            image_bgr: Input frame in BGR format
            
        Returns:
            List of DetectedFace instances with bounding box, confidence, and landmarks.
        """
        if image_bgr is None or image_bgr.size == 0:
            return []

        h, w = image_bgr.shape[:2]
        # Standard RetinaFace preprocessing: subtract channel means (104, 117, 123)
        img_float = np.float32(image_bgr)
        img_float -= (104.0, 117.0, 123.0)
        img_tensor = torch.from_numpy(img_float).permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.no_grad():
            loc, conf, landms = self.model(img_tensor)

        priors = generate_prior_boxes(h, w).to(self.device)
        boxes = decode_boxes(loc.data.squeeze(0), priors.data)
        landm_pts = decode_landmarks(landms.data.squeeze(0), priors.data)

        # Scale decoded coordinates to pixel dimensions
        scale = torch.tensor([w, h, w, h], dtype=torch.float32, device=self.device)
        boxes = boxes * scale
        scale_landm = torch.tensor([w, h] * 5, dtype=torch.float32, device=self.device)
        landm_pts = landm_pts * scale_landm

        scores = F.softmax(conf.data.squeeze(0), dim=-1)[:, 1]

        # Filter by confidence threshold
        keep_mask = scores > self.confidence_threshold
        if not keep_mask.any():
            return []

        filtered_boxes = boxes[keep_mask]
        filtered_scores = scores[keep_mask]
        filtered_landms = landm_pts[keep_mask]

        # Apply Non-Maximum Suppression (NMS)
        keep_indices = py_nms(filtered_boxes, filtered_scores, self.nms_threshold)
        if not keep_indices:
            return []

        detected_faces: List[DetectedFace] = []
        for idx in keep_indices:
            box = filtered_boxes[idx].cpu().numpy()
            score = float(filtered_scores[idx].cpu().item())
            lm_coords = filtered_landms[idx].cpu().numpy().reshape(5, 2)

            x1 = max(0, int(box[0]))
            y1 = max(0, int(box[1]))
            x2 = min(w, int(box[2]))
            y2 = min(h, int(box[3]))
            fw = max(1, x2 - x1)
            fh = max(1, y2 - y1)

            landmarks = [(float(lm_coords[k, 0]), float(lm_coords[k, 1])) for k in range(5)]

            detected_faces.append(DetectedFace(
                x=x1,
                y=y1,
                width=fw,
                height=fh,
                confidence=float(np.clip(score, 0.0, 1.0)),
                landmarks=landmarks
            ))

        return detected_faces


class RetinaFaceTracker:
    """
    RetinaFace face detector and spatial-temporal tracker.
    
    Adheres to blueprint specification:
    Video File -> FFmpeg Sampler -> RetinaFace Detector -> Spatial Tracker.
    """
    def __init__(
        self,
        detector: Optional[RetinaFaceDetector] = None,
        confidence_threshold: float = 0.50,
        max_track_distance: float = 80.0,
    ):
        self.detector = detector or RetinaFaceDetector(confidence_threshold=confidence_threshold)
        self.confidence_threshold = confidence_threshold
        self.max_track_distance = max_track_distance
        self.next_track_id = 1
        self.active_tracks: Dict[int, DetectedFace] = {}

    def detect_faces(self, image_bgr: np.ndarray) -> List[DetectedFace]:
        """Runs genuine RetinaFace detector on image."""
        return self.detector.detect_faces(image_bgr)

    def track_faces_in_frame(self, image_bgr: np.ndarray, frame_index: int) -> List[DetectedFace]:
        """
        Detects faces in current frame via RetinaFace and maintains continuous track IDs
        across video timeline.
        """
        detections = self.detect_faces(image_bgr)
        if not detections:
            return []

        if not self.active_tracks:
            for det in detections:
                det.track_id = self.next_track_id
                self.active_tracks[self.next_track_id] = det
                self.next_track_id += 1
            return detections

        unmatched = list(detections)
        matched_pairs: List[Tuple[int, DetectedFace]] = []

        for track_id, last_det in list(self.active_tracks.items()):
            best_match = None
            best_dist = float("inf")

            for det in unmatched:
                c1 = last_det.center
                c2 = det.center
                dist = np.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)
                iou = self._calculate_iou(last_det, det)

                if dist < self.max_track_distance or iou > 0.3:
                    if dist < best_dist:
                        best_dist = dist
                        best_match = det

            if best_match is not None:
                best_match.track_id = track_id
                matched_pairs.append((track_id, best_match))
                unmatched.remove(best_match)

        new_active: Dict[int, DetectedFace] = {}
        for track_id, det in matched_pairs:
            new_active[track_id] = det

        for det in unmatched:
            det.track_id = self.next_track_id
            new_active[self.next_track_id] = det
            self.next_track_id += 1

        self.active_tracks = new_active
        return detections

    @staticmethod
    def _calculate_iou(box1: DetectedFace, box2: DetectedFace) -> float:
        x1 = max(box1.x, box2.x)
        y1 = max(box1.y, box2.y)
        x2 = min(box1.x + box1.width, box2.x + box2.width)
        y2 = min(box1.y + box1.height, box2.y + box2.height)

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = box1.width * box1.height
        area2 = box2.width * box2.height
        union = area1 + area2 - intersection

        return float(intersection / (union + 1e-6))
