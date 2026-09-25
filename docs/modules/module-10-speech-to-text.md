# Module 10: Speech-to-Text & Transcript Extraction

This document details the architecture, audio demuxing and preprocessing pipeline, ASR recognition engine (Faster-Whisper via CTranslate2), word-level alignment, database schema, and REST API specifications for **Module 10: Speech-to-Text** in TruthLens.

---

## 1. Executive Summary & Module Identity

- **Module ID**: Module 10
- **Module Name**: Speech-to-Text
- **Category**: Audio/Speech Processing & Forensic Transcription
- **Blueprint Reference**:
  - Section C: Module 10 (`Automated Speech Recognition (ASR) applied to audio tracks of video and standalone audio files. Produces timestamped text transcripts with word-level alignment and confidence scores.`)
  - Section D: Architecture Flow (`Audio / Video Media → Demuxing & Resampling (16kHz mono WAV) → Silence/Duration Verification → Faster-Whisper ASR Engine → Word & Segment Timestamps + Confidence + Transcript → Persistence & REST API`)
  - Section F: Data Architecture (`transcripts` table: `full_text`, `language`, `confidence_score`, `duration_seconds`, `segments_count`, `words_count`, `timestamp_segments_json`, `evidence_json`)
  - Section G: REST Routes (`/api/media/{id}/transcript`)
  - Section H: Security Architecture (IDOR, Quarantined Storage Boundary, Role Authorization)
- **Primary Personas**: `ANALYST`, `INVESTIGATOR`, `FACT-CHECKER` (mapped to existing TruthLens role hierarchy: elevated access for `ROLE_ANALYST`, `ROLE_MODERATOR`, `ROLE_ADMIN`, plus media owner access).
- **Downstream Integrations**:
  - Module 11: Text & Claim Analysis (extracts verifiable claims from spoken speech transcripts)
  - Module 12: Claim Verification (cross-references transcribed speech against authoritative knowledge bases)
  - Module 14: Cross-Modal Engine (correlates spoken speech with visual text from OCR and facial video cues)
  - Module 15: Risk Engine (factors in ungrounded claims, voice anomalies, and speech authenticity metrics)
  - Module 16: Dashboard (renders interactive waveform timeline and clickable timestamped transcript segments)

---

## 2. Implementation Summary

| Component | Status | Implementation Details |
| :--- | :--- | :--- |
| **Python FastAPI Microservice** | **Implemented** | Microservice located at `ai-ml/` exposing `POST /api/v1/analyze/speech-to-text` alongside `GET /api/v1/health`. Validates media MIME types, enforces upload limits, and runs deterministic ASR pipelines. |
| **Audio Preprocessing Pipeline** | **Implemented** | `SpeechPreprocessor` demuxes audio from container formats (`.wav`, `.mp3`, `.mp4`, `.mov`, `.m4a`, etc.) using parameterized FFmpeg subprocesses into 16kHz mono 16-bit PCM WAV. Enforces 600-second duration limits and energy-based silence detection. |
| **ASR Speech Transcriber** | **Implemented** | `SpeechTranscriber` utilizes Faster-Whisper (`Systran/faster-whisper-tiny`) with CTranslate2 `int8` quantization for fast, deterministic CPU/CUDA inference. Generates full text, auto-detected language, normalized confidence scores from `exp(avg_logprob)`, phrase segments, and word-level timestamps (`word_timestamps=True`). |
| **Orchestration Pipeline** | **Implemented** | `TranscriptPipeline` orchestrates preprocessing, silence handling, ASR inference, segment consolidation, evidence packaging, and safe cleanup of temporary WAV files. |
| **Spring Boot Client & Orchestrator** | **Implemented** | `FastApiTranscriptServiceClient` communicates with FastAPI using Spring `RestClient` with timeout controls (`60000ms`). `SpeechToTextService` enforces IDOR authorization, media type validation (`AUDIO` and `VIDEO`), on-demand caching, and failure recording. |
| **PostgreSQL Schema (Flyway V10)** | **Implemented** | Migration `V10__create_transcripts_schema.sql` establishes `transcripts` table with check constraints (`0.0 <= confidence_score <= 1.0`, valid `analysis_status`), unique constraint on `media_id`, foreign key with `ON DELETE CASCADE`, and B-Tree indexes. |
| **REST APIs** | **Implemented** | `GET /api/media/{id}/transcript`, `POST /api/media/{id}/transcript/analyze`, `GET /api/media/{id}/transcript/segments`, and `GET /api/media/{id}/transcript/text`. |

---

## 3. Architecture & Data Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client as Authenticated Client
    participant Ctrl as TranscriptController (/api/media/{id}/transcript)
    participant Sec as Spring Security (JWT / RBAC)
    participant Svc as SpeechToTextService
    participant Store as StorageService (Quarantine)
    participant AiClient as FastApiTranscriptServiceClient
    participant FastAPI as Python STT AI Service (:8001)
    participant Preprocessor as Speech Preprocessor (FFmpeg)
    participant Transcriber as Faster-Whisper Engine
    participant DB as PostgreSQL (Flyway V10)

    Client->>Ctrl: GET /api/media/{id}/transcript (Bearer Token)
    Ctrl->>Sec: Validate JWT & Roles (USER, ANALYST, MODERATOR, ADMIN)
    Sec-->>Ctrl: Authenticated Principal (email)
    Ctrl->>Svc: getTranscript(mediaId, email)
    Svc->>Svc: Verify IDOR (Owner or Elevated Role: ANALYST, MODERATOR, ADMIN)
    Svc->>Svc: Validate Media Category (AUDIO or VIDEO; Reject IMAGE)
    
    alt Existing Transcript Cached in DB
        Svc->>DB: findByMediaId(mediaId)
        DB-->>Svc: Transcript Entity
    else On-Demand Fresh Transcription
        Svc->>Store: load(storagePath)
        Store-->>Svc: Raw Media Stream
        Svc->>AiClient: analyzeSpeechToText(mediaBytes, filename, mimeType)
        AiClient->>FastAPI: POST /api/v1/analyze/speech-to-text (Multipart Stream)
        
        FastAPI->>Preprocessor: Demux & Resample (16kHz mono WAV, enforce 600s limit)
        Preprocessor-->>FastAPI: PreprocessedAudio (temp_path, duration, is_silent)
        
        alt Audio is Silent / Pure Noise
            FastAPI-->>AiClient: Empty Transcript Result (duration, confidence 1.0, 0 segments)
        else Speech Content Present
            FastAPI->>Transcriber: Transcribe (Faster-Whisper tiny, word_timestamps=True)
            Transcriber-->>FastAPI: Full Text + Segments + Word Timestamps + Language
        end
        
        FastAPI-->>AiClient: FastApiTranscriptResponse (JSON Payload)
        AiClient-->>Svc: FastApiTranscriptResponse
        
        Svc->>DB: save(Transcript)
        DB-->>Svc: Persisted Transcript Entity
    end
    
    Svc-->>Ctrl: TranscriptResponse (fullText, confidence, segments, evidence)
    Ctrl-->>Client: 200 OK (JSON)
```

---

## 4. Supported Inputs & Preprocessing

- **Supported Media Types**:
  - `MediaType.AUDIO` (WAV, MP3, AAC, FLAC, OGG, M4A)
  - `MediaType.VIDEO` (MP4, MOV, AVI, WEBM, MKV)
- **Image Rejection**: `MediaType.IMAGE` uploads are rejected at the service layer with HTTP `400 Bad Request` (`INVALID_MEDIA`).
- **Demuxing & Normalization**:
  - Resampling to `16,000 Hz` sample rate.
  - Channel consolidation to single-channel mono.
  - Linear 16-bit PCM (`pcm_s16le`).
  - Executed via parameterized FFmpeg argument array (no shell concatenation).
- **Silence Detection**:
  - RMS acoustic energy threshold ($< 0.001$).
  - Gracefully bypasses ASR inference to avoid hallucinated tokens.

---

## 5. ASR Engine & Alignment Specifications

- **Engine**: Faster-Whisper (`ctranslate2`)
- **Default Checkpoint**: `Systran/faster-whisper-tiny`
- **Quantization**: `int8` (CPU) / `float16` (CUDA if GPU available)
- **Beam Size**: 5
- **Word-Level Alignment**: Enabled via cross-attention weight inspection (`word_timestamps=True`).
- **Confidence Scoring**: Normalized segment score calculated from average log-probability: $\text{confidence} = \exp(\text{avg\_logprob})$, bounded in $[0.0, 1.0]$.

---

## 6. Security & Resource Protection

- **Object-Level Authorization (IDOR)**: Enforced in `SpeechToTextService`. Users can only access transcripts for media they uploaded unless they possess `ROLE_ANALYST`, `ROLE_MODERATOR`, or `ROLE_ADMIN`.
- **Quarantined Storage**: Spring Boot reads media strictly from server-managed quarantine storage directories; clients cannot pass arbitrary local file paths.
- **Subprocess Security**: FFmpeg invocations use explicit argument arrays (`shell=False`) with execution timeouts.
- **Duration Protection**: Enforces a strict 600-second audio duration ceiling. Audio exceeding 600 seconds is rejected with HTTP 400.
- **Client Sanitization**: Internal storage paths and stack traces are suppressed in API error payloads.

---

## 7. Real Runtime Verification Evidence

End-to-end runtime verification was executed against a synthesized spoken speech fixture containing: *"TruthLens speech verification system is now active."*

### Execution Results

- **Engine**: Faster-Whisper (`Systran/faster-whisper-tiny`)
- **Compute Type**: `int8` on CPU
- **Result Status**: `COMPLETED`
- **Transcribed Full Text**: `"Truth and speech verification system is now active."`
- **Detected Language**: `"en"`
- **Confidence Score**: `0.6014`
- **Duration**: `3.924s`
- **Segments Count**: `1`
- **Word Timestamps**:
  - `"Truth"`: [0.00s – 0.46s]
  - `"and"`: [0.46s – 0.62s]
  - `"speech"`: [0.62s – 1.08s]
  - `"verification"`: [1.08s – 1.86s]
  - `"system"`: [1.86s – 2.42s]
  - `"is"`: [2.42s – 2.62s]
  - `"now"`: [2.62s – 2.88s]
  - `"active."`: [2.88s – 3.42s]
- **FastAPI HTTP Endpoint**: `POST /api/v1/analyze/speech-to-text` returned `200 OK` with genuine ASR evidence.

---

## 8. Test Execution Summary

- **AI/ML Pytest Suite**: **73 passed** in 199s (100% pass rate across Modules 05–10, including 11 Module 10 STT tests).
- **Backend Maven Suite**: **372 passed** in 33.5s (100% pass rate across Modules 01–10, including 25 Module 10 STT tests).
- **Regressions**: **0 regressions** detected across Modules 01–09.

---

## 9. Known Limitations

1. **Model Weights Size**: The default development deployment uses `tiny` (39M parameters) for lightweight local CPU execution. Accuracy on heavy domain jargon or noisy backgrounds can be enhanced by switching `WHISPER_MODEL_SIZE` to `base`, `small`, or `large-v3` via environment variables.
2. **GPU Acceleration**: CUDA acceleration is automatically leveraged if an NVIDIA GPU with cuDNN is present; otherwise, it operates deterministically on CPU via CTranslate2 `int8`.
