/**
 * Forensics & AI/ML analysis types matching Spring Boot backend DTOs (Modules 03–10).
 */

export type AnalysisStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

// -----------------------------------------------------------------------------
// Module 03 — Fingerprint & Duplicate Matching
// -----------------------------------------------------------------------------

export interface FingerprintResponse {
  mediaId: string;
  sha256Hash: string;
  perceptualHash?: string | null;
  acousticFingerprint?: string | null;
  videoFingerprint?: string | null;
  createdAt: string;
}

export interface DuplicateMatchResponse {
  matchedMediaId: string;
  matchType: 'EXACT' | 'NEAR_DUPLICATE' | 'ACOUSTIC' | 'VISUAL';
  similarityScore: number;
  originalFilename?: string | null;
  createdAt: string;
}

// -----------------------------------------------------------------------------
// Module 04 — Metadata & Digital Forensics
// -----------------------------------------------------------------------------

export interface MetadataAnomalyDto {
  tag: string;
  anomalyType: string;
  description: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
}

export interface MetadataResponse {
  id: string;
  mediaId: string;
  cameraMake?: string | null;
  cameraModel?: string | null;
  lensModel?: string | null;
  software?: string | null;
  dateTimeOriginal?: string | null;
  gpsLatitude?: number | null;
  gpsLongitude?: number | null;
  anomaliesCount: number;
  forensicScore: number;
  anomalies: MetadataAnomalyDto[];
  extractionEngine: string;
  createdAt: string;
  updatedAt?: string | null;
}

// -----------------------------------------------------------------------------
// Module 05 — Image Authenticity Analysis
// -----------------------------------------------------------------------------

export interface ImageEvidenceDto {
  noise_variance?: number;
  noise_inconsistency_score?: number;
  fft_anomaly_score?: number;
  copy_move_detected?: boolean;
  splicing_detected?: boolean;
  image_width?: number;
  image_height?: number;
  details?: Record<string, unknown>;
}

export interface ImageAnalysisResponse {
  id: string;
  mediaId: string;
  aiProb: number;
  manipulationProb: number;
  authenticityAssessment: string;
  elaHeatmapUrl?: string | null;
  gradcamHeatmapUrl?: string | null;
  noiseVariance?: number | null;
  fftAnomalyScore?: number | null;
  copyMoveDetected: boolean;
  splicingDetected: boolean;
  analysisStatus: AnalysisStatus;
  modelVersion?: string | null;
  evidence?: ImageEvidenceDto | null;
  createdAt: string;
  updatedAt?: string | null;
}

// -----------------------------------------------------------------------------
// Module 06 — Video Deepfake Detection
// -----------------------------------------------------------------------------

export interface SuspiciousTimestampDto {
  frame_index: number;
  timestamp_seconds: number;
  anomaly_score: number;
  reason?: string;
}

export interface VideoEvidenceDto {
  frame_anomaly_scores?: number[];
  face_detection_confidence?: number;
  optical_flow_inconsistency?: number;
  suspicious_intervals?: Array<{ start: number; end: number }>;
}

export interface VideoAnalysisResponse {
  id: string;
  media_id: string;
  deepfake_prob: number;
  face_count: number;
  total_frames_sampled: number;
  authenticity_assessment: string;
  analysis_status: AnalysisStatus;
  model_version?: string | null;
  suspicious_timestamps: SuspiciousTimestampDto[];
  evidence?: VideoEvidenceDto | null;
  created_at: string;
  updated_at?: string | null;
}

// -----------------------------------------------------------------------------
// Module 07 — Audio Authenticity & Voice Forensics
// -----------------------------------------------------------------------------

export interface AudioSpliceMarkerDto {
  timestamp_seconds: number;
  confidence: number;
  discontinuity_type: string;
}

export interface AudioEvidenceDto {
  spectral_centroid?: number;
  spectral_flatness?: number;
  zero_crossing_rate?: number;
  f0_mean_hz?: number;
  f0_std_hz?: number;
}

export interface AudioAnalysisResponse {
  id: string;
  media_id: string;
  synthetic_voice_prob: number;
  spectrogram_url?: string | null;
  spectrogram_base64?: string | null;
  pitch_variance: number;
  phase_discontinuity: number;
  authenticity_assessment: string;
  analysis_status: AnalysisStatus;
  model_name?: string | null;
  model_version?: string | null;
  splice_markers: AudioSpliceMarkerDto[];
  evidence?: AudioEvidenceDto | null;
  created_at: string;
  updated_at?: string | null;
}

// -----------------------------------------------------------------------------
// Module 08 — Audio-Video Synchronization
// -----------------------------------------------------------------------------

export interface MismatchSegmentDto {
  start_seconds: number;
  end_seconds: number;
  drift_ms: number;
  confidence: number;
}

export interface AvSyncEvidenceDto {
  envelope_correlation?: number;
  syncnet_distance?: number;
  face_track_coverage_pct?: number;
}

export interface AvSyncAnalysisResponse {
  id: string;
  mediaId: string;
  syncScore: number;
  lipOffsetMs: number;
  confidence: number;
  assessment: string;
  analysisStatus: AnalysisStatus;
  modelName?: string | null;
  modelVersion?: string | null;
  mismatchSegments: MismatchSegmentDto[];
  evidence?: AvSyncEvidenceDto | null;
  createdAt: string;
  updatedAt?: string | null;
}

// -----------------------------------------------------------------------------
// Module 09 — Optical Character Recognition (OCR)
// -----------------------------------------------------------------------------

export interface OcrBoundingBoxDto {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface OcrTextRegionDto {
  text: string;
  confidence: number;
  boundingBox: OcrBoundingBoxDto;
  polygon?: Array<{ x: number; y: number }> | null;
}

export interface OcrEvidenceDto {
  preprocessor?: string;
  ocr_engine?: string;
  language_detected?: string;
  line_count?: number;
}

export interface OcrResultResponse {
  id: string;
  mediaId: string;
  extractedText: string;
  language: string;
  confidenceScore: number;
  regionsCount: number;
  regions: OcrTextRegionDto[];
  evidence?: OcrEvidenceDto | null;
  analysisStatus: AnalysisStatus;
  createdAt: string;
  updatedAt?: string | null;
}

// -----------------------------------------------------------------------------
// Module 10 — Speech-to-Text & Transcripts
// -----------------------------------------------------------------------------

export interface TranscriptWordDto {
  word: string;
  start_seconds: number;
  end_seconds: number;
  confidence: number;
}

export interface TranscriptSegmentDto {
  segment_id: number;
  start_seconds: number;
  end_seconds: number;
  text: string;
  confidence: number;
  words?: TranscriptWordDto[] | null;
}

export interface TranscriptEvidenceDto {
  duration_seconds?: number;
  silence_ratio?: number;
  engine?: string;
}

export interface TranscriptResponse {
  id: string;
  mediaId: string;
  fullText: string;
  language: string;
  confidenceScore: number;
  durationSeconds: number;
  segmentsCount: number;
  wordsCount: number;
  segments: TranscriptSegmentDto[];
  evidence?: TranscriptEvidenceDto | null;
  analysisStatus: AnalysisStatus;
  createdAt: string;
  updatedAt?: string | null;
}
