# Image Authenticity Analysis API Specification

Module 05 exposes RESTful endpoints for triggering synthetic AI generation detection, localized physical tampering analysis, forensic evidence retrieval, and visual artifact streaming.

---

## Base URL
`/api/media/{id}/image-analysis`

## Security & Authentication
- **Authentication**: `Authorization: Bearer <JWT_TOKEN>` required for all endpoints.
- **Allowed Roles**: `USER`, `ANALYST`, `MODERATOR`, `ADMIN`, `RESEARCHER`.
- **Object-Level Authorization (IDOR)**: `USER` and `RESEARCHER` roles may only access their own uploads. `ANALYST`, `MODERATOR`, and `ADMIN` roles may access any media item.
- **Supported Media Types**: Only media with `mediaType == IMAGE` are accepted. Other media types return `400 Bad Request`.

---

## Endpoints

### 1. Get Image Analysis (On-Demand)

Retrieves the image authenticity analysis. If the image has not been analyzed yet, it automatically performs the analysis on-demand and caches the result.

- **Method**: `GET`
- **Path**: `/api/media/{id}/image-analysis`
- **Success Response**: `200 OK`
- **Response Schema**:
```json
{
  "id": "e4b971a8-8f5c-48be-8f3e-4b2a8d1c9e01",
  "mediaId": "c3d1e2f4-5a6b-7c8d-9e0f-1a2b3c4d5e6f",
  "aiProb": 0.8542,
  "manipulationProb": 0.1230,
  "authenticityAssessment": "HIGH_SYNTHETIC_RISK",
  "elaHeatmapUrl": "/api/media/c3d1e2f4-5a6b-7c8d-9e0f-1a2b3c4d5e6f/image-analysis/artifacts/ela",
  "gradcamHeatmapUrl": "/api/media/c3d1e2f4-5a6b-7c8d-9e0f-1a2b3c4d5e6f/image-analysis/artifacts/gradcam",
  "noiseVariance": 18.52,
  "fftAnomalyScore": 0.3541,
  "copyMoveDetected": false,
  "splicingDetected": false,
  "analysisStatus": "COMPLETED",
  "modelVersion": "TruthLens-DiffusionClassifier-0.1.0-dev",
  "evidence": {
    "noiseVariance": 18.52,
    "noiseInconsistencyScore": 0.082,
    "fftAnomalyScore": 0.3541,
    "copyMoveDetected": false,
    "splicingDetected": false,
    "imageWidth": 1920,
    "imageHeight": 1080,
    "details": {
      "hfEnergyRatio": 0.3541,
      "periodicSpikeDetected": false,
      "patchNoiseStd": 1.52
    }
  },
  "createdAt": "2026-09-23T01:30:00Z",
  "updatedAt": "2026-09-23T01:30:00Z"
}
```

---

### 2. Trigger Fresh Analysis (Re-analyze)

Forces a re-evaluation of the image through the Python vision service, updating the existing record and refreshing visual heatmaps.

- **Method**: `POST`
- **Path**: `/api/media/{id}/image-analysis`
- **Success Response**: `200 OK` (returns updated `ImageAnalysisResponse` schema as above).

---

### 3. Get Structured Forensic Evidence

Returns the fine-grained explainable evidence breakdown for analytical dashboards and the risk scoring engine.

- **Method**: `GET`
- **Path**: `/api/media/{id}/image-analysis/evidence`
- **Success Response**: `200 OK`
- **Response Schema**:
```json
{
  "noiseVariance": 18.52,
  "noiseInconsistencyScore": 0.082,
  "fftAnomalyScore": 0.3541,
  "copyMoveDetected": false,
  "splicingDetected": false,
  "imageWidth": 1920,
  "imageHeight": 1080,
  "details": {
    "patchVarianceStd": 1.52,
    "highFrequencyRatio": 0.3541,
    "periodicSpikeCount": 0
  }
}
```

---

### 4. Stream Forensic Heatmap Artifact

Securely streams the generated visual forensic PNG artifact (ELA or Grad-CAM attention heatmap).

- **Method**: `GET`
- **Path**: `/api/media/{id}/image-analysis/artifacts/{type}`
- **Path Parameters**:
  - `type`: `ela` (Error Level Analysis) or `gradcam` (Grad-CAM Attention Overlay)
- **Success Response**: `200 OK`
- **Content-Type**: `image/png`
- **Response Body**: Binary PNG image stream

---

## Error Responses

| Status Code | Error Code | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `INVALID_MEDIA` | The target media is not an image (e.g. video, audio). |
| `401 Unauthorized`| `UNAUTHORIZED` | Missing, expired, or invalid JWT Bearer token. |
| `403 Forbidden`   | `FORBIDDEN` | Caller does not own the media item and lacks elevated privileges. |
| `404 Not Found`   | `MEDIA_NOT_FOUND` | Media ID does not exist or requested artifact has not been generated. |
| `502 Bad Gateway` | `AI_SERVICE_UNAVAILABLE` | Downstream Python AI vision service is unreachable, timed out, or returned an error. |
