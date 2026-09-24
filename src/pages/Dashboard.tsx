const analysisResult = {
  overallRisk: 87,
  authenticity: 24,
  provenance: 31,
  claimCredibility: 28,
  manipulationRisk: 91,
  aiProbability: 89,
};

import { analysisMock } from "../utils/analysisMock";

function Dashboard() {
  const result = analysisMock;

  const riskLabel =
    result.riskLevel === "high"
      ? "High Risk"
      : result.riskLevel === "medium"
        ? "Medium Risk"
        : "Low Risk";

  return (
    <div className="dashboard">
      {/* ==============================
          HEADER
      ============================== */}

      <header className="dashboard-header">
        <div>
          <span className="eyebrow">
            ANALYSIS OVERVIEW
          </span>

          <h2>Investigation Dashboard</h2>

          <p>
            Review the evidence and understand the signals
            behind this assessment.
          </p>
        </div>

        <div className="dashboard-header-actions">
          <div className="media-id">
            <span>MEDIA</span>
            <strong>{result.mediaId}</strong>
          </div>

          <button className="primary-button">
            View Full Analysis →
          </button>
        </div>
      </header>

      {/* ==============================
          RISK HERO
      ============================== */}

      <section className="risk-hero">
        <div className="risk-hero-main">
          <div className="risk-heading">
            <span className="card-label">
              OVERALL RISK
            </span>

            <span className={`risk-pill ${result.riskLevel}`}>
              <span className="risk-pill-dot" />
              {riskLabel}
            </span>
          </div>

          <div className="risk-number">
            {result.overallRisk}
            <span>/100</span>
          </div>

          <div className="risk-meter">
            <div
              style={{
                width: `${result.overallRisk}%`,
              }}
            />
          </div>

          <p className="risk-caption">
            Overall assessment derived from the available
            TruthLens analysis signals.
          </p>
        </div>

        <div className="risk-hero-explanation">
          <span className="card-label">
            ANALYSIS SUMMARY
          </span>

          <h3>
            Why is this media considered high risk?
          </h3>

          <p>{result.summary}</p>

          <button className="hero-link">
            Explore supporting evidence
            <span>→</span>
          </button>
        </div>
      </section>

      {/* ==============================
          SCORE BREAKDOWN
      ============================== */}

      <section className="dashboard-section">
        <div className="section-heading">
          <div>
            <span className="card-label">
              SIGNAL BREAKDOWN
            </span>

            <h3>Assessment signals</h3>
          </div>

          <span className="section-hint">
            4 core signals
          </span>
        </div>

        <div className="score-grid">
          <ScoreCard
            title="Authenticity"
            value={result.scores.authenticity}
            description="Media authenticity"
          />

          <ScoreCard
            title="Provenance"
            value={result.scores.provenance}
            description="Origin confidence"
          />

          <ScoreCard
            title="Claim Credibility"
            value={result.scores.claimCredibility}
            description="Claim reliability"
          />

          <ScoreCard
            title="Manipulation Risk"
            value={result.scores.manipulationRisk}
            description="Manipulation likelihood"
          />
        </div>
      </section>

      {/* ==============================
          SECONDARY SIGNALS
      ============================== */}

      <section className="dashboard-grid">
        <div className="panel signal-panel">
          <div className="panel-heading">
            <div>
              <span className="card-label">
                AI SIGNAL
              </span>

              <h3>AI Probability</h3>
            </div>

            <span className="panel-value">
              {result.scores.aiProbability}%
            </span>
          </div>

          <div className="signal-bar">
            <div
              className="signal-fill"
              style={{
                width: `${result.scores.aiProbability}%`,
              }}
            />
          </div>

          <div className="signal-meta">
            <span>Low</span>
            <span>Medium</span>
            <span>High</span>
          </div>

          <p className="panel-description">
            Estimated probability based on the available
            analysis signals.
          </p>
        </div>

        <div className="panel media-panel">
          <div className="panel-heading">
            <div>
              <span className="card-label">
                EVIDENCE
              </span>

              <h3>Media Preview</h3>
            </div>

            <span className="status-badge">
              ANALYZED
            </span>
          </div>

          <div className="media-preview">
            <div className="media-preview-icon">
              ◈
            </div>

            <div>
              <strong>
                {result.mediaId}
              </strong>

              <span>
                Analysis completed
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ==============================
          EXPLAINABILITY
      ============================== */}

      <section className="explainability-panel">
        <div className="explainability-copy">
          <span className="card-label">
            EXPLAINABILITY
          </span>

          <h3>
            The score is not the conclusion.
          </h3>

          <p>
            TruthLens should help investigators understand
            the signals behind an assessment and inspect
            the underlying evidence before reaching a
            conclusion.
          </p>
        </div>

        <div className="explainability-flow">
          <ExplanationStep
            number="01"
            title="Signal detected"
            text="Analysis identifies a risk signal."
          />

          <div className="flow-line" />

          <ExplanationStep
            number="02"
            title="Evidence examined"
            text="Supporting evidence is surfaced."
          />

          <div className="flow-line" />

          <ExplanationStep
            number="03"
            title="Investigator reviews"
            text="Human judgment remains central."
          />
        </div>
      </section>
    </div>
  );
}

type ScoreCardProps = {
  title: string;
  value: number;
  description: string;
};

function ScoreCard({
  title,
  value,
  description,
}: ScoreCardProps) {
  const level =
    value >= 70
      ? "high"
      : value >= 40
        ? "medium"
        : "low";

  const label =
    level === "high"
      ? "High concern"
      : level === "medium"
        ? "Moderate concern"
        : "Requires review";

  return (
    <div className="score-card">
      <div className="score-card-header">
        <div>
          <span className="score-title">
            {title}
          </span>

          <small>{description}</small>
        </div>

        <span
          className={`score-dot ${level}`}
        />
      </div>

      <div className="score-value">
        {value}
        <span>/100</span>
      </div>

      <div className="mini-bar">
        <div
          className={`mini-fill ${level}`}
          style={{
            width: `${value}%`,
          }}
        />
      </div>

      <div className="score-footer">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
    </div>
  );
}

function ExplanationStep({
  number,
  title,
  text,
}: {
  number: string;
  title: string;
  text: string;
}) {
  return (
    <div className="explanation-step">
      <div className="explanation-number">
        {number}
      </div>

      <div>
        <strong>{title}</strong>
        <span>{text}</span>
      </div>
    </div>
  );
}

export default Dashboard;