# TruthLens REST API: Media Upload & Secure Ingestion (Module 02)

This document details the HTTP API endpoints implemented for **Module 02: Media Upload & Secure Ingestion**.

---

## 1. Endpoints Summary

| Method | Route | Security / Roles | Request Format | Success Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/media/upload` | Authenticated (`USER`, `ANALYST`, `MODERATOR`, `ADMIN`) | `multipart/form-data` | `201 Created` (`MediaUploadResponse`) |
| `GET` | `/api/media/{id}` | Authenticated (`USER`, `ANALYST`, `MODERATOR`, `ADMIN`) | None | `200 OK` (`MediaResponse`) |
| `GET` | `/api/media/my` | Authenticated (`USER`, `ANALYST`, `MODERATOR`, `ADMIN`) | None | `200 OK` (`List<MediaResponse>`) |

---

## 2. Endpoint Details

### 2.1 Media Upload

Uploads an image, video, audio, or text file. Validates content via Apache Tika, calculates SHA-256 hash, stores in quarantined storage, and records metadata in PostgreSQL.

- **URL**: `/api/media/upload`
- **Method**: `POST`
- **Headers**:
  - `Authorization: Bearer <jwt_token>`
  - `Content-Type: multipart/form-data`
- **Form Data Parameters**:
  - `file` (Binary file, required)

#### Success Response (HTTP 201 Created)
```json
{
  "message": "Media uploaded and quarantined successfully",
  "id": "e4a2c1f0-8c9d-4e1f-a3b4-c5d6e7f8a9b0",
  "uploaderId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "originalFilename": "evidence_image.jpg",
  "storagePath": "quarantine/image/20260919/d3b07384-d113-4672-9c7e-b08e2f84b3d1.jpg",
  "mediaType": "IMAGE",
  "mimeType": "image/jpeg",
  "fileSize": 2048500,
  "sha256Hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f01234",
  "uploadStatus": "UPLOADED",
  "createdAt": "2026-09-19T16:00:00Z"
}
```

#### Error Responses
- **400 Bad Request**: File is missing, empty, or has an unsupported format.
  ```json
  {
    "status": 400,
    "error": "INVALID_MEDIA",
    "message": "Unsupported file format: 'application/x-dosexec'. Supported categories: IMAGE, VIDEO, AUDIO, TEXT.",
    "path": "/api/media/upload",
    "timestamp": "2026-09-19T16:00:05.123456Z"
  }
  ```
- **401 Unauthorized**: Missing or invalid Bearer token.
- **403 Forbidden**: Caller's account is suspended.
- **413 Payload Too Large**: Uploaded file exceeds configured limit.
  ```json
  {
    "status": 413,
    "error": "FILE_SIZE_EXCEEDED",
    "message": "The uploaded file exceeds the configured maximum upload size limit.",
    "path": "/api/media/upload",
    "timestamp": "2026-09-19T16:00:05.123456Z"
  }
  ```
- **500 Internal Server Error**: Storage or database persistence failure. Quarantined file is automatically purged on persistence rollback.

---

### 2.2 Get Media Metadata by ID

- **URL**: `/api/media/{id}`
- **Method**: `GET`
- **Headers**:
  - `Authorization: Bearer <jwt_token>`

#### Success Response (HTTP 200 OK)
```json
{
  "id": "e4a2c1f0-8c9d-4e1f-a3b4-c5d6e7f8a9b0",
  "uploaderId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "originalFilename": "evidence_image.jpg",
  "storagePath": "quarantine/image/20260919/d3b07384-d113-4672-9c7e-b08e2f84b3d1.jpg",
  "mediaType": "IMAGE",
  "mimeType": "image/jpeg",
  "fileSize": 2048500,
  "sha256Hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f01234",
  "uploadStatus": "UPLOADED",
  "createdAt": "2026-09-19T16:00:00Z",
  "updatedAt": "2026-09-19T16:00:00Z"
}
```

---

### 2.3 Get Current User's Uploads

- **URL**: `/api/media/my`
- **Method**: `GET`
- **Headers**:
  - `Authorization: Bearer <jwt_token>`

#### Success Response (HTTP 200 OK)
```json
[
  {
    "id": "e4a2c1f0-8c9d-4e1f-a3b4-c5d6e7f8a9b0",
    "uploaderId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "originalFilename": "evidence_image.jpg",
    "storagePath": "quarantine/image/20260919/d3b07384-d113-4672-9c7e-b08e2f84b3d1.jpg",
    "mediaType": "IMAGE",
    "mimeType": "image/jpeg",
    "fileSize": 2048500,
    "sha256Hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f01234",
    "uploadStatus": "UPLOADED",
    "createdAt": "2026-09-19T16:00:00Z",
    "updatedAt": "2026-09-19T16:00:00Z"
  }
]
```
