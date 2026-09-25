# Module 04: Metadata Forensics API Specification

This document defines the REST endpoints, request parameters, response structures, and authorization constraints for **Module 04: Metadata & Digital Forensics**.

---

## Base Path

`/api/media/{id}/metadata`

All requests require a valid Bearer JWT token in the `Authorization` header.

---

## 1. Get Forensic Metadata

Retrieves normalized EXIF/container metadata, detected forensic anomalies, and suspicion score for a media file. If metadata has not yet been extracted, it is generated and persisted on-demand.

- **Method**: `GET`
- **Path**: `/api/media/{id}/metadata`
- **Authorized Roles**: `ROLE_USER` (own media), `ROLE_RESEARCHER` (own media), `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`

### Response (200 OK)

```json
{
  "id": "7b0a8806-0cb7-4f40-a15d-8b024479361a",
  "mediaId": "48b1c43d-0d6c-48c0-bc66-3d604e760bf6",
  "cameraMake": "Canon",
  "cameraModel": "Canon EOS 5D Mark IV",
  "lensModel": "EF 24-70mm f/2.8L II USM",
  "softwareTag": "Adobe Photoshop 2024 (Macintosh)",
  "capturedAt": "2026-08-15T14:22:00Z",
  "modifiedAt": "2026-08-16T09:10:00Z",
  "gpsLatitude": 37.7749,
  "gpsLongitude": -122.4194,
  "gpsAltitude": 15.0,
  "width": 1920,
  "height": 1080,
  "durationSeconds": null,
  "bitrate": null,
  "frameRate": null,
  "videoCodec": null,
  "audioCodec": null,
  "audioSampleRate": null,
  "audioChannels": null,
  "containerFormat": "JPEG",
  "anomalies": [
    {
      "ruleId": "ANOM_EDITING_SOFTWARE",
      "category": "SOFTWARE_MODIFICATION",
      "severity": "HIGH",
      "title": "Editing Software Signature Detected",
      "description": "Metadata headers indicate modification or creation using graphic editing software (Adobe Photoshop 2024 (Macintosh)). Strongly suggests post-capture manipulation.",
      "evidence": "Software Tag: Adobe Photoshop 2024 (Macintosh)",
      "confidence": 0.95,
      "scoreImpact": 0.35
    }
  ],
  "hasAnomalies": true,
  "anomalyCount": 1,
  "forensicScore": 0.35,
  "riskLevel": "SUSPICIOUS",
  "extractionEngine": "JAVA_METADATA_EXTRACTOR",
  "createdAt": "2026-09-22T14:30:00Z",
  "updatedAt": "2026-09-22T14:30:00Z"
}
```

---

## 2. Generate or Re-evaluate Metadata

Explicitly triggers extraction or re-evaluation of metadata and anomaly findings for a media asset against the current ruleset.

- **Method**: `POST`
- **Path**: `/api/media/{id}/metadata`
- **Authorized Roles**: `ROLE_USER` (own media), `ROLE_RESEARCHER` (own media), `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`

### Response (200 OK)

Returns refreshed `MediaMetadataResponse`.

---

## 3. Get Anomaly Report

Retrieves structured forensic anomaly report with discrete risk classification and rule findings.

- **Method**: `GET`
- **Path**: `/api/media/{id}/metadata/anomalies`
- **Authorized Roles**: `ROLE_USER` (own media), `ROLE_RESEARCHER` (own media), `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`

### Response (200 OK)

```json
{
  "mediaId": "48b1c43d-0d6c-48c0-bc66-3d604e760bf6",
  "hasAnomalies": true,
  "anomalyCount": 1,
  "forensicScore": 0.35,
  "riskLevel": "SUSPICIOUS",
  "anomalies": [
    {
      "ruleId": "ANOM_EDITING_SOFTWARE",
      "category": "SOFTWARE_MODIFICATION",
      "severity": "HIGH",
      "title": "Editing Software Signature Detected",
      "description": "Metadata headers indicate modification or creation using graphic editing software (Adobe Photoshop 2024 (Macintosh)). Strongly suggests post-capture manipulation.",
      "evidence": "Software Tag: Adobe Photoshop 2024 (Macintosh)",
      "confidence": 0.95,
      "scoreImpact": 0.35
    }
  ],
  "summary": "Forensic evaluation completed with 1 anomaly indicator(s). Overall metadata suspicion score: 0.3500 (SUSPICIOUS).",
  "evaluatedAt": "2026-09-22T14:30:00Z"
}
```

---

## 4. Get Raw Metadata Tree

Retrieves the complete hierarchical raw metadata tree serialized as JSON.

- **Method**: `GET`
- **Path**: `/api/media/{id}/metadata/raw`
- **Produces**: `application/json`
- **Authorized Roles**: `ROLE_USER` (own media), `ROLE_RESEARCHER` (own media), `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`

### Response (200 OK)

```json
{
  "Exif IFD0": {
    "Make": "Canon",
    "Model": "Canon EOS 5D Mark IV",
    "Software": "Adobe Photoshop 2024 (Macintosh)"
  },
  "Exif SubIFD": {
    "Lens Model": "EF 24-70mm f/2.8L II USM",
    "Date/Time Original": "2026:08:15 14:22:00"
  },
  "GPS": {
    "GPS Latitude": "37° 46' 29.64\"",
    "GPS Longitude": "-122° 25' 9.84\""
  }
}
```

---

## Error Status Codes

| Status Code | Reason | Description |
| :---: | :--- | :--- |
| **401 Unauthorized** | Missing/invalid JWT token | Request did not supply valid authentication credentials. |
| **403 Forbidden** | Access Denied / IDOR | Standard user or researcher attempted to access another user's media. |
| **404 Not Found** | Media Not Found | The provided media UUID does not exist. |
