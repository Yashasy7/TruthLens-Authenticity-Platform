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
| **Module 05** | Image Authenticity Analysis | Vishal | *Planned* | - |
| **Module 06** | Video Deepfake & Forensic Analysis | Vishal | *Planned* | - |
| **Module 07** | Audio Authenticity & Voice Forensics | Vishal | *Planned* | - |
| **Module 08** | Audio-Video Synchronization Analysis | Vishal + Yashas | *Planned* | - |
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
- [REST API: Authentication & User](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/api/authentication-user-api.md)
- [REST API: Media Ingestion](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/api/media-ingestion-api.md)
- [Database Schema: Auth V1](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/database/schema-module-01.md)
- [Database Schema: Media V2](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/database/schema-module-02.md)
- [Developer Setup Guide](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/development/setup-guide.md)
- [Testing Strategy & Test Suite](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/docs/testing/test-strategy-and-suite.md)
