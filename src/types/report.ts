export type ReportStatus =
  | "draft"
  | "ready"
  | "exported";

export type FindingSeverity =
  | "high"
  | "medium"
  | "low";

export interface ReportFinding {
  id: string;
  title: string;
  description: string;
  severity: FindingSeverity;
}

export interface ReportMetadata {
  generatedAt: string;
  generatedBy: string;
  caseId: string;
  mediaCount: number;
}

export interface InvestigationReport {
  id: string;

  caseId: string;

  title: string;

  status: ReportStatus;

  riskScore: number;

  summary: string;

  metadata: ReportMetadata;

  findings: ReportFinding[];
}