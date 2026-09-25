# API Specification: Module 11 — Text & Claim Analysis

This document describes the REST API endpoints, request/response contracts, authorization rules, and error handling for **Module 11: Text & Claim Analysis**.

---

## 1. Overview

Module 11 extracts and structures factual statements, named entities, and verifiable claims from OCR visual text (Module 09) and speech-to-text transcripts (Module 10). It exposes endpoints for:
1. Fetching structured claims extracted for a specific media asset.
2. Forcing re-analysis with optional source filtering (`OCR`, `TRANSCRIPT`, `COMBINED`).
3. Fetching an individual structured claim by its UUID.
4. Performing ad-hoc claim decomposition and entity recognition directly on raw arbitrary text.

---

## 2. Endpoints

### 2.1. Get Claims for Media

Retrieves structured claims decomposed from OCR and/or transcript text for a given media asset. Reuses cached records if already analyzed.

- **Method**: `GET`
- **Path**: `/api/media/{id}/claims`
- **Security**: Bearer JWT. Owner access or elevated role (`ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`).
- **Response**: `200 OK`

```json
{
  "mediaId": "48c34fbc-5407-425b-80fb-a9b08f43c333",
  "sourceType": "TRANSCRIPT",
  "analyzedTextLength": 240,
  "sentencesCount": 3,
  "claimsCount": 2,
  "claims": [
    {
      "id": "e421d0a5-f9db-4841-b857-e9a30489cf8b",
      "mediaId": "48c34fbc-5407-425b-80fb-a9b08f43c333",
      "claimText": "The Prime Minister announced a 15 billion euro relief package in Paris on Monday.",
      "normalizedClaimText": "the prime minister announced a 15 billion euro relief package in paris on monday",
      "claimType": "FACTUAL_CLAIM",
      "subject": "The Prime Minister",
      "action": "announced",
      "value": "a 15 billion euro relief package",
      "entityType": "MONEY",
      "confidenceScore": 0.95,
      "claimHash": "5a278912e69cbfa889211093...",
      "sourceType": "TRANSCRIPT",
      "sentenceIndex": 0,
      "startChar": 0,
      "endChar": 81,
      "entities": [
        {
          "text": "15 billion euro",
          "label": "MONEY",
          "normalized_label": "MONEY",
          "start_char": 31,
          "end_char": 46
        },
        {
          "text": "Paris",
          "label": "GPE",
          "normalized_label": "LOCATION",
          "start_char": 65,
          "end_char": 70
        },
        {
          "text": "Monday",
          "label": "DATE",
          "normalized_label": "DATE",
          "start_char": 74,
          "end_char": 80
        }
      ],
      "analysisStatus": "COMPLETED",
      "createdAt": "2026-09-24T15:30:00Z"
    }
  ],
  "entities": [ ... ],
  "evidence": {
    "model_name": "spaCy/en_core_web_sm",
    "sentences_count": 3,
    "claims_count": 2,
    "entities_count": 5,
    "duration_seconds": 0.042
  },
  "analysisStatus": "COMPLETED",
  "createdAt": "2026-09-24T15:30:00Z"
}
```

---

### 2.2. Re-Analyze Claims for Media

Forces fresh claim decomposition and entity recognition, clearing existing records for the specified media asset.

- **Method**: `POST`
- **Paths**: `/api/media/{id}/claims/analyze` or `/api/media/{id}/claims`
- **Query Parameter**: `source` (Optional: `OCR`, `TRANSCRIPT`, `COMBINED`)
- **Security**: Bearer JWT. Owner access or elevated role.
- **Response**: `200 OK` (returns fresh `ClaimAnalysisResponse`)

---

### 2.3. Get Claim by ID

Retrieves an individual claim record.

- **Method**: `GET`
- **Path**: `/api/media/{id}/claims/{claimId}`
- **Security**: Bearer JWT. Owner access or elevated role.
- **Response**: `200 OK` (returns `ClaimDto`)

---

### 2.4. Ad-Hoc Direct Text Claim Analysis

Decomposes arbitrary text into structured claims without saving to persistent storage.

- **Method**: `POST`
- **Paths**: `/api/claims/extract` (Blueprint REST route) or `/api/claims/analyze-text`
- **Security**: Bearer JWT (any authenticated user; elevated roles for cross-modal pipelines).
- **Request Body**:
```json
{
  "text": "The Federal Reserve cut interest rates by 25 basis points in Washington.",
  "sourceType": "DIRECT_TEXT",
  "language": "en"
}
```
- **Response**: `200 OK` (returns transient `ClaimAnalysisResponse`)

---

## 3. Error Responses

| Status Code | Reason | Description |
| :--- | :--- | :--- |
| `400 BAD REQUEST` | Validation Error | Blank text, text exceeds 100,000 characters, or malformed JSON. |
| `401 UNAUTHORIZED` | Missing/Invalid Token | Bearer JWT is missing, expired, or revoked. |
| `403 FORBIDDEN` | IDOR Access Denied | Caller is neither the owner of the media nor an elevated analyst/moderator/admin. |
| `404 NOT FOUND` | Resource Not Found | Media ID or Claim ID does not exist. |
| `502 BAD GATEWAY` | AI Service Failure | Python FastAPI NLP service is unreachable or returned an error. |
