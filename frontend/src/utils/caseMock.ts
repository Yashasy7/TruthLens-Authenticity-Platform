import type { InvestigationCase } from "../types/case";

export const caseMock: InvestigationCase[] = [
  {
    id: "CASE-001",
    title: "Suspicious political video",
    description:
      "Investigation into potential manipulation and provenance inconsistencies.",
    status: "investigating",
    riskScore: 87,
    mediaCount: 3,
    assignedTo: "Sudheendra",
    updatedAt: "Today, 10:42 AM",
  },
  {
    id: "CASE-002",
    title: "Synthetic interview clip",
    description:
      "Video and audio signals require additional investigator review.",
    status: "open",
    riskScore: 74,
    mediaCount: 2,
    assignedTo: "Yashas",
    updatedAt: "Yesterday",
  },
  {
    id: "CASE-003",
    title: "Image provenance review",
    description:
      "Metadata and provenance information need verification.",
    status: "reviewed",
    riskScore: 58,
    mediaCount: 1,
    assignedTo: "Sudheendra",
    updatedAt: "Aug 23",
  },
];