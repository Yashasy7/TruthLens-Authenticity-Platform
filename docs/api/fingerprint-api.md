# API Specification: Module 03 (Media Fingerprinting & Duplicate Detection)

Base Path: `/api/media/{id}`  
Security: Bearer Token (JWT) required. Authorized Roles: `USER`, `ANALYST`, `MODERATOR`, `ADMIN`, `RESEARCHER`.

---

## 1. Get Media Fingerprint

Retrieves cryptographic (SHA-256), perceptual (dHash), and acoustic (chromaprint) fingerprints for a specified media item.

- **URL**: `/api/media/{id}/fingerprint`
- **Method**: `GET`
- **Authentication**: Required (`USER`, `ANALYST`, `MODERATOR`, `ADMIN`, `RESEARCHER`)
- **Access Control**: Object-level authorization (IDOR protected). Callers with `ROLE_USER` or `ROLE_RESEARCHER` must be the media owner. Elevated roles (`ANALYST`, `MODERATOR`, `ADMIN`) may inspect any media.

### Responses

#### 200 OK
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "mediaId": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "sha256Hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "phash": "a4f208c1d3e5b709",
  "chromaprint": null,
  "isDuplicate": true,
  "duplicateOfMediaId": null,
  "similarityScore": 0.96875,
  "matchType": "NEAR_MATCH_PHASH",
  "createdAt": "2026-09-19T18:15:00Z"
}
```
*(Note: `duplicateOfMediaId` is masked as `null` when requested by a standard user or researcher duplicating another user's media to preserve privacy and prevent IDOR UUID enumeration. Elevated investigation roles and owners duplicating their own uploads receive the true internal UUID).*

#### 403 Forbidden
```json
{
  "timestamp": "2026-09-19T18:15:00Z",
  "status": 403,
  "error": "FORBIDDEN",
  "message": "Access denied. You do not have permission to access this media's fingerprint.",
  "path": "/api/media/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d/fingerprint"
}
```

---

## 2. Trigger Fingerprint Generation & Catalog Re-evaluation

Generates fingerprints if not already computed, or forces a re-evaluation of duplicate detection against the current catalog when new duplicates may have entered the system (F-03).

- **URL**: `/api/media/{id}/fingerprint`
- **Method**: `POST`
- **Authentication**: Required (`USER`, `ANALYST`, `MODERATOR`, `ADMIN`, `RESEARCHER`)
- **Responses**: Same as `GET /api/media/{id}/fingerprint` with refreshed duplicate detection status.

---

## 3. Get Duplicate Details

Returns forensic duplicate detection metrics, match classification, and privacy-governed reference details.

- **URL**: `/api/media/{id}/duplicates`
- **Method**: `GET`
- **Authentication**: Required (`USER`, `ANALYST`, `MODERATOR`, `ADMIN`, `RESEARCHER`)

### Responses

#### 200 OK (Standard User / Cross-User Privacy Masked)
```json
{
  "mediaId": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "isDuplicate": true,
  "matchType": "NEAR_MATCH_PHASH",
  "similarityScore": 0.96875,
  "duplicateOfMediaId": null,
  "duplicateOfFilename": "Verified Reference Item",
  "detectedAt": "2026-09-19T18:15:00Z"
}
```

#### 200 OK (Elevated Role: ANALYST, MODERATOR, ADMIN)
```json
{
  "mediaId": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "isDuplicate": true,
  "matchType": "NEAR_MATCH_PHASH",
  "similarityScore": 0.96875,
  "duplicateOfMediaId": "8a0deb4d-1b2c-3def-4bad-5b6d7b8dcb9e",
  "duplicateOfFilename": "original_evidence_photo.jpg",
  "detectedAt": "2026-09-19T18:15:00Z"
}
```
*(Note: `duplicateOfFilename` and `duplicateOfMediaId` reveal actual original metadata only to elevated roles `ANALYST`, `MODERATOR`, `ADMIN` or the original uploader. For other standard users and researchers, sensitive references are masked to protect cross-user privacy).*
