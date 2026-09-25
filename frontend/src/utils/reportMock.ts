import type { InvestigationReport } from "../types/report";

export const reportMock: InvestigationReport[] = [
  {
    id: "REPORT-001",

    caseId: "CASE-001",

    title:
      "Suspicious Political Video — Investigation Report",

    status: "ready",

    riskScore: 87,

    summary:
      "The investigation identified multiple signals requiring further review, including manipulation indicators, incomplete provenance, and cross-modal inconsistencies.",

    metadata: {
      generatedAt: "Aug 24, 2026",
      generatedBy: "Sudheendra",
      caseId: "CASE-001",
      mediaCount: 3,
    },

    findings: [
      {
        id: "F-001",
        title: "High manipulation signal",
        description:
          "Multiple analysis signals indicate a high probability of media manipulation.",
        severity: "high",
      },

      {
        id: "F-002",
        title: "Provenance chain incomplete",
        description:
          "Available provenance information does not establish a complete chain of origin.",
        severity: "medium",
      },

      {
        id: "F-003",
        title: "Cross-modal inconsistency",
        description:
          "Signals across available modalities show an inconsistency requiring review.",
        severity: "high",
      },
    ],
  },

  {
    id: "REPORT-002",

    caseId: "CASE-002",

    title:
      "Synthetic Interview Clip — Findings",

    status: "draft",

    riskScore: 74,

    summary:
      "The investigation identified audio signals that require additional investigator review.",

    metadata: {
      generatedAt: "Aug 23, 2026",
      generatedBy: "Sudheendra",
      caseId: "CASE-002",
      mediaCount: 2,
    },

    findings: [
      {
        id: "F-004",
        title: "Audio signal requires review",
        description:
          "Audio analysis produced a signal requiring further investigation.",
        severity: "medium",
      },
    ],
  },
];