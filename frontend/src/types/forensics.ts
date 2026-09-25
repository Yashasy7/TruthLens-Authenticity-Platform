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
  tag?: string;
  ruleId?: string;
  category?: string;
  anomalyType?: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL' | string;
  title?: string;
  description: string;
  evidence?: string;
  confidence?: number;
  scoreImpact?: number;
}

export interface MetadataResponse {
  id: string;
  mediaId: string;
  cameraMake?: string | null;
  cameraModel?: string | null;
  lensModel?: string | null;
  software?: string | null;
  softwareTag?: string | null;
  dateTimeOriginal?: string | null;
  capturedAt?: string | null;
  modifiedAt?: string | null;
  gpsLatitude?: number | null;
  gpsLongitude?: number | null;
  gpsAltitude?: number | null;
  width?: number | null;
  height?: number | null;
  durationSeconds?: number | null;
  bitrate?: number | null;
  frameRate?: number | null;
  videoCodec?: string | null;
  audioCodec?: string | null;
  audioSampleRate?: number | null;
  audioChannels?: number | null;
  containerFormat?: string | null;
  hasAnomalies?: boolean;
  anomaliesCount?: number;
  anomalyCount?: number;
  forensicScore: number;
  riskLevel?: string | null;
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

export interface VideoFrameScoreDto {
  frame_index: number;
  timestamp_seconds: number;
  deepfake_score: number;
  temporal_inconsistency?: number;
  faces_detected?: number;
  is_suspicious?: boolean;
}

export interface VideoEvidenceDto {
  frame_anomaly_scores?: number[];
  frame_scores?: VideoFrameScoreDto[];
  face_detection_confidence?: number;
  face_count?: number;
  total_frames_sampled?: number;
  duration_seconds?: number;
  optical_flow_inconsistency?: number;
  suspicious_intervals?: Array<{ start: number; end: number }>;
  suspicious_timestamps?: SuspiciousTimestampDto[];
  details?: Record<string, unknown>;
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
  spectral_centroid_mean?: number;
  spectral_bandwidth_mean?: number;
  spectral_rolloff_mean?: number;
  spectral_flatness?: number;
  zero_crossing_rate?: number;
  zero_crossing_rate_mean?: number;
  phase_discontinuity_score?: number;
  f0_mean_hz?: number;
  f0_std_hz?: number;
  details?: Record<string, unknown>;
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
  start_seconds?: number;
  end_seconds?: number;
  drift_ms?: number;
  start_time?: number;
  end_time?: number;
  offset_ms?: number;
  confidence: number;
  reason?: string;
}

export interface AvSyncEvidenceDto {
  envelope_correlation?: number;
  syncnet_distance?: number;
  face_track_coverage_pct?: number;
  details?: Record<string, unknown>;
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
  polygon?: Array<[number, number] | { x: number; y: number }> | null;
  normalized_bbox?: number[] | null;
}

export interface OcrTextRegionDto {
  text: string;
  confidence: number;
  boundingBox?: OcrBoundingBoxDto;
  bounding_box?: OcrBoundingBoxDto;
  language?: string;
  frame_index?: number | null;
  timestamp_seconds?: number | null;
  polygon?: Array<{ x: number; y: number }> | null;
}

export interface OcrEvidenceDto {
  preprocessor?: string;
  ocr_engine?: string;
  engine_used?: string;
  language_detected?: string;
  detected_languages?: string[];
  image_width?: number;
  image_height?: number;
  line_count?: number;
  total_regions?: number;
  details?: Record<string, unknown>;
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
  start?: number;
  end?: number;
  start_seconds?: number;
  end_seconds?: number;
  probability?: number;
  confidence?: number;
}

export interface TranscriptSegmentDto {
  id?: number;
  segment_id?: number;
  start?: number;
  end?: number;
  start_seconds?: number;
  end_seconds?: number;
  text: string;
  confidence: number;
  tokens?: number[];
  temperature?: number;
  words?: TranscriptWordDto[] | null;
}

export interface TranscriptEvidenceDto {
  duration_seconds?: number;
  silence_ratio?: number;
  engine?: string;
  model_name?: string;
  detected_language?: string;
  details?: Record<string, unknown>;
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
