# TruthLens Documentation

Welcome to the official technical and architectural documentation for the **TruthLens Authenticity Platform**.

---

## 1. Source of Truth & Architecture Blueprint

The overarching architectural blueprint, system philosophy, technology stack classification, and 20-module execution roadmap are defined in:

* [TruthLensBlueprint.html](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/blueprint/TruthLensBlueprint.html)

> [!IMPORTANT]
> **Blueprint vs. Implementation Principle**
> - The **Blueprint** defines the intended target architecture, 20-module decomposition, data models, and specifications.
> - The **Codebase** defines what is currently implemented.
> - The documentation in this `docs/` folder accurately reflects the **current implementation state** while providing clear traceability back to the blueprint.

---

## 2. Documentation Structure

The documentation is organized into focused directories:

```
docs/
├── architecture/         # System topology, microservices boundaries, tech stack
│   └── overview.md       # Architectural overview (Blueprint vs Current Implementation)
├── modules/              # Detailed specifications for each build module
│   └── module-01-auth-rbac-user-management.md  # Complete Module 01 documentation
├── api/                  # REST API route contracts, schemas, DTOs
│   └── authentication-user-api.md              # Auth, User & RBAC API reference
├── database/             # Relational schemas, migrations, ER models
│   └── schema-module-01.md                     # PostgreSQL Flyway V1 schema documentation
├── development/          # Developer environment setup, configurations, workflows
│   └── setup-guide.md                          # Local backend & database setup guide
└── testing/              # Testing strategies, suite breakdown, execution guides
    └── test-strategy-and-suite.md              # Test architecture & 57-test suite details
```

---

## 3. Implementation Status Matrix

TruthLens follows a modular 20-module build roadmap. The table below provides an accurate reflection of the current repository state:

| Module ID | Module Name | Primary Blueprint Owner | Repository Status | Current Deliverables |
| :--- | :--- | :--- | :--- | :--- |
| **Module 01** | **Authentication, RBAC & User Management** | Yashas | **Implemented (Backend Core)** | Spring Security 6, JWT, RBAC, Flyway V1, 57 automated tests |
| **Module 02** | **Media Upload & Secure Ingestion** | Yashas + Vishal | **Implemented (Backend Core)** | Apache Tika validation, SHA-256 hashing, quarantine storage, Flyway V2, 44 tests |
| **Module 03** | **Media Fingerprinting & Duplicate Detection** | Yashas + Vishal | **Implemented (Backend Core)** | SHA-256, dHash visual perceptual hashing, audio chromaprint, Flyway V3, 50 tests |
| **Module 04** | **Metadata & Digital Forensics** | Vishal + Yashas | **Implemented (Backend Core)** | EXIF/container/audio extraction (metadata-extractor, ExifTool & MediaInfo CLI wrapper), 8 anomaly detection rules, Flyway V4, 61 tests |
| **Module 05** | **Image Authenticity Analysis** | Vishal + Yashas | **Implemented (Dual Engine: Python FastAPI + Spring Boot)** | Dual-engine AI vision analysis: PyTorch Diffusion Classifier Net, Grad-CAM attention exporter, OpenCV ELA heatmap, spatial noise variance, 2D FFT spectral analysis, copy-move & splicing detector, Flyway V5, 44 tests (14 Python + 30 Java) |
| **Module 06** | **Video Deepfake & Forensic Analysis** | Vishal + Yashas | **Implemented (Dual Engine: Python FastAPI + Spring Boot)** | Dual-engine video deepfake analysis: FFmpeg video frame sampler, PyTorch RetinaFace detector & spatial-temporal tracker, PyTorch 3D-CNN spatiotemporal classifier net, optical flow temporal analyzer, Flyway V6, 46 tests (15 Python + 31 Java) |
| **Module 07** | **Audio Authenticity & Voice Forensics** | Vishal | **Implemented (Dual Engine: Python FastAPI + Spring Boot)** | Dual-engine audio authenticity analysis: Librosa 80-band Mel-spectrogram extractor, YIN F0 pitch variance, STFT phase discontinuity, spectral statistics, onset spectral flux splicing markers, PyTorch AASIST GAT classifier net, Mel-spectrogram PNG/Base64 generator, Flyway V7, 35 tests (6 Python + 29 Java) |
| **Module 08** | **Audio-Video Synchronization Analysis** | Vishal + Yashas | **Implemented (Dual Engine: Python FastAPI + Spring Boot)** | Multi-modal AV sync analysis: MediaPipe lip tracker, acoustic speech envelope cross-correlation, PyTorch SyncNet two-stream evaluator, mismatch segment detection, Flyway V8, 38 tests (15 Python + 23 Java) |
| **Module 09** | OCR & Visual Text Extraction | Yashas | *Planned* | - |
| **Module 10** | Speech-to-Text & Transcript Extraction | Vishal | *Planned* | - |
| **Module 11** | Text & Claim Analysis | Vishal + Yashas | *Planned* | - |
| **Module 12** | Claim Verification & Evidence Retrieval | Yashas + Member | *Planned* | - |
| **Module 13** | Provenance & Content Credentials (C2PA) | Yashas + Vishal | *Planned* | - |
| **Module 14** | Cross-Modal Consistency Analysis | Vishal + Yashas | *Planned* | - |
| **Module 15** | Authenticity & Risk Scoring Engine | Yashas | *Planned* | - |
| **Module 16** | Explainable Analysis & Results Dashboard | Yashas + Team | *Planned* | - |
| **Module 17** | Investigation Case Management | Yashas | *Planned* | - |
| **Module 18** | Report Generation & Evidence Export | Yashas | *Planned* | - |
| **Module 19** | Analysis Job Management & Processing Queue | Yashas + Vishal | *Planned* | - |
| **Module 20** | Security, Audit & System Monitoring | Yashas | *Planned* | - |

---

## 4. Quick Links

- [Architecture Overview](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/architecture/overview.md)
- [Module 01: Authentication, RBAC & User Management](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/modules/module-01-auth-rbac-user-management.md)
- [Module 02: Media Upload & Secure Ingestion](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/modules/module-02-media-upload-secure-ingestion.md)
- [Module 03: Media Fingerprinting & Duplicate Detection](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/modules/module-03-media-fingerprinting-duplicate-detection.md)
- [Module 04: Metadata & Digital Forensics](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/modules/module-04-metadata-digital-forensics.md)
- [Module 05: Image Authenticity Analysis](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/modules/module-05-image-authenticity-analysis.md)
- [Module 06: Video Deepfake & Forensic Analysis](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/modules/module-06-video-deepfake-forensic-analysis.md)
- [Module 07: Audio Authenticity & Voice Forensics](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/modules/module-07-audio-authenticity-voice-forensics.md)
- [Module 08: Audio-Video Synchronization Analysis](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/modules/module-08-audio-video-synchronization.md)
- [REST API: AV Synchronization Analysis](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/api/av-sync-api.md)
- [Database Schema: AV Sync Analysis V8](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/database/schema-module-08.md)
- [Developer Setup Guide](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/development/setup-guide.md)
- [Testing Strategy & Test Suite](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/testing/test-strategy-and-suite.md)
