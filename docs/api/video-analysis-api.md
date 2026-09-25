# Video Deepfake & Forensic Analysis API Specification

Module 06 exposes RESTful endpoints for evaluating deepfake manipulation, retrieving frame-level scores, and viewing chronological suspicious timeline markers for video media.

---

## Base URL
`/api/media/{id}/video-analysis`

## Security & Authentication
- **Authentication**: `Authorization: Bearer <JWT_TOKEN>` required for all endpoints.
- **Allowed Roles**: `USER`, `ANALYST`, `MODERATOR`, `ADMIN`, `RESEARCHER`.
- **Object-Level Authorization (IDOR)**: `USER` and `RESEARCHER` roles may only access their own uploads. `ANALYST`, `MODERATOR`, and `ADMIN` roles may access any media item.
- **Supported Media Types**: Only media with `mediaType == VIDEO` are accepted. Other media types return `400 Bad Request`.

---

## Endpoints

### 1. Get Video Deepfake Analysis (On-Demand)

Retrieves the video deepfake analysis findings. If the video has not been analyzed yet, it executes the analysis pipeline on-demand and caches the result.

- **Method**: `GET`
- **Path**: `/api/media/{id}/video-analysis`
- **Success Response**: `200 OK`
- **Response Schema**:
```json
{
  "id": "f5a892b1-1234-4b56-7890-abcdef123456",
  "media_id": "c3d1e2f4-5a6b-7c8d-9e0f-1a2b3c4d5e6f",
  "deepfake_prob": 0.8421,
  "face_count": 2,
  "total_frames_sampled": 15,
  "authenticity_assessment": "HIGH_DEEPFAKE_RISK",
  "analysis_status": "COMPLETED",
  "model_version": "TruthLens-VideoDeepfakeClassifier-0.1.0-dev",
  "suspicious_timestamps": [
    {
      "timestamp_seconds": 2.0,
      "frame_index": 4,
      "score": 0.884,
      "reason": "HIGH_SYNTHETIC_FACE_PROBABILITY"
    }
  ],
  "evidence": {
    "face_count": 2,
    "total_frames_sampled": 15,
    "duration_seconds": 15.0,
    "frame_scores": [
      {
        "frame_index": 4,
        "timestamp_seconds": 2.0,
        "deepfake_score": 0.884,
        "temporal_inconsistency": 0.725,
        "faces_detected": 2,
        "is_suspicious": true
      }
    ],
    "suspicious_timestamps": [
      {
        "timestamp_seconds": 2.0,
        "frame_index": 4,
        "score": 0.884,
        "reason": "HIGH_SYNTHETIC_FACE_PROBABILITY"
      }
    ],
    "details": {
      "p90_deepfake": 0.884,
      "mean_deepfake": 0.521,
      "p90_temporal": 0.725
    }
  },
  "created_at": "2026-09-23T22:00:00Z",
  "updated_at": "2026-09-23T22:00:00Z"
}
```

---

### 2. Re-Analyze Video Asset

Explicitly triggers a fresh analysis pass on the video, refreshing frame samples, facial tracking, and model predictions.

- **Method**: `POST`
- **Path**: `/api/media/{id}/video-analysis`
- **Success Response**: `200 OK`
- **Response Schema**: Same as `GET /api/media/{id}/video-analysis`

---

### 3. Get Video Evidence Breakdown

Retrieves the structured forensic evidence, per-frame scores, and optical flow metrics.

- **Method**: `GET`
- **Path**: `/api/media/{id}/video-analysis/evidence`
- **Success Response**: `200 OK`
- **Response Schema**: `VideoEvidenceDto`

---

### 4. Get Suspicious Timestamps Timeline

Retrieves a chronologically ordered array of timestamps flagged for synthetic facial artifacts or temporal discontinuities.

- **Method**: `GET`
- **Path**: `/api/media/{id}/video-analysis/timeline`
- **Success Response**: `200 OK`
- **Response Schema**:
```json
[
  {
    "timestamp_seconds": 2.0,
    "frame_index": 4,
    "score": 0.884,
    "reason": "HIGH_SYNTHETIC_FACE_PROBABILITY"
  },
  {
    "timestamp_seconds": 5.5,
    "frame_index": 11,
    "score": 0.762,
    "reason": "TEMPORAL_DISCONTINUITY"
  }
]
```

---

## Error Responses

| Status Code | Error Code | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `INVALID_MEDIA` | Media is not a video (`mediaType != VIDEO`). |
| `401 Unauthorized` | `UNAUTHORIZED` | Missing or invalid JWT Bearer token. |
| `403 Forbidden` | `FORBIDDEN` | Caller does not own the video and lacks elevated role. |
| `404 Not Found` | `MEDIA_NOT_FOUND` | Media ID does not exist. |
| `502 Bad Gateway` | `AI_SERVICE_UNAVAILABLE` | Downstream FastAPI video service failed or timed out. |
