# TruthLens — Master Technical & Architectural Blueprint

## Document Metadata

- **Title:** TruthLens — Master Technical & Architectural Blueprint
- **Logo:** TL
- **Status:** FINAL YEAR CAPSTONE
- **Document Type:** Final Year Engineering Capstone Blueprint
- **Source file:** `TruthLensBlueprint.html`

## Table of Contents

### Platform Architecture
- **A** Project Overview (`#sec-overview`)
- **B** User Roles & Logins (`#sec-roles`)
- **D** System Architecture (`#sec-architecture`)
- **E** Technology Stack (`#sec-tech-stack`)
- **F** Data Architecture (`#sec-data-arch`)
- **G** API Architecture (`#sec-api-arch`)
- **H** Security Architecture (`#sec-security-arch`)
- **I** Testing & Evaluation (`#sec-testing`)

### Build Modules (20)
- **01** Auth & RBAC (`#mod-01`)
- **02** Media Ingestion (`#mod-02`)
- **03** Fingerprinting (`#mod-03`)
- **04** Metadata Forensics (`#mod-04`)
- **05** Image Authenticity (`#mod-05`)
- **06** Video Deepfake (`#mod-06`)
- **07** Audio Authenticity (`#mod-07`)
- **08** AV Synchronization (`#mod-08`)
- **09** OCR Text Extract (`#mod-09`)
- **10** Speech-to-Text (`#mod-10`)
- **11** Text & Claims (`#mod-11`)
- **12** Claim Verification (`#mod-12`)
- **13** Provenance (C2PA) (`#mod-13`)
- **14** Cross-Modal Engine (`#mod-14`)
- **15** Risk Scoring Engine (`#mod-15`)
- **16** Explainable Dashboard (`#mod-16`)
- **17** Case Management (`#mod-17`)
- **18** Report Generator (`#mod-18`)
- **19** Processing Queue (`#mod-19`)
- **20** Security & Audit (`#mod-20`)
- **+** Optional Modules (`#mod-optional`)

### Study & Engineering
- **J** Study Reference (`#sec-study-reference`)
- **K** Datasets & Models (`#sec-datasets`)
- **L** Build Roadmap (`#sec-roadmap`)
- **M** Dependency Graph (`#sec-dependencies`)
- **N** Team Ownership (`#sec-team`)
- **O** Git Workflow (`#sec-git`)
- **P** Final Demo Plan (`#sec-demo`)
- **Q** Limitations (`#sec-limitations`)
- **R** Future Work (`#sec-extensions`)

FINAL YEAR ENGINEERING CAPSTONE BLUEPRINT

# TRUTHLENS

AI-Powered Multimodal Media Authenticity & Misinformation Analysis Platform

A cybersecurity-focused platform that analyzes image, video, audio and text using AI-based forensic
analysis,
provenance verification, claim analysis and multimodal evidence fusion to combat automated
misinformation.

20

Build Modules

4

Supported Modalities

6+

AI / Forensic Engines

Final Year

Capstone Scope

CORE TECH STACK:
Java Spring Boot 3.2
Python FastAPI
React 18 + TS
PyTorch
PostgreSQL 16
C2PA Credentials
Docker Compose

## SECTION A — Project Overview & Core Philosophy

Cyber Security + AI + Forensics

****TruthLens**** is a final-year engineering capstone project designed to address the
catastrophic risk posed by AI-generated deepfakes, synthetic media, and context-manipulated
misinformation across digital communication channels.

💡 Core Design Principle: Factual Truth vs Provenance vs Authenticity

****Media authenticity, provenance, and factual truth are related but distinct
concepts:****

- A **genuine, unedited photograph** can still be paired with a false headline to spread
  misinformation (Out-of-Context Media).
- An **AI-generated image** can be benign, creative, or completely truthful in a
  synthetic illustration context.
- An **authentic C2PA provenance signature** verifies who made the file, but does not
  guarantee the statement being spoken is true.

Therefore, ****TruthLens avoids binary "Real vs Fake" labels****. Instead, it computes
multi-dimensional evidence indicators, verifiable source citations, and transparent risk
explanations.

Problem Statement
THE CHALLENGE

AI-generated media enables misinformation; platforms need automated authenticity checks
across image, video, audio and text.

Proposed Solution
TRUTHLENS ARCHITECTURE

An integrated cybersecurity & forensic platform aggregating PyTorch vision/audio detectors,
C2PA manifest validators, OCR/STT text extractors, claim verification search, and an
explainable risk scoring dashboard.

Key Technical Innovation
MULTIMODAL FUSION

Cross-modal consistency scoring that cross-references visual scene semantics, audio speech
transcripts, extracted OCR text, and user captions to flag cheapfakes and context-mismatched
content.

#### Cyber Security Relevance

Integrates STRIDE threat modeling, OWASP file upload isolation, rate
limiting, append-only security audit logging, and protection against adversarial model
perturbations.

#### Artificial Intelligence Relevance

Leverages deep learning for Diffusion/GAN detection, 3D-CNN video deepfake
classification, zero-shot audio voice cloning detection, Whisper speech recognition, and
spaCy NER.

#### Digital Forensics Relevance

Extracts EXIF/container metadata anomalies, performs Error Level Analysis
(ELA), evaluates frequency FFT domain noise variance, and parses C2PA cryptographic
credentials.

## SECTION B — User Logins & Role Permissions Matrix

Access Control

TruthLens enforces Role-Based Access Control (RBAC) across 5 distinct system roles to ensure proper
segregation of duties between casual users, forensic investigators, moderators, and administrators.

| User Role | Login Method | Permissions & System Capabilities | Target Persona |
| --- | --- | --- | --- |
| ****1. User**** | Email + Password / JWT | Upload media files, trigger standard analysis, view basic risk score summaries, export user summary reports. | General Public, Journalists |
| ****2. Analyst / Investigator**** | JWT + 2FA / Secure Auth | Full access to ELA heatmaps, Grad-CAM overlays, video deepfake frame markers, create & manage investigation cases, add analyst notes, export digitally signed PDF reports. | Cybersecurity Analysts, Digital Forensic Experts |
| ****3. Moderator / Fact Checker**** | JWT / Internal Auth | Review flagged media queues, inspect claim extraction details, evaluate evidence retrieval sources, approve or dispute automated claim verdicts. | Fact-Checking Organizations, Media Content Moderators |
| ****4. Administrator**** | Strict MFA + Dedicated Auth | Manage user accounts & roles, configure risk scoring weighting parameters, adjust model detection thresholds, monitor system health, inspect append-only security audit logs. | System Ops, Lead Engineers |
| ****5. Researcher**** | JWT / Read-Only Access | View AI model evaluation benchmarks, precision/recall curves, false-positive distributions, register benchmark datasets for evaluation. | Academic Evaluators, ML Engineers |

#### AUTHENTICATION & RBAC FLOW DIAGRAM

#### Diagram 1 — Extracted Diagram Data
- User Login Request
- Spring Security Filter
- BCrypt / DB Auth Check
- JWT Token Issuance
- Protected APIs
\*\*Flow:\*\* User Login Request → Spring Security Filter → BCrypt / DB Auth Check → JWT Token Issuance → Protected APIs

## SECTION C — The TruthLens Modules (20 Build Modules)

20 Software Components

🎯 STRICT MODULE DEFINITION RULE

****The numbered modules below represent actual product capabilities that the team has to
build.****
There is NO study material, textbook chapters, or phase-by-phase development instructions inside
these module cards. Study material is isolated in Section J.

All 20 Modules
Core MVP (14)
Advanced (6)

Module 01 — Authentication, RBAC & User Management

CORE

Core Security

****Who Uses It:****
User, Analyst, Moderator, Admin, Researcher

What It Does

Provides user registration, login authentication, JWT token
issuance, password hashing, session validation, user profile management, and
role-based route protection across frontend and backend.

Architecture Flow

React Auth Form → Auth Controller (/api/auth) → Spring Security 6
→ BCrypt → PostgreSQL (users, roles) → Signed JWT → Protected API Guard

Data Architecture

Tables: `users`, `roles`,
`user_roles`, `revoked_tokens`.

Build Scope

Spring Security filter chain, JWT provider, Auth Controller
endpoints, User Profile CRUD service, React Login/Register components, RBAC route
guards.

****Integration:**** Protects all API endpoints across Modules 02 through 20. |
****Primary Owner:**** Yashas

Module 02 — Media Upload & Secure Ingestion

CORE

Core Infrastructure

****Who Uses It:****
User, Analyst, Moderator

What It Does

Central ingestion gateway supporting Image, Video, Audio, and
Text uploads with magic-byte MIME validation, file size enforcement, path traversal
protection, SHA-256 hash generation, and quarantined storage.

Architecture Flow

React Dropzone → Multipart API (/api/media/upload) → Apache Tika
MIME Check → SHA-256 Hasher → MinIO / Storage → PostgreSQL (media)

Data Architecture

Tables: `media`; Storage: Quarantined S3/MinIO
bucket.

Build Scope

Spring Boot multipart file handler, Apache Tika validation
filter, SHA-256 hasher, MinIO storage manager, React Drag-and-Drop Dropzone UI.

****Integration:**** Ingests media for Modules 03, 04, 05, 06, 07, 09, 10, 19. |
****Primary Owner:**** Yashas

Module 03 — Media Fingerprinting & Duplicate Detection

CORE

Core Forensics

****Who Uses It:****
Analyst, Moderator, System

What It Does

Generates SHA-256 cryptographic hashes, image perceptual hashes
(pHash/dHash), and audio acoustic fingerprints to detect exact duplicates and visual
near-matches against previously analyzed media.

Architecture Flow

Ingested Media Stream → Java SHA-256 + Python pHash Engine →
PostgreSQL (media_hashes) → Vector Similarity Search → Duplicate Match Flag

Data Architecture

Tables: `media_hashes` (sha256, phash_vector,
chromaprint).

Build Scope

Java MessageDigest SHA-256 generator, Python pHash vector
calculator, hash collision lookup service, duplicate alert UI widget.

****Integration:**** Receives file from Module 02; informs Modules 15, 16. |
****Primary Owner:**** Yashas + Vishal

Module 04 — Metadata & Digital Forensics

CORE

Core Forensics

****Who Uses It:****
Analyst, Investigator

What It Does

Parses EXIF headers, camera profiles, timestamps, GPS
coordinates, editing software tags (e.g., Photoshop), video container headers,
codecs, and audio sampling metadata to output a metadata forensic report.

Architecture Flow

Media File → ExifTool / MediaInfo Wrapper → JSON Metadata
Extractor → Anomaly Detection Rules → Metadata Forensic Score

Data Architecture

Tables: `metadata` (raw_json, camera_model,
software_tag, anomaly_flags).

Build Scope

ExifTool and MediaInfo CLI wrapper service, metadata anomaly
evaluator, JSON metadata tree parser, React EXIF Viewer component.

****Integration:**** Receives file from Module 02; feeds Module 15 (Risk Engine). |
****Primary Owner:**** Vishal + Yashas

Module 05 — Image Authenticity Analysis

CORE

AI Vision & Forensics

****Who Uses It:****
Analyst, User, Moderator

What It Does

Dual-engine image analyzer detecting synthetic AI generation
(Diffusion/GANs) and localized physical manipulations (Error Level Analysis - ELA,
copy-move tampering, splicing, noise inconsistency, FFT frequency anomalies).

Architecture Flow

Image Tensor → Python FastAPI → PyTorch Model (Diffusion
Classifier) + OpenCV ELA Generator → AI Prob & ELA Heatmap PNG → Spring Boot Backend

Data Architecture

Tables: `image_analysis` (ai_prob, ela_heatmap_url,
manipulation_prob).

Build Scope

PyTorch vision model inference wrapper, OpenCV ELA heatmap
generator, noise variance calculator, Grad-CAM attention exporter, FastAPI
endpoints.

****Integration:**** Triggered by Module 19; feeds Module 15 (Risk Engine), Module
16 (Dashboard). | ****Primary Owner:**** Vishal

Module 06 — Video Deepfake & Forensic Analysis

CORE

AI Video & Forensics

****Who Uses It:****
Analyst, Investigator, Moderator

What It Does

Extracts video keyframes, performs facial detection and
tracking, evaluates face-swap deepfakes, analyzes temporal frame inconsistency,
scores frame-level artifacts, and marks suspicious timestamps.

Architecture Flow

Video File → FFmpeg Sampler → RetinaFace Detector → PyTorch 3D-CNN
/ EfficientNet → Suspicious Frame Array → Video Deepfake Score

Data Architecture

Tables: `video_analysis` (deepfake_prob,
suspicious_timestamps, frame_scores_json).

Build Scope

FFmpeg frame extraction pipeline, RetinaFace face bounding box
tracker, PyTorch deepfake classifier, timeline timestamp marker, FastAPI video
service.

****Integration:**** Triggered by Module 19; feeds Module 08 (AV Sync), Module 15
(Risk Engine). | ****Primary Owner:**** Vishal

Module 07 — Audio Authenticity & Voice Forensics

CORE

AI Audio Forensics

****Who Uses It:****
Analyst, Investigator

What It Does

Detects synthetic speech generation, neural voice cloning
(ElevenLabs/Bark), audio splicing boundaries, Mel-spectrogram frequency anomalies,
phase discontinuities, and acoustic pitch variance.

Architecture Flow

Audio Track → Librosa Spectrogram Extractor → PyTorch AASIST
Classifier → Mel-Spectrogram Image + Voice Cloning Probability

Data Architecture

Tables: `audio_analysis` (synthetic_voice_prob,
spectrogram_url, pitch_variance).

Build Scope

Librosa acoustic feature extractor, Mel-spectrogram generator
script, PyTorch voice cloning detector, spectrogram UI visualizer.

****Integration:**** Triggered by Module 19; feeds Module 08 (AV Sync), Module 10
(STT), Module 15 (Risk Engine). | ****Primary Owner:**** Vishal

Module 08 — Audio-Video Synchronization Analysis

ADVANCED

Advanced AV Sync

****Who Uses It:****
Analyst, Investigator

What It Does

Measures physical alignment between spoken audio phonemes and
visual lip movements (visemes) to detect dubbed audio, replaced voice tracks, and
lip-sync deepfakes.

Architecture Flow

Video + Audio Tracks → MediaPipe Lip Tracker + Audio Envelope
Correlator → SyncNet Evaluator → AV Sync Score + Mismatch Timestamps

Data Architecture

Tables: `av_sync_analysis` (sync_score,
lip_offset_ms, mismatch_segments).

Build Scope

Lip landmark extraction pipeline, audio envelope
cross-correlator, SyncNet offset calculator microservice, offset timeline UI
component.

****Integration:**** Receives inputs from Modules 06, 07; feeds Module 14
(Cross-Modal), Module 15 (Risk Engine). | ****Primary Owner:**** Vishal + Yashas

Module 09 — OCR & Visual Text Extraction

CORE

Core Vision NLP

****Who Uses It:****
Analyst, Moderator, System

What It Does

Extracts embedded visual text from images, video keyframes,
social media screenshots, news banners, posters, and memes using Optical Character
Recognition (OCR), providing language detection and text region bounding boxes.

Architecture Flow

Image/Frame → Binarization Preprocessor → Tesseract / EasyOCR
Engine → Extracted Text Strings + Bounding Boxes → Claim Engine

Data Architecture

Tables: `ocr_results` (extracted_text,
bounding_boxes_json, language).

Build Scope

OpenCV image preprocessor (contrast, binarization),
Tesseract/EasyOCR integration, text box coordinate mapper, React OCR Overlay
component.

****Integration:**** Triggered by Module 02/19; feeds Module 11 (Claim Analysis). |
****Primary Owner:**** Vishal

Module 10 — Speech-to-Text & Transcript Extraction

CORE

Core Speech NLP

****Who Uses It:****
Analyst, User, Moderator

What It Does

Transcribes spoken speech from audio tracks and video clips into
timestamped text transcripts with language detection, confidence scores, and
word-level timing offsets.

Architecture Flow

Audio Stream → Faster-Whisper ASR Microservice → Timestamped Text
Transcript JSON → Claim Engine

Data Architecture

Tables: `transcripts` (full_text,
timestamp_segments_json, language).

Build Scope

Faster-Whisper speech-to-text service wrapper, transcript
segmenter, timestamp alignment parser, React interactive transcript player.

****Integration:**** Triggered by Module 19; feeds Module 11 (Claim Analysis),
Module 14 (Cross-Modal). | ****Primary Owner:**** Vishal

Module 11 — Text & Claim Analysis

CORE

Core NLP

****Who Uses It:****
Analyst, Moderator, Fact Checker

What It Does

Parses extracted OCR text and audio transcripts using Named
Entity Recognition (NER) and NLP claim decomposition to extract factual statements,
entities (people, places, amounts, dates), and verifiable claims.

Architecture Flow

Raw Transcript & OCR Text → spaCy / HuggingFace NER → Sentence
Classifier → Structured Claim Objects (Entity, Action, Value)

Data Architecture

Tables: `claims` (claim_text, entity_type, subject,
claim_hash).

Build Scope

spaCy / Transformer NLP pipeline, claim extraction rules, entity
tagger, claim normalization service, React Claim List UI.

****Integration:**** Receives input from Modules 09, 10; feeds Module 12 (Claim
Verification), Module 15 (Risk Engine). | ****Primary Owner:**** Vishal + Yashas

Module 12 — Claim Verification & Evidence Retrieval

CORE

Core Evidence & Search

****Who Uses It:****
Analyst, Moderator, Fact Checker

What It Does

Queries trusted news APIs, fact-check databases, and vector
search indices to retrieve supporting or contradicting evidence for extracted
claims, classifying verdicts as Supported, Partially Supported, Contradicted,
Unverified, or Insufficient Evidence.

Architecture Flow

Claim Object → Vector Similarity Search (FAISS/OpenSearch) +
Fact-Check API → Evidence Ranker → Verdict Classification + Source Citations

Data Architecture

Tables: `evidence`, `sources`,
`claim_verdicts` (verdict_enum, similarity_score, source_url).

Build Scope

Vector search query builder, fact-check API client, evidence
ranking algorithm, source citation formatter, React Evidence Cards UI.

****Integration:**** Communicates with Module 11; feeds Module 15 (Risk Engine),
Module 16 (Dashboard), Module 18 (Reports). | ****Primary Owner:**** Yashas +
Vishal

Module 13 — Provenance & Content Credentials (C2PA)

ADVANCED

Advanced Cryptography

****Who Uses It:****
Analyst, Investigator

What It Does

Parses and cryptographically validates embedded C2PA (Coalition
for Content Provenance and Authenticity) manifests, Content Credentials, digital
signatures, and asset modification history.

Architecture Flow

Media Header → C2PA JUMBF Parser → X.509 Certificate Chain
Validator → Assertion History Tree → Provenance Status (VERIFIED / INVALID / ABSENT)

Data Architecture

Tables: `provenance_manifests` (c2pa_status, issuer,
signing_time, edit_actions_json).

Build Scope

C2PA Rust/Python SDK wrapper, X.509 certificate chain verifier,
editing lineage tree parser, React Content Credentials badge & tree UI.

****Integration:**** Receives file from Module 02; feeds Module 15 (Risk Engine),
Module 16 (Dashboard). | ****Primary Owner:**** Yashas + Vishal

Module 14 — Cross-Modal Consistency Analysis

ADVANCED

Advanced Multimodal NLP/Vision

****Who Uses It:****
Analyst, Researcher

What It Does

Cross-references visual scene content, audio speech transcript,
OCR text, and user-provided captions using multimodal embeddings (CLIP/ImageBind) to
compute a Cross-Modal Consistency Score and detect out-of-context miscaptioning.

Architecture Flow

Visual Embeddings + Audio Transcript + User Caption → CLIP /
ImageBind Encoder → Cosine Similarity Matrix → Cross-Modal Alignment Score

Data Architecture

Tables: `cross_modal_results` (alignment_score,
mismatch_flags_json).

Build Scope

Multimodal embedding generator, cross-modal similarity matrix
calculator, context mismatch detector, React Cross-Modal Radar Chart component.

****Integration:**** Communicates with Modules 05, 06, 09, 10, 11; feeds Module 15
(Risk Engine). | ****Primary Owner:**** Vishal + Yashas

Module 15 — Authenticity & Risk Scoring Engine

CORE

Core Decision Support

****Who Uses It:****
Analyst, User, Moderator, Admin

What It Does

Central decision-support aggregator synthesizing multi-engine
evidence (AI prob, forensics, EXIF, C2PA, claim verdicts, cross-modal alignment)
into 6 independent scores (Authenticity, Provenance, Claim Credibility, Manipulation
Risk, AI Prob, Overall Risk) with clear auditability.

Architecture Flow

Engine Outputs (Mods 04-14) → Weighting Matrix & Dynamic
Calibrator → 6 Calibrated Risk Scores + Key Evidence Reason Codes → Analysis Results
Object

Data Architecture

Tables: `analysis_results`, `risk_scores`
(overall_risk, authenticity_score, provenance_score, claim_credibility_score).

Build Scope

Multi-factor risk aggregation algorithm, dynamic score
calibrator, evidence reason code generator, configurable weighting model in Spring
Boot.

****Integration:**** Aggregates Modules 04-14; feeds Modules 16, 17, 18. |
****Primary Owner:**** Yashas

Module 16 — Explainable Analysis & Results Dashboard

CORE

Core Frontend / XAI

****Who Uses It:****
User, Analyst, Moderator

What It Does

Interactive analysis portal displaying overall risk gauges,
confidence meters, Grad-CAM heatmaps, video deepfake timeline markers,
Mel-spectrogram visualizers, evidence cards, EXIF data, and plain-English
explanations.

Architecture Flow

Backend Analysis JSON → React 18 UI Portal → Recharts Gauges +
HTML Canvas Overlay (Heatmaps) + Interactive Timelines → User Screen

Data Architecture

Client-side rendering of `analysis_results` context
object.

Build Scope

React Dashboard components, Recharts risk radial meters, HTML
Canvas Grad-CAM heatmap overlay renderer, interactive video timeline controller,
claim verdict cards.

****Integration:**** Renders output from Modules 03-15. | ****Primary
Owner:**** Sudheendra + Yashas

Module 17 — Investigation Case Management

ADVANCED

Advanced Case Console

****Who Uses It:****
Analyst, Investigator, Moderator

What It Does

Enables cybersecurity analysts and fact-checkers to group
multiple media files into investigation cases, assign case IDs, record notes, track
status (OPEN, INVESTIGATING, REVIEWED, RESOLVED, ARCHIVED), and manage analyst
assignments.

Architecture Flow

React Case Console → Case Management APIs → PostgreSQL
(investigations, case_media, analyst_notes) → Dossier Summary

Data Architecture

Tables: `investigations`, `case_media`,
`analyst_notes` (case_id, status_enum, analyst_id).

Build Scope

Case CRUD Spring Boot APIs, case dossier data models, note
tagging feature, status lifecycle state machine, React Case Board view.

****Integration:**** Links to Modules 02, 15, 16, 18. | ****Primary
Owner:**** Yashas + Sudheendra

Module 18 — Report Generation & Evidence Export

CORE

Core Reporting

****Who Uses It:****
Analyst, User, Investigator

What It Does

Compiles comprehensive analysis and investigation results into
exportable, cryptographically signed PDF reports, machine-readable JSON files, and
shareable web link reports containing complete evidence chains and QR verification
codes.

Architecture Flow

Analysis Result Context → Thymeleaf HTML Template → iText PDF
Compiler + Digital Signature Key → Signed PDF File Stream + QR Link

Data Architecture

Tables: `reports`, `report_signatures`
(report_id, digital_signature, qr_code_url).

Build Scope

Thymeleaf PDF layout template, iText PDF generation engine,
digital signature applier, QR code generator, report download endpoints.

****Integration:**** Pulls data from Modules 03-17. | ****Primary
Owner:**** Yashas + Sudheendra

Module 19 — Analysis Job Management & Processing Queue

CORE

Core Infrastructure

****Who Uses It:****
System, Admin

What It Does

Asynchronous background processing queue managing long-running
AI vision, video deepfake, and audio speech analysis tasks through state transitions
(UPLOADED → QUEUED → PROCESSING → COMPLETED / FAILED / CANCELLED).

Architecture Flow

Upload Trigger → Spring Async Task Launcher → Redis Task Queue →
Python ML Worker Nodes → Job State Updater (Postgres) → WebSocket Client
Notification

Data Architecture

Tables: `analysis_jobs` (job_id, status_enum,
progress_pct, error_log).

Build Scope

Redis job queue publisher/listener, Spring Async background
orchestrator, progress tracker, retry & failure handler, WebSocket notification
gateway.

****Integration:**** Orchestrates execution of Modules 04-14. | ****Primary
Owner:**** Yashas

Module 20 — Security, Audit & System Monitoring

CORE

Core Cybersecurity

****Who Uses It:****
Admin, Security QA (Manoj)

What It Does

Implements immutable append-only audit logging for all
authentication events, file uploads, score overrides, and administrative actions,
alongside API rate limiting, input sanitization, and security event alerts.

Architecture Flow

Spring AspectJ Interceptor → Audit Log Event Publisher →
Append-Only PostgreSQL Log Table (audit_logs) → Admin Monitoring Console

Data Architecture

Tables: `audit_logs` (log_id, action_type, user_id,
ip_address, timestamp, payload_hash).

Build Scope

Spring AOP audit interceptor, append-only database table
migration, OWASP input validation filters, rate limiting middleware, Admin Security
Console UI.

****Integration:**** Monitors and logs activity across all Modules 01-19. |
****Primary Owner:**** Manoj + Yashas


### Optional Scope Extensions (Separated from Core 20)

POST-MVP SCOPE

These capabilities are optional extensions if the core 20 modules are completed early. They do
NOT inflate the primary 20 development modules required for capstone completion.

Optional Module A — Model Management Platform
OPTIONAL

Model registry database, version comparison dashboard, batch evaluation
runner tracking accuracy, precision, recall, and ROC-AUC curve performance.

Optional Module B — Research Dataset Manager
OPTIONAL

Registration console for benchmark datasets (FaceForensics++,
DeepfakeDetection, ASVspoof), sample extraction, and ground-truth validation runner.

Optional Module C — Real-Time Media Analysis
OPTIONAL

Live video stream frame sampling, real-time audio chunk spectrogram
analysis, and WebSocket alert push for streaming media moderation.

Optional Module D — Browser Extension
OPTIONAL

Chrome/Firefox extension allowing users to submit web images, social
media posts, and news URLs directly to TruthLens for automated authenticity checks.

Optional Module E — Platform API & Webhook Integration
OPTIONAL

Public REST API gateway with API key management, rate limits, and
Webhook callbacks for third-party platforms to query TruthLens analysis services.

## SECTION D — System Architecture ("How It All Connects")

System Topology

TruthLens follows a decoupled microservice architecture separating the user-facing React web client,
the Java Spring Boot orchestration gateway, the Python FastAPI AI inference engines, and the
persistent storage layer.

#### TRUTHLENS END-TO-END SYSTEM ARCHITECTURE

#### Diagram 2 — Extracted Diagram Data
- TRUTHLENS WEB CLIENT (React 18 + TypeScript + Vite)
- Dashboard • Dropzone • XAI Heatmaps • Case Board • Reports
- SPRING BOOT 3.2 BACKEND ORCHESTRATION GATEWAY
- Spring Security (JWT) • Media Ingestion • Job Queue (Redis) • Case Manager • Audit Logger
- REST APIs (/api/auth, /api/media, /api/analysis, /api/reports)
- IMAGE ENGINE
- PyTorch Vision
- Diffusion / ELA / FFT
- VIDEO ENGINE
- RetinaFace + 3D-CNN
- Deepfake / Timestamps
- AUDIO ENGINE
- Librosa + AASIST
- Mel-Spectrogram / Voice AI
- OCR & STT ENGINE
- Faster-Whisper
- Tesseract OCR
- CLAIMS & C2PA
- spaCy NER + FAISS
- C2PA JUMBF Manifests
- AUTHENTICITY & RISK SCORING ENGINE (Module 15)
- Synthesizes 6 Scores (Authenticity, Provenance, Claims, Manipulation, AI Prob, Overall Risk)
- PERSISTENT STORAGE LAYER
- PostgreSQL 16 (Relational DB)
- MinIO / S3 Object Store
- Redis / Vector Store
\*\*Architecture flow represented:\*\* React web client → Spring Boot orchestration gateway → specialized analysis engines → Authenticity & Risk Scoring Engine → persistent storage.

## SECTION E — Technology Stack Classification

Tech Specifications

#### Frontend Layer

- ****Core Framework:**** React 18 with TypeScript
- ****Build Tool:**** Vite
- ****Styling:**** Tailwind CSS + CSS Variables
- ****Visualizations:**** Recharts (Radial Risk Gauges) + HTML Canvas (Heatmaps)
- ****HTTP Client:**** Axios

#### Backend Orchestration

- ****Language:**** Java 21 LTS
- ****Framework:**** Spring Boot 3.2
- ****Security:**** Spring Security 6 (JWT + RBAC)
- ****Data Access:**** Spring Data JPA / Hibernate
- ****Reporting:**** Thymeleaf + iText PDF Compiler

#### AI / ML & Microservices

- ****Language:**** Python 3.11
- ****Microservice Gateway:**** FastAPI (Async Uvicorn)
- ****DL Framework:**** PyTorch 2.2
- ****Vision & Video:**** OpenCV, FFmpeg, RetinaFace, timm
- ****Audio & Speech:**** Librosa, Faster-Whisper, AASIST
- ****NLP & Claims:**** spaCy, HuggingFace Transformers, Tesseract OCR

#### Data & DevOps

- ****Relational DB:**** PostgreSQL 16
- ****Object Storage:**** MinIO / Local Disk Quarantine
- ****Queue & Cache:**** Redis
- ****Containerization:**** Docker + Docker Compose
- ****CI/CD:**** GitHub Actions

## SECTION F — Data Architecture & Entity Schema

Database Entities

TruthLens uses PostgreSQL 16 as its relational data store. Below are the primary entities and
relationships governing user access, media tracking, analysis outputs, claims, evidence, and audit
trails.

| Database Entity | Primary Key | Key Foreign Keys | Description & Core Columns |
| --- | --- | --- | --- |
| `users` | `id (UUID)` | - | User account records (email, password_hash, status, created_at). |
| `roles` | `id (UUID)` | - | System access roles (USER, ANALYST, MODERATOR, ADMIN, RESEARCHER). |
| `media` | `id (UUID)` | `user_id -> users.id` | Central registry for ingested media (original_name, mime_type, file_size, storage_path, upload_status). |
| `media_hashes` | `id (UUID)` | `media_id -> media.id` | Fingerprinting table storing cryptographic sha256_hash, phash_vector, and chromaprint_hash. |
| `metadata` | `id (UUID)` | `media_id -> media.id` | EXIF and container header details (camera_model, editing_software, raw_exif_json, anomaly_flags). |
| `analysis_jobs` | `id (UUID)` | `media_id -> media.id` | Asynchronous job queue status tracking (job_status, progress_pct, retry_count, error_log). |
| `analysis_results` | `id (UUID)` | `media_id, job_id` | Synthesized risk scores (overall_risk, authenticity_score, provenance_score, claim_score, reasoning_json). |
| `image_analysis` | `id (UUID)` | `media_id -> media.id` | Image specific AI outputs (synthetic_prob, ela_heatmap_path, noise_variance). |
| `video_analysis` | `id (UUID)` | `media_id -> media.id` | Video deepfake outputs (deepfake_prob, suspicious_timestamps_json, face_count). |
| `audio_analysis` | `id (UUID)` | `media_id -> media.id` | Audio voice forensics (synthetic_voice_prob, spectrogram_url, pitch_contour). |
| `claims` | `id (UUID)` | `media_id -> media.id` | Extracted factual statements (claim_text, entity_name, subject, normalized_claim). |
| `evidence` | `id (UUID)` | `claim_id -> claims.id` | Retrieved evidence sources (verdict_enum, similarity_score, source_url, snippet_text). |
| `provenance` | `id (UUID)` | `media_id -> media.id` | C2PA credentials manifest (c2pa_status, cert_issuer, sign_time, edit_actions_json). |
| `investigations` | `id (UUID)` | `analyst_id -> users.id` | Analyst case dossiers (case_number, case_title, status_enum, analyst_notes). |
| `reports` | `id (UUID)` | `media_id, case_id` | Generated forensic reports (pdf_storage_path, report_hash, digital_signature, qr_code). |
| `audit_logs` | `id (UUID)` | `user_id -> users.id` | Append-only security log (action_type, ip_address, timestamp, payload_hash). |

## SECTION G — REST API Route Architecture

API Endpoints

| HTTP Method | API Route Endpoint | Role Required | Description & Functionality |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | PUBLIC | Register new user account. |
| POST | `/api/auth/login` | PUBLIC | Authenticate credentials & return JWT bearer token. |
| POST | `/api/media/upload` | USER+ | Upload raw media file for MIME validation & ingestion. |
| GET | `/api/analysis/{jobId}/status` | USER+ | Poll async background job processing status. |
| GET | `/api/analysis/{mediaId}/results` | USER+ | Fetch complete aggregated risk scores & evidence. |
| POST | `/api/image/analyze` | INTERNAL / API | Execute PyTorch vision model & ELA heatmap generator. |
| POST | `/api/video/analyze` | INTERNAL / API | Execute FFmpeg frame sampling & deepfake classifier. |
| POST | `/api/audio/analyze` | INTERNAL / API | Execute Librosa spectrogram extraction & voice AI detector. |
| POST | `/api/claims/extract` | ANALYST+ | Extract factual claim statements from text/audio transcripts. |
| POST | `/api/evidence/verify` | ANALYST+ | Execute vector search & retrieve fact-checking evidence. |
| POST | `/api/provenance/verify` | ANALYST+ | Parse embedded C2PA manifests & check cert chain. |
| POST | `/api/investigations/cases` | ANALYST+ | Create new investigation case dossier. |
| POST | `/api/reports/export-pdf` | ANALYST+ | Compile & download digitally signed PDF forensic report. |
| GET | `/api/admin/audit-logs` | ADMIN | Retrieve append-only security audit log history. |

## SECTION H — Security Architecture & Threat Model

Cybersecurity Controls

#### Application Security

JWT token verification, Spring Security RBAC filter chains, OWASP input
sanitization to prevent XSS/SQLi, Redis token-bucket rate limiting per IP/user.

#### Media Upload Security

Magic-byte MIME verification via Apache Tika, file size limits (50MB image,
500MB video), anti-malware quarantine storage, path traversal block filters.

#### AI Model Security

Multi-indicator ensemble scoring to prevent zero-day adversarial noise
evasion, prompt injection filtering on NLP text extractors, model weight checksum
verification.

#### Data & Audit Security

TLS 1.3 encryption in transit, AES-256 at rest, BCrypt password hashing,
immutable append-only audit tables for all authentication and administrative actions.

## SECTION I — Multi-Tiered Testing & Evaluation

Quality & AI Metrics

#### 🧪 Software Integration Testing

JUnit 5 / Mockito unit tests for Spring Boot backend controllers; pytest
unit tests for Python ML services; React component testing with Vitest.

#### 🛡️ Security Penetration Testing

OWASP ZAP automated vulnerability scanning, Burp Suite manual API testing,
malicious file upload fuzzing, IDOR authorization verification.

#### 📊 AI Model Evaluation Metrics

Model performance evaluated against benchmark test datasets using
Precision, Recall, F1-Score, ROC-AUC curves, Confusion Matrices, and False Positive/Negative
trade-off tracking.

## SECTION J — Study & Research Reference

Domain Knowledge Base

📚 MANDATORY DISTINCTION: KNOWLEDGE REQUIREMENTS

****These topics represent domain knowledge, standards, and theories the team must master to
make sound technical decisions.****
They are NOT separate development modules to code.

#### S1 — Generative AI & Synthetic Media

****What It Is:**** Diffusion models, GANs, Neural Text-to-Speech
(TTS), and LLMs.
****Why TruthLens Needs It:**** To understand how synthetic
visual/audio artifacts originate.
Supports:
Module 05, 06, 07

#### S2 — Digital Image Forensics

****What It Is:**** Error Level Analysis (ELA), JPEG compression
quantization, noise variance, FFT frequencies.
****Why TruthLens Needs It:****
To formulate image manipulation detection algorithms.
Supports: Module 05

#### S3 — Deepfake Video Technologies

****What It Is:**** Face swapping, expression reenactment,
boundary blending, temporal frame artifacts.
****Why TruthLens Needs It:**** To
design frame sampling and facial artifact tracking pipelines.
Supports: Module 06, 08

#### S4 — Audio Forensics & Voice AI

****What It Is:**** Mel-spectrogram analysis, spectral flux, phase
continuity, zero-shot voice cloning.
****Why TruthLens Needs It:**** To
configure synthetic voice detection models.
Supports: Module 07

#### S5 — C2PA & Content Credentials

****What It Is:**** C2PA specifications, JUMBF metadata
containers, X.509 cert chains, digital signatures.
****Why TruthLens Needs
It:**** To implement cryptographic provenance verification.
Supports: Module 13

#### S6 — Misinformation & Claim Verification

****What It Is:**** Fact-checking methodologies, cheapfakes,
vector similarity search, claim extraction.
****Why TruthLens Needs It:**** To
build claim verification and evidence retrieval workflows.
Supports: Module 11, 12, 14

## SECTION K — Datasets & Model Benchmark Research

Research Datasets

| Media Category | Benchmark Datasets Used | Evaluation Methodology |
| --- | --- | --- |
| ****AI & Real Images**** | CIFAKE, Midjourney-v6 Bench, COCO, Flickr30k | 70/15/15 train/val/test split; evaluated on synthetic vs authentic classification accuracy. |
| ****Video Deepfakes**** | FaceForensics++, DeepFake Detection Challenge (DFDC), Celeb-DF | Frame-level and video-level ROC-AUC score comparison across face swap algorithms. |
| ****Synthetic Speech**** | ASVspoof 2021, LJSpeech, LibriSpeech | Equal Error Rate (EER) measurement on zero-shot neural voice cloning samples. |
| ****Claims & Evidence**** | FEVER, MultiFC, LIAR Dataset | Precision and recall evaluation on claim extraction and vector evidence retrieval ranking. |

## SECTION L — 8-Month Build Roadmap

Phase Schedule

| Roadmap Period | Development Focus & Objectives | Modules Included |
| --- | --- | --- |
| ****Phase 1: Foundation (Months 1–2)**** | System scaffolding, database schema, Spring Boot JWT Auth, media ingestion pipeline, SHA-256 fingerprinting. | Modules 01, 02, 03 |
| ****Phase 2: Media Intelligence (Months 3–4)**** | EXIF metadata parser, PyTorch image authenticity model, ELA generator, FFmpeg video frame extractor, PyTorch audio voice classifier. | Modules 04, 05, 06, 07 |
| ****Phase 3: Language & Evidence (Months 5–6)**** | Tesseract OCR, Faster-Whisper speech-to-text, spaCy claim extraction NLP, FAISS vector evidence search engine. | Modules 09, 10, 11, 12 |
| ****Phase 4: Trust & Fusion (Month 7)**** | SyncNet AV lip-sync, C2PA manifest validator, cross-modal CLIP consistency engine, multi-indicator Risk Aggregator. | Modules 08, 13, 14, 15 |
| ****Phase 5: Platform & Investigation (Month 8)**** | React Dashboard UI, Investigation Case Management, iText PDF Report Generator, Redis Async Queue, Security Audit Logging. | Modules 16, 17, 18, 19, 20 |

## SECTION M — Module Dependency Graph

Execution Flow

#### MODULE EXECUTION & DEPENDENCY FLOW

#### Diagram 3 — Extracted Diagram Data
- 01 Auth & RBAC
- 02 Media Ingestion
- 03 Fingerprinting
- 04 Metadata Forensics
- 19 Analysis Queue
- 05 Image Engine
- 06 Video Engine
- 07 Audio Engine
- 09/10 OCR & STT
- 13 C2PA Provenance
- 11/12 Claim & Evidence
- 15 Risk Scoring Engine
\*\*Dependency flow represented:\*\* Auth/RBAC + Media Ingestion + Fingerprinting + Metadata Forensics → analysis engines (Image, Video, Audio, OCR/STT, C2PA, Claims/Evidence) → Risk Scoring Engine.

## SECTION N — Team Responsibility Matrix

4-Member Team Ownership

| Module Number & Name | Yashas (Lead) | Vishal (AI-ML) | Sudheendra (UI) | Manoj (QA/Security) |
| --- | --- | --- | --- | --- |
| Module 01 — Auth & RBAC | LEAD | Support | UI Integration | Security Audit |
| Module 02 — Media Ingestion | LEAD | Support | Dropzone UI | Malware Check |
| Module 03 — Fingerprinting | LEAD | Support | Informed | Collision Test |
| Module 04 — Metadata Forensics | Integration | LEAD | EXIF View UI | Metadata Test |
| Module 05 — Image Authenticity | Integration | LEAD | Heatmap UI | Benchmark Test |
| Module 06 — Video Deepfake | Integration | LEAD | Timeline UI | Benchmark Test |
| Module 07 — Audio Authenticity | Integration | LEAD | Spectrogram UI | Benchmark Test |
| Module 08 — AV Synchronization | Integration | LEAD | Offset UI | Evaluation |
| Module 09 — OCR Text Extraction | Integration | LEAD | OCR Overlay UI | Test |
| Module 10 — Speech-to-Text | Integration | LEAD | Transcript Player UI | Test |
| Module 11 — Text & Claim Analysis | Support | LEAD | Claim List UI | NLP Testing |
| Module 12 — Claim Verification | LEAD | LEAD | Evidence Cards UI | API Test |
| Module 13 — C2PA Provenance | LEAD | Support | Provenance Tree UI | Security Audit |
| Module 14 — Cross-Modal Engine | Integration | LEAD | Radar Chart UI | Evaluation |
| Module 15 — Risk Scoring Engine | LEAD | Weight Support | Renders Scores UI | Calibration Test |
| Module 16 — Explainable Dashboard | Integration | Support | LEAD | UI/UX Testing |
| Module 17 — Case Management | Support | Informed | LEAD | QA Test |
| Module 18 — Report Generator | LEAD | Informed | LEAD | PDF Audit |
| Module 19 — Processing Queue | LEAD | Support | Status Monitor UI | Load Test |
| Module 20 — Security & Audit | Support | Informed | Informed | LEAD |

## SECTION O — Git & Branching Strategy

Dev Workflow

#### GIT BRANCHING & PULL REQUEST WORKFLOW

#### Diagram 4 — Extracted Diagram Data
- main
- feature/backend-auth
- feature/ai-vision
- PR #12 Merged
- PR #15 Merged
\*\*Git flow represented:\*\* `main` with feature branches `feature/backend-auth` and `feature/ai-vision`, followed by merged pull requests PR #12 and PR #15.

## SECTION P — Final Demo Strategy & Trace

5 Demo Moments

#### Demo Moment 1: Suspicious Upload

Upload an AI-generated image paired with a fake viral news caption via
React Dropzone.

#### Demo Moment 2: Async Pipeline

Demonstrate progress state transitions: Uploaded $\rightarrow$ Queued
$\rightarrow$ Processing $\rightarrow$ Completed.

#### Demo Moment 3: XAI Report View

Render overall risk score gauge (88/100 HIGH RISK), ELA heatmap overlays,
and claim verification source links.

#### Demo Moment 4: Multimodal Deepfake

Demonstrate a video clip with deepfake face swap and cloned voice audio,
highlighting timeline markers and AV sync offset.

#### Demo Moment 5: Analyst PDF Dossier

Create an investigation case, add analyst notes, and download a digitally
signed PDF report with a QR verification code.

## SECTION Q — System Limitations & Constraints

Realistic Scope

⚠️ Engineering Limitations

- AI detectors are probabilistic and may be subject to zero-day diffusion model evasion
  attacks.
- Social media platforms strip EXIF metadata upon upload, limiting metadata forensics on
  re-compressed files.
- C2PA Content Credentials are not yet universally embedded by all digital camera
  manufacturers.
- Automated fact-checking provides evidence search rather than absolute, infallible truth
  determination.

## SECTION R — Future Research Extensions

Post-Capstone Ideas

#### Social Media URL Crawler

Automatically ingest and analyze web URLs from Twitter/X, Reddit, and
Telegram posts.

#### Real-Time Livestream Analyzer

Process live RTMP video streams for real-time deepfake detection during
broadcasts.

#### Browser Security Extension

Chrome/Firefox extension giving users instant hover authenticity checks on
web images.

#### Blockchain Evidence Registry

Anchor analysis hashes to a public blockchain ledger for immutable
tamper-proof evidence records.

© 2026 TruthLens Engineering Team — Yashas (Lead), Vishal, Sudheendra G K, Manoj.

Master Technical & Architectural Blueprint — Final Year
B.E. Engineering Capstone

## Embedded Interactive Behavior

The original HTML also defines the following client-side behavior:

1. **Theme Toggle:** switches between dark mode and light mode and updates the icon/text between `🌙 Dark Mode` and `☀️ Light Mode`.
2. **Module Filtering:** filters the 20 module cards by `all`, `CORE`, or `ADVANCED`.
3. **Live Module Search:** searches module card text by keyword, technology, or owner and hides non-matching cards.
4. **ScrollSpy Navigation:** tracks the visible section/module and highlights the corresponding sidebar navigation item.

## External Resources Declared by the HTML

- Google Fonts: `Inter`
- Google Fonts: `Outfit`
- Google Fonts: `JetBrains Mono`
- Font stylesheet URL is declared in the source HTML.

## Extraction Note

This Markdown version preserves the document's substantive text, tables, lists, module specifications, navigation labels, diagram text/data, technology names, API paths, database/table names, ownership information, and interactive behavior. CSS styling rules are intentionally not reproduced because they are presentation code rather than document content/data.
