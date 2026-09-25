import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Dict, Any, Optional
from ..config import settings


class GraphAttentionLayer(nn.Module):
    """
    Graph Attention Layer (GAT) for spectro-temporal graph representation.
    Applies self-attention across graph nodes to model non-local acoustic dependencies.
    """

    def __init__(self, in_features: int, out_features: int, dropout: float = 0.1, alpha: float = 0.2):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.dropout = nn.Dropout(dropout)
        self.alpha = alpha

        self.W = nn.Linear(in_features, out_features, bias=False)
        self.a = nn.Parameter(torch.empty(size=(2 * out_features, 1)))
        nn.init.xavier_uniform_(self.a.data, gain=1.414)
        nn.init.xavier_uniform_(self.W.weight, gain=1.414)

        self.leakyrelu = nn.LeakyReLU(self.alpha)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        """
        Forward pass for Graph Attention Layer.
        Args:
            h: Node feature tensor [Batch, NumNodes, in_features]
        Returns:
            Updated node representations [Batch, NumNodes, out_features]
        """
        batch_size, num_nodes, _ = h.shape
        Wh = self.W(h)  # [B, N, out_features]

        # Compute pairwise attention coefficients
        Wh1 = Wh.unsqueeze(2).repeat(1, 1, num_nodes, 1)  # [B, N, N, out_features]
        Wh2 = Wh.unsqueeze(1).repeat(1, num_nodes, 1, 1)  # [B, N, N, out_features]
        all_combinations = torch.cat([Wh1, Wh2], dim=-1)  # [B, N, N, 2 * out_features]

        # Attention logits e_ij
        e = self.leakyrelu(torch.matmul(all_combinations, self.a).squeeze(-1))  # [B, N, N]

        attention = F.softmax(e, dim=-1)
        attention = self.dropout(attention)

        # Output aggregation: [B, N, N] x [B, N, out_features] -> [B, N, out_features]
        h_prime = torch.matmul(attention, Wh)
        return F.elu(h_prime + Wh)  # Residual connection with ELU activation


class AASISTClassifierNet(nn.Module):
    """
    AASIST (Audio Anti-Spoofing using Integrated Spectro-Temporal Graph Attention Networks).
    
    Blueprint specification:
    Audio Track -> Librosa Spectrogram Extractor -> PyTorch AASIST Classifier -> Mel-Spectrogram Image + Voice Cloning Probability.
    
    Architecture:
    1. Sinc/Convolutional front-end extracting spectro-temporal feature maps from raw waveform.
    2. Temporal Graph Attention Network (Temporal-GAT) modeling frame-to-frame speech dynamics.
    3. Spectral Graph Attention Network (Spectral-GAT) modeling inter-harmonic frequency distributions.
    4. Graph Readout Module combining maximum and mean pooling across both graphs.
    5. Multi-layer perceptron classification head computing bonafide vs. synthetic/spoofed probability.
    """

    def __init__(self, node_dim: int = 64):
        super().__init__()
        torch.manual_seed(42)
        self.node_dim = node_dim

        # 1. Front-end 1D convolutional feature extractor on raw audio waveform
        self.conv1 = nn.Conv1d(1, 32, kernel_size=128, stride=4, padding=64)
        self.bn1 = nn.BatchNorm1d(32)
        self.pool1 = nn.MaxPool1d(4)

        self.conv2 = nn.Conv1d(32, 64, kernel_size=16, stride=2, padding=8)
        self.bn2 = nn.BatchNorm1d(64)
        self.pool2 = nn.MaxPool1d(4)

        self.conv3 = nn.Conv1d(64, node_dim, kernel_size=8, stride=2, padding=4)
        self.bn3 = nn.BatchNorm1d(node_dim)
        self.pool3 = nn.MaxPool1d(2)

        # 2. Temporal GAT: nodes are time frames
        self.temporal_gat = GraphAttentionLayer(in_features=node_dim, out_features=node_dim)

        # 3. Spectral GAT: projection to spectral graph nodes
        self.spectral_proj = nn.Linear(node_dim, node_dim)
        self.spectral_gat = GraphAttentionLayer(in_features=node_dim, out_features=node_dim)

        # 4. Classification Head operating on concatenated graph readouts
        # Concatenation of [TempMax, TempMean, SpecMax, SpecMean] -> 4 * node_dim
        self.fc = nn.Sequential(
            nn.Linear(node_dim * 4, 128),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.2),
            nn.Linear(64, 2)  # 2 classes: [bonafide, spoof]
        )

        self._init_weights()

    def _init_weights(self):
        torch.manual_seed(42)
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass for AASIST architecture.
        Args:
            x: Raw audio waveform tensor [Batch, 1, NumSamples] or [Batch, NumSamples]
        Returns:
            Logits tensor [Batch, 2] where index 0=bonafide, index 1=spoofed/synthetic
        """
        if x.dim() == 2:
            x = x.unsqueeze(1)  # [B, 1, L]

        # 1. Front-end 1D convolutions
        feat = self.pool1(F.leaky_relu(self.bn1(self.conv1(x)), 0.2))
        feat = self.pool2(F.leaky_relu(self.bn2(self.conv2(feat)), 0.2))
        feat = self.pool3(F.leaky_relu(self.bn3(self.conv3(feat)), 0.2))  # [B, node_dim, T]

        # Ensure we have at least 2 temporal nodes
        if feat.shape[-1] < 2:
            feat = F.pad(feat, (0, 2 - feat.shape[-1]))

        # 2. Temporal Graph Attention
        # Nodes: [B, T, node_dim]
        h_temp = feat.transpose(1, 2)  # [B, T, node_dim]
        # Cap max temporal nodes to avoid O(T^2) memory explosion for long audio
        if h_temp.shape[1] > 128:
            step = h_temp.shape[1] // 128
            h_temp = h_temp[:, ::step, :][:, :128, :]

        temp_out = self.temporal_gat(h_temp)  # [B, T', node_dim]
        temp_max = torch.max(temp_out, dim=1)[0]   # [B, node_dim]
        temp_mean = torch.mean(temp_out, dim=1)    # [B, node_dim]

        # 3. Spectral Graph Attention
        # Nodes: [B, node_dim, node_dim]
        # Pool temporal dimension T' to node_dim so that spectral nodes have dimension node_dim
        h_spec = F.adaptive_avg_pool1d(temp_out.transpose(1, 2), self.node_dim)  # [B, node_dim, node_dim]
        h_spec = self.spectral_proj(h_spec)  # [B, node_dim, node_dim]
        spec_out = self.spectral_gat(h_spec)  # [B, node_dim, node_dim]
        spec_max = torch.max(spec_out, dim=1)[0]   # [B, node_dim]
        spec_mean = torch.mean(spec_out, dim=1)    # [B, node_dim]

        # 4. Graph Readout & Classification
        readout = torch.cat([temp_max, temp_mean, spec_max, spec_mean], dim=-1)  # [B, 4 * node_dim]
        logits = self.fc(readout)  # [B, 2]
        return logits


class AudioAuthenticityInferenceService:
    """
    Orchestrates PyTorch AASIST inference for audio deepfake and synthetic voice detection.
    """

    def __init__(
        self,
        model_path: str = settings.AUDIO_MODEL_PATH,
        device_name: str = settings.DEVICE,
    ):
        self.device = torch.device(device_name if torch.cuda.is_available() and device_name == "cuda" else "cpu")
        self.model = AASISTClassifierNet().to(self.device)
        self.model_name = "TruthLens-PyTorch-AASIST-AudioClassifier"
        self.model_version = "0.1.0-dev"
        self.is_production_checkpoint = False

        if model_path:
            if not os.path.isfile(model_path):
                raise FileNotFoundError(f"Configured audio authenticity model checkpoint not found: {model_path}")
            try:
                state_dict = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.is_production_checkpoint = True
                self.model_version = "1.0.0-prod"
            except Exception as e:
                raise RuntimeError(f"Failed to load audio authenticity checkpoint from {model_path}: {e}")

        self.model.eval()

    def predict_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[float, Dict[str, Any]]:
        """
        Runs AASIST graph attention network inference on audio waveform.

        Args:
            audio_data: 1D numpy array of audio samples (float32).
            sample_rate: Audio sampling frequency in Hz.

        Returns:
            synthetic_voice_prob: Probability in [0.0, 1.0] that speech is synthetic/cloned.
            details: Dictionary containing inference metadata.
        """
        if audio_data is None or len(audio_data) == 0:
            return 0.05, {"samples_analyzed": 0, "inference_status": "EMPTY_AUDIO"}

        # Subsample or window to a representative segment if audio is very long
        # Standard AASIST evaluation segment: 64,600 samples (~4 seconds at 16kHz)
        target_samples = 64600
        if len(audio_data) > target_samples:
            # Take central segment to capture dominant vocal content
            start_idx = (len(audio_data) - target_samples) // 2
            eval_audio = audio_data[start_idx : start_idx + target_samples]
        elif len(audio_data) < 1600:  # less than 0.1s
            # Pad audio to minimum viable sample size
            eval_audio = np.pad(audio_data, (0, 1600 - len(audio_data)), mode="wrap")
        else:
            eval_audio = audio_data

        tensor = torch.from_numpy(eval_audio.astype(np.float32)).unsqueeze(0).to(self.device)  # [1, L]

        with torch.no_grad():
            logits = self.model(tensor)  # [1, 2]
            probabilities = F.softmax(logits, dim=-1)  # [1, 2]
            # Index 1 corresponds to synthetic/spoofed speech class
            synthetic_prob = float(probabilities[0, 1].item())

        synthetic_prob = float(np.clip(synthetic_prob, 0.0, 1.0))
        details = {
            "samples_analyzed": len(eval_audio),
            "sample_rate": sample_rate,
            "device": str(self.device),
            "is_production_checkpoint": self.is_production_checkpoint,
        }

        return synthetic_prob, details
