# REST API Specification: Module 10 — Speech-to-Text & Transcript Extraction

This document outlines the REST API endpoints, authorization rules, request/response models, and error responses for **Module 10: Speech-to-Text & Transcript Extraction**.

---

## Base Path & Security Context

- **Base URI**: `/api/media/{id}/transcript`
- **Security Requirement**: Authenticated with JWT Bearer Token (`Authorization: Bearer <token>`).
- **Authorization Rule**: Media owner, or elevated user role (`ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`). Non-owners without elevated roles receive `403 Forbidden` (IDOR defense).
- **Supported Media Types**: `AUDIO` and `VIDEO`. Visual-only assets (`IMAGE`) receive `400 Bad Request`.

---

## 1. Retrieve Speech-to-Text Transcript

Retrieves the structured transcript findings. Reuses cached database findings if already analyzed; triggers on-demand STT transcription if absent.

- **Method**: `GET`
- **Path**: `/api/media/{id}/transcript`
- **Headers**: `Authorization: Bearer <token>`

### Response (200 OK)

```json
{
  "id": "e6f47738-466d-4952-b8bb-15c4d0a1b2c3",
  "mediaId": "b18b4562-b91c-4389-9806-38d58c1db457",
  "fullText": "TruthLens speech verification system is now active.",
  "language": "en",
  "confidenceScore": 0.96,
  "durationSeconds": 3.92,
  "segmentsCount": 1,
  "wordsCount": 8,
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 3.92,
      "text": "TruthLens speech verification system is now active.",
      "tokens": [101, 2034, 451],
      "temperature": 0.0,
      "avg_logprob": -0.05,
      "compression_ratio": 1.1,
      "no_speech_prob": 0.01,
      "confidence": 0.96,
      "words": [
        {
          "word": "TruthLens",
          "start": 0.0,
          "end": 0.6,
          "probability": 0.98
        },
        {
          "word": "speech",
          "start": 0.6,
          "end": 1.1,
          "probability": 0.97
        }
      ]
    }
  ],
  "evidence": {
    "model_name": "Faster-Whisper",
    "model_size": "tiny",
    "compute_type": "int8",
    "device": "cpu",
    "detected_language": "en",
    "language_probability": 0.99,
    "duration_seconds": 3.92,
    "audio_sample_rate": 16000,
    "media_type": "AUDIO",
    "details": {}
  },
  "analysisStatus": "COMPLETED",
  "createdAt": "2026-09-24T14:40:00Z",
  "updatedAt": "2026-09-24T14:40:00Z"
}
```

---

## 2. Re-Analyze / Force Transcript Regeneration

Explicitly re-runs the Faster-Whisper ASR pipeline, updates the stored database record, and returns fresh findings.

- **Method**: `POST`
- **Path**: `/api/media/{id}/transcript` or `/api/media/{id}/transcript/analyze`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `200 OK` (Same schema as `GET /api/media/{id}/transcript`)

---

## 3. Retrieve Timestamped Segments

Retrieves only the list of phrase/sentence segments with word-level alignment offsets.

- **Method**: `GET`
- **Path**: `/api/media/{id}/transcript/segments`
- **Headers**: `Authorization: Bearer <token>`

### Response (200 OK)

```json
[
  {
    "id": 0,
    "seek": 0,
    "start": 0.0,
    "end": 3.92,
    "text": "TruthLens speech verification system is now active.",
    "tokens": [101, 2034, 451],
    "temperature": 0.0,
    "avg_logprob": -0.05,
    "compression_ratio": 1.1,
    "no_speech_prob": 0.01,
    "confidence": 0.96,
    "words": [
      {
        "word": "TruthLens",
        "start": 0.0,
        "end": 0.6,
        "probability": 0.98
      }
    ]
  }
]
```

---

## 4. Retrieve Extracted Full Text

Retrieves the raw concatenated text transcript string.

- **Method**: `GET`
- **Path**: `/api/media/{id}/transcript/text`
- **Headers**: `Authorization: Bearer <token>`

### Response (200 OK)

```json
{
  "full_text": "TruthLens speech verification system is now active."
}
```

---

## Error Responses

| Status Code | Error Code | Reason |
| :--- | :--- | :--- |
| `401 Unauthorized` | `UNAUTHORIZED` | Missing or invalid Bearer JWT token. |
| `403 Forbidden` | `FORBIDDEN` | Caller is neither media owner nor possesses `ANALYST`/`MODERATOR`/`ADMIN` role. |
| `400 Bad Request` | `INVALID_MEDIA` | Target media asset is an `IMAGE` or unsupported media type. |
| `404 Not Found` | `MEDIA_NOT_FOUND` | No media asset found matching the specified UUID. |
| `502 Bad Gateway` | `AI_SERVICE_UNAVAILABLE` | Python FastAPI STT microservice is unreachable or timed out. |
