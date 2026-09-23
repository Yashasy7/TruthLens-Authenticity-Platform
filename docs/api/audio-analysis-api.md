# Audio Authenticity & Voice Forensics REST API (Module 07)

This document provides the OpenAPI specification and request/response examples for the **Audio Authenticity & Voice Forensics** REST API.

---

## 1. Authentication & Authorization

All endpoints require a valid JWT Bearer token in the `Authorization` header:
```http
Authorization: Bearer <jwt-token>
```

### Access Control Rules
- **Asset Ownership**: Users with role `USER` or `RESEARCHER` can only access audio analysis records for media assets they personally uploaded. IDOR violations return `403 Forbidden`.
- **Privileged Roles**: Users with role `ANALYST`, `MODERATOR`, or `ADMIN` can access audio analysis records across all uploaded media.
- **Media Type Validation**: Only assets with `media_type = 'AUDIO'` can be analyzed. Assets of type `IMAGE` or `VIDEO` return `400 Bad Request`.

---

## 2. Endpoints

### 2.1 Get Audio Authenticity Analysis
`GET /api/media/{id}/audio-analysis`

Retrieves audio authenticity findings for the specified media asset. Returns cached findings if already analyzed; triggers on-demand analysis if absent.

#### Response (200 OK)
```json
{
  "id": "e0a2f4bc-8791-4c45-9856-43e7bb01d451",
  "media_id": "c13867c2-f155-46aa-83a1-778912efbc34",
  "synthetic_voice_prob": 0.8542,
  "spectrogram_url": "/artifacts/audio_spectrogram_9a12b4e8c1.png",
  "spectrogram_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "pitch_variance": 142.5000,
  "phase_discontinuity": 0.7200,
  "authenticity_assessment": "HIGH_SYNTHETIC_VOICE_RISK",
  "analysis_status": "COMPLETED",
  "model_name": "TruthLens-PyTorch-AASIST-AudioClassifier",
  "model_version": "0.1.0-dev",
  "splice_markers": [
    {
      "timestamp_seconds": 1.45,
      "score": 0.88,
      "reason": "SPECTRAL_FLUX_JUMP"
    }
  ],
  "evidence": {
    "duration_seconds": 4.50,
    "pitch_mean": 215.40,
    "pitch_variance": 142.5000,
    "spectral_centroid_mean": 1850.20,
    "spectral_bandwidth_mean": 1420.50,
    "spectral_rolloff_mean": 3800.00,
    "zero_crossing_rate_mean": 0.0820,
    "phase_discontinuity_score": 0.7200,
    "splice_markers": [
      {
        "timestamp_seconds": 1.45,
        "score": 0.88,
        "reason": "SPECTRAL_FLUX_JUMP"
      }
    ],
    "details": {
      "aasist_synthetic_score": 0.8250,
      "pitch_anomaly_score": 0.7500
    }
  },
  "created_at": "2026-09-24T00:50:00Z",
  "updated_at": "2026-09-24T00:50:00Z"
}
```

---

### 2.2 Re-analyze Audio Asset
`POST /api/media/{id}/audio-analysis`

Forces re-execution of the audio authenticity and voice forensics pipeline, updating the persisted record.

#### Response (200 OK)
Returns fresh `AudioAnalysisResponse`.

---

### 2.3 Get Acoustic Evidence Breakdown
`GET /api/media/{id}/audio-analysis/evidence`

Retrieves the detailed acoustic evidence metrics without top-level wrapper fields.

#### Response (200 OK)
```json
{
  "duration_seconds": 4.50,
  "pitch_mean": 215.40,
  "pitch_variance": 142.5000,
  "spectral_centroid_mean": 1850.20,
  "spectral_bandwidth_mean": 1420.50,
  "spectral_rolloff_mean": 3800.00,
  "zero_crossing_rate_mean": 0.0820,
  "phase_discontinuity_score": 0.7200,
  "splice_markers": [],
  "details": {}
}
```

---

### 2.4 Get Audio Splicing Markers
`GET /api/media/{id}/audio-analysis/splice-markers`

Retrieves chronological list of detected splicing transitions.

#### Response (200 OK)
```json
[
  {
    "timestamp_seconds": 1.45,
    "score": 0.88,
    "reason": "SPECTRAL_FLUX_JUMP"
  }
]
```

---

## 3. Error Responses

| Status Code | Error Message | Description |
| :--- | :--- | :--- |
| `401 Unauthorized` | `Full authentication is required to access this resource` | Missing or invalid JWT token. |
| `403 Forbidden` | `Access denied. You do not have permission to access this media's analysis.` | Non-owner attempting to access private media. |
| `404 Not Found` | `Media not found with id: <uuid>` | Media asset does not exist. |
| `400 Bad Request` | `Audio authenticity analysis is only supported for audio assets. Target media type: VIDEO` | Asset is not an audio file. |
| `502 Bad Gateway` | `Failed to communicate with AI audio service` | Python FastAPI service unreachable or timed out. |
