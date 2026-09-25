# Audio-Video Synchronization REST API (Module 08)

This document provides the OpenAPI-style endpoint specifications for **Module 08: Audio-Video Synchronization Analysis**.

---

## Base Endpoints

All endpoints require JWT Bearer Authentication header:
```http
Authorization: Bearer <jwt-token>
```

---

### 1. Get AV Synchronization Analysis

Retrieves audio-video synchronization findings for a specific media asset. If already analyzed, returns the cached result; otherwise, triggers on-demand analysis.

- **Route**: `GET /api/media/{id}/av-sync`
- **Roles**: Owner of the media asset, or elevated roles: `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`.
- **Path Parameters**:
  - `id` (UUID): ID of the video media asset.

#### Response: `200 OK`
```json
{
  "id": "e4f1a23c-789a-4bc1-9012-3456789abcde",
  "mediaId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "syncScore": 0.88,
  "lipOffsetMs": -15.5,
  "confidence": 0.92,
  "assessment": "SYNCHRONIZED",
  "analysisStatus": "COMPLETED",
  "modelName": "TruthLens-PyTorch-SyncNet-DualStream",
  "modelVersion": "TruthLens-SyncNet-v1.0-dev",
  "mismatchSegments": [
    {
      "start_time": 1.2,
      "end_time": 2.5,
      "offset_ms": -15.5,
      "confidence": 0.85,
      "reason": "Slight localized offset"
    }
  ],
  "evidence": {
    "detected_faces_count": 1,
    "selected_face_track_id": 1,
    "video_duration_seconds": 3.0,
    "audio_duration_seconds": 3.0,
    "fps": 25.0,
    "envelope_correlation": 0.86,
    "syncnet_min_distance": 0.38,
    "syncnet_confidence": 0.89,
    "tracking_stability": 0.95,
    "is_development_model": true,
    "details": {}
  },
  "createdAt": "2026-09-24T12:00:00Z",
  "updatedAt": "2026-09-24T12:00:00Z"
}
```

#### Error Responses
- `400 Bad Request`: Target media is not a video (`MediaType.VIDEO`) or lacks an audio stream.
- `401 Unauthorized`: Missing or expired Bearer token.
- `403 Forbidden`: Non-owner user without elevated roles attempted access (IDOR blocked).
- `404 Not Found`: Media ID does not exist.

---

### 2. Explicitly Re-Analyze AV Synchronization

Forces fresh re-execution of the audio-video synchronization analysis pipeline, replacing previous findings.

- **Route**: `POST /api/media/{id}/av-sync`
- **Roles**: Owner of the media asset, or elevated roles: `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`.
- **Response**: `200 OK` (identical structure to `GET /api/media/{id}/av-sync`).

---

### 3. Get Granular AV Sync Evidence

Returns detailed cross-modal metric evidence, face tracking metrics, envelope correlation scores, and SyncNet distance evaluations.

- **Route**: `GET /api/media/{id}/av-sync/evidence`
- **Roles**: Media owner or elevated roles.
- **Response**: `200 OK` with `AvSyncEvidenceDto`.

---

### 4. Get Mismatch Segments Timeline

Returns the list of detected temporal mismatch windows where voice-over dubbing, speech-viseme breaks, or temporal anomalies occurred.

- **Route**: `GET /api/media/{id}/av-sync/mismatch-segments`
- **Roles**: Media owner or elevated roles.
- **Response**: `200 OK`
```json
[
  {
    "start_time": 1.2,
    "end_time": 2.5,
    "offset_ms": -15.5,
    "confidence": 0.85,
    "reason": "Active speech audio detected without corresponding visual lip motion (dubbing signature)"
  }
]
```

---

## FastAPI Internal AI Microservice Endpoint

Used by Spring Boot backend service client:

- **Route**: `POST /api/v1/analyze/av-sync`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Raw binary stream of video asset (`.mp4`, `.mov`, `.mkv`, etc.).
- **Response**: `200 OK` with `AvSyncAnalysisResult` schema.
