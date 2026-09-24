export type EvidenceStatus = "positive" | "warning" | "negative";

export interface EvidenceItem {
  id: string;
  title: string;
  description: string;
  status: EvidenceStatus;
  confidence: number;
}

export interface AnalysisEvidence {
  image: EvidenceItem[];
  video: EvidenceItem[];
  audio: EvidenceItem[];
  claims: EvidenceItem[];
  provenance: EvidenceItem[];
  crossModal: EvidenceItem[];
}