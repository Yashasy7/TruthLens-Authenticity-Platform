import { useState } from "react";
import { evidenceMock } from "../utils/evidenceMock";

type AnalysisTab =
  | "overview"
  | "image"
  | "video"
  | "audio"
  | "claims"
  | "provenance"
  | "crossModal";

const tabs: { id: AnalysisTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "image", label: "Image" },
  { id: "video", label: "Video" },
  { id: "audio", label: "Audio" },
  { id: "claims", label: "Claims" },
  { id: "provenance", label: "Provenance" },
  { id: "crossModal", label: "Cross-Modal" },
];

function Analysis() {
  const [activeTab, setActiveTab] =
    useState<AnalysisTab>("overview");

  return (
    <div className="analysis-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">FORENSIC ANALYSIS</span>

          <h2>Analysis Workspace</h2>

          <p>
            Inspect the signals and evidence behind the
            TruthLens assessment.
          </p>
        </div>

        <div className="analysis-id">
          <span>MEDIA ID</span>
          <strong>TL-001</strong>
        </div>
      </div>

      <div className="analysis-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={
              activeTab === tab.id
                ? "analysis-tab active"
                : "analysis-tab"
            }
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && <Overview />}

      {activeTab !== "overview" && (
        <EvidenceSection type={activeTab} />
      )}
    </div>
  );
}

function Overview() {
  const allEvidence = Object.values(evidenceMock).flat();

  const highRiskCount = allEvidence.filter(
    (item) => item.status === "negative",
  ).length;

  return (
    <div>
      <div className="analysis-overview-grid">
        <div className="analysis-summary-card">
          <span className="card-label">
            ANALYSIS STATUS
          </span>

          <div className="analysis-status">
            <span className="status-dot" />
            Completed
          </div>

          <p>
            TruthLens has completed the available analysis
            pipeline for this media item.
          </p>
        </div>

        <div className="analysis-summary-card">
          <span className="card-label">
            EVIDENCE SIGNALS
          </span>

          <strong className="analysis-number">
            {allEvidence.length}
          </strong>

          <p>
            Evidence signals available for investigator review.
          </p>
        </div>

        <div className="analysis-summary-card">
          <span className="card-label">
            HIGH CONCERN
          </span>

          <strong className="analysis-number danger-text">
            {highRiskCount}
          </strong>

          <p>
            Signals currently requiring closer attention.
          </p>
        </div>
      </div>

      <section className="analysis-section">
        <div className="section-title-row">
          <div>
            <span className="card-label">
              EVIDENCE MAP
            </span>

            <h3>Where should I investigate?</h3>
          </div>
        </div>

        <div className="evidence-map">
          <EvidenceMapItem
            label="Image"
            count={evidenceMock.image.length}
            color="blue"
          />

          <EvidenceMapItem
            label="Video"
            count={evidenceMock.video.length}
            color="purple"
          />

          <EvidenceMapItem
            label="Audio"
            count={evidenceMock.audio.length}
            color="orange"
          />

          <EvidenceMapItem
            label="Claims"
            count={evidenceMock.claims.length}
            color="green"
          />

          <EvidenceMapItem
            label="Provenance"
            count={evidenceMock.provenance.length}
            color="yellow"
          />

          <EvidenceMapItem
            label="Cross-Modal"
            count={evidenceMock.crossModal.length}
            color="pink"
          />
        </div>
      </section>

      <section className="analysis-section">
        <div className="section-title-row">
          <div>
            <span className="card-label">
              INVESTIGATOR GUIDANCE
            </span>

            <h3>Start with the strongest signals</h3>
          </div>
        </div>

        <Guidance
          number="01"
          title="Review image evidence"
          description="Inspect the visual authenticity signals and identified anomalies before moving to other evidence."
        />

        <Guidance
          number="02"
          title="Compare supporting evidence"
          description="Check claims, provenance and cross-modal signals against the primary evidence."
        />

        <Guidance
          number="03"
          title="Create an investigation case"
          description="When the evidence requires continued review, move the investigation into case management."
        />
      </section>
    </div>
  );
}

function Guidance({
  number,
  title,
  description,
}: {
  number: string;
  title: string;
  description: string;
}) {
  return (
    <div className="guidance-card">
      <div className="guidance-number">{number}</div>

      <div>
        <strong>{title}</strong>

        <p>{description}</p>
      </div>
    </div>
  );
}

function EvidenceSection({
  type,
}: {
  type: AnalysisTab;
}) {
  const evidence =
    evidenceMock[type as keyof typeof evidenceMock] ?? [];

  const title =
    tabs.find((tab) => tab.id === type)?.label ?? "Evidence";

  return (
    <section className="analysis-section">
      <div className="section-title-row">
        <div>
          <span className="card-label">
            EVIDENCE ANALYSIS
          </span>

          <h3>{title} Evidence</h3>
        </div>

        <span className="evidence-count">
          {evidence.length} signal
          {evidence.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="evidence-list">
        {evidence.map((item) => (
          <EvidenceCard
            key={item.id}
            item={item}
          />
        ))}
      </div>
    </section>
  );
}

function EvidenceCard({
  item,
}: {
  item: {
    id: string;
    title: string;
    description: string;
    status: "positive" | "warning" | "negative";
    confidence: number;
  };
}) {
  return (
    <div className="evidence-card">
      <div className="evidence-card-header">
        <div>
          <span className="evidence-id">
            {item.id}
          </span>

          <h3>{item.title}</h3>
        </div>

        <span
          className={`evidence-status ${item.status}`}
        >
          {item.status}
        </span>
      </div>

      <p>{item.description}</p>

      <div className="confidence-row">
        <span>Confidence</span>

        <strong>{item.confidence}%</strong>
      </div>

      <div className="confidence-bar">
        <div
          style={{
            width: `${item.confidence}%`,
          }}
        />
      </div>
    </div>
  );
}

function EvidenceMapItem({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className={`map-item ${color}`}>
      <span className="map-dot" />

      <div>
        <strong>{label}</strong>

        <small>
          {count} signal{count !== 1 ? "s" : ""}
        </small>
      </div>
    </div>
  );
}

export default Analysis;