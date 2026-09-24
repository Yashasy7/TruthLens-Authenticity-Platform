export type RiskLevel = "low" | "medium" | "high";

export interface AnalysisScores {
  authenticity: number;
  provenance: number;
  claimCredibility: number;
  manipulationRisk: number;
  aiProbability: number;
}

export interface AnalysisResult {
  mediaId: string;
  overallRisk: number;
  riskLevel: RiskLevel;
  scores: AnalysisScores;
  summary: string;
}