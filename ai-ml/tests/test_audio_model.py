"""Tests for Module 07 AASIST-L audio classifier and checkpoint loading."""

import io
import math
import struct
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import torch

from services.audio_analysis.model import (
    AASISTLClassifier,
    AASIST_L_INPUT_SAMPLES,
    load_audio_classifier,
    pad_or_crop_waveform,
    predict_synthetic_voice_probability,
    reset_audio_model,
)
from services.audio_analysis.service import analyze_audio_bytes


def _make_sine_wav_bytes(duration_sec: float = 1.5, sample_rate: int = 16000, freq_hz: float = 220.0) -> bytes:
    n_samples = int(duration_sec * sample_rate)
    samples = [
        int(12000 * math.sin(2.0 * math.pi * freq_hz * i / sample_rate))
        for i in range(n_samples)
    ]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_samples}h", *samples))
    return buf.getvalue()


class TestPadOrCropWaveform:
    def test_short_waveform_is_tiled_to_64600(self):
        short = np.linspace(-0.5, 0.5, 16000, dtype=np.float32)
        out = pad_or_crop_waveform(short)
        assert out.shape == (AASIST_L_INPUT_SAMPLES,)
        assert out.dtype == np.float32
        assert np.allclose(out[:16000], short)

    def test_long_waveform_is_cropped_deterministically(self):
        long_wf = np.arange(80000, dtype=np.float32)
        out = pad_or_crop_waveform(long_wf)
        assert out.shape == (AASIST_L_INPUT_SAMPLES,)
        assert np.array_equal(out, long_wf[:AASIST_L_INPUT_SAMPLES])


class TestAASISTLClassifier:
    def setup_method(self):
        reset_audio_model()

    def teardown_method(self):
        reset_audio_model()

    def test_forward_pass_returns_two_logits(self):
        model = AASISTLClassifier()
        model.eval()
        batch = torch.zeros(2, AASIST_L_INPUT_SAMPLES, dtype=torch.float32)
        with torch.no_grad():
            logits = model(batch)
        assert logits.shape == (2, 2)

    def test_pretrained_checkpoint_loads_on_cpu(self):
        model, meta = load_audio_classifier(require_checkpoint=True)
        assert model is not None
        assert meta["checkpoint_loaded"] is True
        assert meta["parameter_count"] == 85306
        assert all(not p.requires_grad for p in model.parameters())
        assert not model.training

        wav = np.zeros(AASIST_L_INPUT_SAMPLES, dtype=np.float32)
        prob = predict_synthetic_voice_probability(wav, model=model)
        assert 0.0 <= prob <= 1.0

    def test_spoof_probability_uses_class_index_zero(self):
        model = AASISTLClassifier()
        model.eval()

        # In official clovaai/aasist & AASIST-L, index 0 = spoof, index 1 = bona fide.
        with patch.object(
            model,
            "forward",
            return_value=torch.tensor([[-5.0, 5.0]], dtype=torch.float32),
        ):
            prob_bonafide_higher = predict_synthetic_voice_probability(
                np.zeros(16000, dtype=np.float32), model=model
            )
        assert prob_bonafide_higher < 0.01

        with patch.object(
            model,
            "forward",
            return_value=torch.tensor([[5.0, -5.0]], dtype=torch.float32),
        ):
            prob_spoof_higher = predict_synthetic_voice_probability(
                np.zeros(16000, dtype=np.float32), model=model
            )
        assert prob_spoof_higher > 0.99

    def test_missing_checkpoint_optional_returns_none_and_inconclusive(self):
        missing = Path("does_not_exist_aasist_l.pth")
        model, meta = load_audio_classifier(checkpoint_path=missing, require_checkpoint=False)
        assert model is None
        assert meta["checkpoint_loaded"] is False

        with pytest.raises(FileNotFoundError):
            load_audio_classifier(checkpoint_path=missing, require_checkpoint=True)

        with patch(
            "services.audio_analysis.model.get_audio_classifier",
            return_value=(None, {"checkpoint_loaded": False, "error": "missing checkpoint"}),
        ):
            with pytest.raises(RuntimeError):
                predict_synthetic_voice_probability(np.zeros(16000, dtype=np.float32), model=None)

    def test_service_returns_model_unavailable_not_likely_authentic_when_missing(self):
        wav_bytes = _make_sine_wav_bytes()
        with patch(
            "services.audio_analysis.service.get_audio_classifier",
            return_value=(None, {"checkpoint_loaded": False, "error": "missing checkpoint"}),
        ):
            response = analyze_audio_bytes(wav_bytes, filename="test.wav")

        assert response.status == "MODEL_UNAVAILABLE"
        assert response.synthetic_voice_prob is None
        assert response.evidence.details["verdict_category"] == "Inconclusive"
        assert response.evidence.details["verdict_category"] != "Likely Authentic"
