import { useState } from "react";
import type {
  CaseStatus,
  InvestigationCase,
} from "../types/case";
import { caseMock } from "../utils/caseMock";

const statuses: CaseStatus[] = [
  "open",
  "investigating",
  "reviewed",
  "resolved",
  "archived",
];

function Cases() {
  const [cases, setCases] =
    useState<InvestigationCase[]>(caseMock);

  const [selectedCase, setSelectedCase] =
    useState<InvestigationCase | null>(null);

  const [showCreate, setShowCreate] =
    useState(false);

  const createCase = () => {
    const newCase: InvestigationCase = {
      id: `CASE-${String(cases.length + 1).padStart(3, "0")}`,
      title: "New Investigation",
      description:
        "New investigation created from the TruthLens workspace.",
      status: "open",
      riskScore: 0,
      mediaCount: 0,
      assignedTo: "Sudheendra",
      updatedAt: "Just now",
    };

    setCases([newCase, ...cases]);

    setShowCreate(false);
    setSelectedCase(newCase);
  };

  const updateStatus = (
    caseId: string,
    status: CaseStatus,
  ) => {
    setCases((currentCases) =>
      currentCases.map((item) =>
        item.id === caseId
          ? {
              ...item,
              status,
              updatedAt: "Just now",
            }
          : item,
      ),
    );

    setSelectedCase((current) =>
      current
        ? {
            ...current,
            status,
            updatedAt: "Just now",
          }
        : null,
    );
  };

  return (
    <div className="cases-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            INVESTIGATION MANAGEMENT
          </span>

          <h2>Cases</h2>

          <p>
            Organize evidence, investigations,
            assignments and review status.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() => setShowCreate(true)}
        >
          + New Case
        </button>
      </div>

      <div className="case-stats">
        <CaseStat
          label="Total Cases"
          value={cases.length}
        />

        <CaseStat
          label="Investigating"
          value={
            cases.filter(
              (item) => item.status === "investigating",
            ).length
          }
        />

        <CaseStat
          label="High Risk"
          value={
            cases.filter(
              (item) => item.riskScore >= 70,
            ).length
          }
        />

        <CaseStat
          label="Resolved"
          value={
            cases.filter(
              (item) => item.status === "resolved",
            ).length
          }
        />
      </div>

      <div className="cases-layout">
        <section className="cases-list">
          <div className="section-title-row">
            <div>
              <span className="card-label">
                INVESTIGATIONS
              </span>

              <h3>Case Board</h3>
            </div>

            <span className="evidence-count">
              {cases.length} cases
            </span>
          </div>

          {cases.map((item) => (
            <CaseCard
              key={item.id}
              item={item}
              selected={
                selectedCase?.id === item.id
              }
              onClick={() =>
                setSelectedCase(item)
              }
            />
          ))}
        </section>

        <section className="case-details">
          {selectedCase ? (
            <CaseDetails
              caseItem={selectedCase}
              onStatusChange={updateStatus}
            />
          ) : (
            <div className="empty-case">
              <div className="empty-icon">□</div>

              <h3>Select an investigation</h3>

              <p>
                Choose a case from the board to inspect
                its details.
              </p>
            </div>
          )}
        </section>
      </div>

      {showCreate && (
        <div className="modal-backdrop">
          <div className="create-case-modal">
            <span className="eyebrow">
              NEW INVESTIGATION
            </span>

            <h3>Create a case?</h3>

            <p>
              This creates a new investigation workspace
              ready for evidence and review.
            </p>

            <div className="modal-actions">
              <button
                className="secondary-button"
                onClick={() => setShowCreate(false)}
              >
                Cancel
              </button>

              <button
                className="primary-button"
                onClick={createCase}
              >
                Create Case
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CaseStat({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="case-stat">
      <span>{label}</span>

      <strong>{value}</strong>
    </div>
  );
}

function CaseCard({
  item,
  selected,
  onClick,
}: {
  item: InvestigationCase;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={
        selected
          ? "case-card selected"
          : "case-card"
      }
      onClick={onClick}
    >
      <div className="case-card-top">
        <span className="case-id">
          {item.id}
        </span>

        <span
          className={`case-status ${item.status}`}
        >
          {item.status}
        </span>
      </div>

      <h3>{item.title}</h3>

      <p>{item.description}</p>

      <div className="case-card-footer">
        <span>
          {item.mediaCount} media
        </span>

        <span>
          Risk {item.riskScore}
        </span>

        <span>
          {item.updatedAt}
        </span>
      </div>
    </button>
  );
}

function CaseDetails({
  caseItem,
  onStatusChange,
}: {
  caseItem: InvestigationCase;
  onStatusChange: (
    caseId: string,
    status: CaseStatus,
  ) => void;
}) {
  return (
    <div>
      <div className="case-detail-header">
        <div>
          <span className="case-id">
            {caseItem.id}
          </span>

          <h3>{caseItem.title}</h3>
        </div>

        <span
          className={`case-status ${caseItem.status}`}
        >
          {caseItem.status}
        </span>
      </div>

      <p className="case-description">
        {caseItem.description}
      </p>

      <div className="case-risk">
        <div>
          <span className="card-label">
            RISK SCORE
          </span>

          <strong>{caseItem.riskScore}</strong>
          <span>/100</span>
        </div>

        <div
          className="case-risk-bar"
        >
          <div
            style={{
              width: `${caseItem.riskScore}%`,
            }}
          />
        </div>
      </div>

      <div className="case-meta-grid">
        <div>
          <span>ASSIGNED TO</span>
          <strong>
            {caseItem.assignedTo}
          </strong>
        </div>

        <div>
          <span>MEDIA</span>
          <strong>
            {caseItem.mediaCount}
          </strong>
        </div>

        <div>
          <span>UPDATED</span>
          <strong>
            {caseItem.updatedAt}
          </strong>
        </div>
      </div>

      <div className="case-section">
        <span className="card-label">
          INVESTIGATION LIFECYCLE
        </span>

        <div className="case-lifecycle">
          {statuses.map((status, index) => {
            const currentIndex =
              statuses.indexOf(caseItem.status);

            return (
              <div
                key={status}
                className={
                  index <= currentIndex
                    ? "lifecycle-step complete"
                    : "lifecycle-step"
                }
              >
                <span>{index + 1}</span>
                <small>{status}</small>
              </div>
            );
          })}
        </div>
      </div>

      <div className="case-section">
        <span className="card-label">
          CASE ACTION
        </span>

        <div className="status-actions">
          {statuses.map((status) => (
            <button
              key={status}
              className={
                caseItem.status === status
                  ? "status-action active"
                  : "status-action"
              }
              onClick={() =>
                onStatusChange(
                  caseItem.id,
                  status,
                )
              }
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      <div className="case-section">
        <span className="card-label">
          QUICK LINKS
        </span>

        <div className="quick-links">
          <button>View Analysis →</button>
          <button>View Evidence →</button>
          <button>Open Report →</button>
        </div>
      </div>
    </div>
  );
}

export default Cases;