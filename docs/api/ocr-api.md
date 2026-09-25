# OCR Text Extraction REST API (Module 09)

This document provides the endpoint specifications for **Module 09: Optical Character Recognition & Visual Text Extraction**.

---

## Base Authentication

All endpoints require JWT Bearer Authentication header:
```http
Authorization: Bearer <jwt-token>
```

---

## Endpoints

### 1. Get OCR Analysis Result

Retrieves optical character recognition analysis findings for a specific media asset (Image or Video). If already analyzed, returns the cached record; otherwise, triggers on-demand analysis.

- **Route**: `GET /api/media/{id}/ocr`
- **Method**: `GET`
- **Roles**: Owner of the media asset, or elevated roles: `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`.
- **Path Parameters**:
  - `id` (UUID): ID of the visual media asset (`IMAGE` or `VIDEO`).

#### Response: `200 OK`
```json
{
  "id": "e4f1a23c-789a-4bc1-9012-3456789abcde",
  "mediaId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "extractedText": "BREAKING NEWS ALERT: INVESTIGATION COMPLETED",
  "language": "en",
  "confidenceScore": 0.94,
  "regionsCount": 1,
  "regions": [
    {
      "text": "BREAKING NEWS ALERT: INVESTIGATION COMPLETED",
      "confidence": 0.94,
      "boundingBox": {
        "x": 40,
        "y": 280,
        "width": 560,
        "height": 36,
        "normalizedBbox": [0.0625, 0.7777, 0.875, 0.1],
        "polygon": [[40, 280], [600, 280], [600, 316], [40, 316]]
      },
      "language": "en",
      "frameIndex": 0,
      "timestampSeconds": 0.0,
      "startTime": 0.0,
      "endTime": 2.5
    }
  ],
  "evidence": {
    "total_regions": 1,
    "detected_languages": ["en"],
    "image_width": 640,
    "image_height": 360,
    "engine_used": "EasyOCR",
    "preprocessing_applied": [
      "Grayscale conversion",
      "Bilateral denoising",
      "CLAHE contrast enhancement",
      "Adaptive & Otsu binarization"
    ],
    "media_type": "VIDEO",
    "frames_analyzed": 5,
    "details": {}
  },
  "analysisStatus": "COMPLETED",
  "createdAt": "2026-09-24T12:00:00Z",
  "updatedAt": "2026-09-24T12:00:00Z"
}
```

---

### 2. Trigger Fresh OCR Analysis

Explicitly re-triggers visual text extraction pipeline regardless of existing cached findings.

- **Route**: `POST /api/media/{id}/ocr/analyze`
- **Method**: `POST`
- **Roles**: Owner of the media asset, or elevated roles: `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`.
- **Response**: `200 OK` (Structured `OcrResultResponse` as above).

---

### 3. Get OCR Bounding Boxes

Retrieves only the spatial text bounding boxes and polygon coordinates for rendering frontend visual overlays.

- **Route**: `GET /api/media/{id}/ocr/bounding-boxes`
- **Method**: `GET`
- **Roles**: Owner of the media asset, or elevated roles: `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`.
- **Response**: `200 OK`
```json
[
  {
    "text": "BREAKING NEWS ALERT: INVESTIGATION COMPLETED",
    "confidence": 0.94,
    "boundingBox": {
      "x": 40,
      "y": 280,
      "width": 560,
      "height": 36,
      "normalizedBbox": [0.0625, 0.7777, 0.875, 0.1],
      "polygon": [[40, 280], [600, 280], [600, 316], [40, 316]]
    },
    "language": "en",
    "frameIndex": 0,
    "timestampSeconds": 0.0,
    "startTime": 0.0,
    "endTime": 2.5
  }
]
```

---

### 4. Get Extracted Text Only

Retrieves the plain raw concatenated text extracted from the visual asset.

- **Route**: `GET /api/media/{id}/ocr/text`
- **Method**: `GET`
- **Roles**: Owner of the media asset, or elevated roles: `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`.
- **Response**: `200 OK`
```json
{
  "text": "BREAKING NEWS ALERT: INVESTIGATION COMPLETED"
}
```

---

## Error Codes

| Status Code | Reason | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | Unsupported Media Type | Visual OCR invoked on non-visual asset (e.g. `AUDIO`). |
| `401 Unauthorized` | Missing / Invalid Token | Request missing valid JWT Bearer header. |
| `403 Forbidden` | Access Denied (IDOR) | Caller is not media owner and lacks elevated role. |
| `404 Not Found` | Media Not Found | Specified media ID does not exist in repository. |
| `502 Bad Gateway` | AI Service Failure | Python OCR microservice unreachable or returned failure. |
