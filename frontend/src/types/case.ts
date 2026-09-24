export type CaseStatus =
  | "open"
  | "investigating"
  | "reviewed"
  | "resolved"
  | "archived";

export interface InvestigationCase {
  id: string;
  title: string;
  description: string;
  status: CaseStatus;
  riskScore: number;
  mediaCount: number;
  assignedTo: string;
  updatedAt: string;
}