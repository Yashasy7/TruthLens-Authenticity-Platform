import type { AnalysisEvidence } from "../types/evidence";

export const evidenceMock: AnalysisEvidence = {
  image: [
    {
      id: "IMG-001",
      title: "Image authenticity signal",
      description:
        "Visual analysis indicates possible manipulation within the media.",
      status: "negative",
      confidence: 91,
    },
    {
      id: "IMG-002",
      title: "ELA anomaly",
      description:
        "Error-level analysis identified regions requiring further inspection.",
      status: "warning",
      confidence: 78,
    },
  ],

  video: [
    {
      id: "VID-001",
      title: "Suspicious frame sequence",
      description:
        "Several frames were identified as requiring investigator review.",
      status: "negative",
      confidence: 84,
    },
  ],

  audio: [
    {
      id: "AUD-001",
      title: "Audio authenticity signal",
      description:
        "Audio analysis produced a signal requiring further investigation.",
      status: "warning",
      confidence: 73,
    },
  ],

  claims: [
    {
      id: "CLM-001",
      title: "Claim requires verification",
      description:
        "The extracted claim could not be treated as independently verified.",
      status: "warning",
      confidence: 81,
    },
  ],

  provenance: [
    {
      id: "PRO-001",
      title: "Provenance unavailable",
      description:
        "Available provenance information does not establish a complete chain of origin.",
      status: "warning",
      confidence: 69,
    },
  ],

  crossModal: [
    {
      id: "CXM-001",
      title: "Cross-modal inconsistency",
      description:
        "Signals across modalities show an inconsistency requiring review.",
      status: "negative",
      confidence: 88,
    },
  ],
};