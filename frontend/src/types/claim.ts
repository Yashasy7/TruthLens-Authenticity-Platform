/**
 * TruthLens — Module 11: Text & Claim Analysis
 * TypeScript Definitions for Structured Claims & Named Entities
 */

export type ClaimType =
  | 'FACTUAL_CLAIM'
  | 'OPINION'
  | 'QUESTION'
  | 'NON_CLAIM'
  | 'UNCERTAIN';

export type ClaimEntityType =
  | 'PERSON'
  | 'ORG'
  | 'LOCATION'
  | 'DATE'
  | 'MONEY'
  | 'QUANTITY'
  | 'EVENT'
  | 'GENERAL';

export type ClaimSourceType =
  | 'OCR'
  | 'TRANSCRIPT'
  | 'COMBINED'
  | 'DIRECT_TEXT';

export type AnalysisStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED';

export interface ClaimEntity {
  text: string;
  label: string;
  normalized_label?: string;
  start_char: number;
  end_char: number;
}

export interface Claim {
  id: string;
  mediaId?: string;
  claimText: string;
  normalizedClaimText: string;
  claimType: ClaimType;
  subject?: string | null;
  action?: string | null;
  value?: string | null;
  entityType: ClaimEntityType;
  confidenceScore: number;
  claimHash: string;
  sourceType: ClaimSourceType;
  sentenceIndex: number;
  startChar: number;
  endChar: number;
  entities: ClaimEntity[];
  analysisStatus: AnalysisStatus;
  createdAt: string;
  updatedAt?: string;
}

export interface ClaimEvidence {
  model_name: string;
  sentences_count: number;
  claims_count: number;
  entities_count: number;
  duration_seconds: number;
  details?: Record<string, unknown>;
}

export interface ClaimAnalysisResponse {
  mediaId?: string;
  sourceType: ClaimSourceType;
  analyzedTextLength: number;
  sentencesCount: number;
  claimsCount: number;
  claims: Claim[];
  entities: ClaimEntity[];
  evidence: ClaimEvidence;
  analysisStatus: AnalysisStatus;
  createdAt: string;
}

export interface AdHocTextClaimRequest {
  text: string;
  sourceType?: string;
  language?: string;
}
