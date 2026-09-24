import type { AnalysisResult } from "../types/analysis";

export const analysisMock: AnalysisResult = {
  mediaId: "TL-001",

  overallRisk: 87,

  riskLevel: "high",

  scores: {
    authenticity: 24,
    provenance: 31,
    claimCredibility: 28,
    manipulationRisk: 91,
    aiProbability: 89,
  },

  summary:
    "Multiple analysis signals indicate a high probability of manipulation. Review the evidence breakdown before making a final determination.",
};