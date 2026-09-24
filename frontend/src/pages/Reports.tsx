import { useMemo, useState } from "react";
import type {
  InvestigationReport,
  ReportStatus,
} from "../types/report";
import { reportMock } from "../utils/reportMock";

function Reports() {
  const [reports, setReports] =
    useState<InvestigationReport[]>(reportMock);

  const [selectedReport, setSelectedReport] =
    useState<InvestigationReport | null>(null);

  const [search, setSearch] = useState("");

  const [statusFilter, setStatusFilter] =
    useState<"all" | ReportStatus>("all");

  const filteredReports = useMemo(() => {
    const query = search.trim().toLowerCase();

    return reports.filter((report) => {
      const matchesSearch =
        !query ||
        report.title.toLowerCase().includes(query) ||
        report.id.toLowerCase().includes(query) ||
        report.caseId.toLowerCase().includes(query);

      const matchesStatus =
        statusFilter === "all" ||
        report.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [reports, search, statusFilter]);

  const handleExport = (reportId: string) => {
    setReports((current) =>
      current.map((report) =>
        report.id === reportId
          ? {
              ...report,
              status: "exported",
            }
          : report,
      ),
    );

    setSelectedReport((current) =>
      current?.id === reportId
        ? {
            ...current,
            status: "exported",
          }
        : current,
    );
  };

  const openLatestReport = () => {
    if (reports.length > 0) {
      setSelectedReport(reports[0]);
    }
  };

  return (
    <div className="reports-page">
      {/* =================================
          HEADER
      ================================= */}

      <header className="reports-header">
        <div>
          <span className="eyebrow">
            INVESTIGATION REPORTING
          </span>

          <h2>Reports</h2>

          <p>
            Turn investigation findings into structured,
            reviewable evidence reports.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={openLatestReport}
          disabled={reports.length === 0}
        >
          Open Latest Report →
        </button>
      </header>

      {/* =================================
          STATS
      ================================= */}

      <div className="report-stats">
        <ReportStat
          label="Total Reports"
          value={reports.length}
        />

        <ReportStat
          label="Ready"
          value={countStatus(reports, "ready")}
        />

        <ReportStat
          label="Drafts"
          value={countStatus(reports, "draft")}
        />

        <ReportStat
          label="Exported"
          value={countStatus(reports, "exported")}
        />
      </div>

      {/* =================================
          TOOLBAR
      ================================= */}

      <div className="reports-toolbar">
        <div className="report-search">
          <span>⌕</span>

          <input
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
            placeholder="Search reports..."
          />
        </div>

        <div className="report-filters">
          <FilterButton
            label="All"
            active={statusFilter === "all"}
            onClick={() => setStatusFilter("all")}
          />

          <FilterButton
            label="Ready"
            active={statusFilter === "ready"}
            onClick={() => setStatusFilter("ready")}
          />

          <FilterButton
            label="Draft"
            active={statusFilter === "draft"}
            onClick={() => setStatusFilter("draft")}
          />

          <FilterButton
            label="Exported"
            active={statusFilter === "exported"}
            onClick={() =>
              setStatusFilter("exported")
            }
          />
        </div>
      </div>

      {/* =================================
          MAIN WORKSPACE
      ================================= */}

      <div className="reports-layout">
        {/* REPORT LIBRARY */}

        <section className="reports-list">
          <div className="section-title-row">
            <div>
              <span className="card-label">
                REPORT LIBRARY
              </span>

              <h3>Investigation Reports</h3>
            </div>

            <span className="evidence-count">
              {filteredReports.length} shown
            </span>
          </div>

          {filteredReports.length === 0 ? (
            <EmptyReports />
          ) : (
            filteredReports.map((report) => (
              <ReportCard
                key={report.id}
                report={report}
                selected={
                  selectedReport?.id === report.id
                }
                onClick={() =>
                  setSelectedReport(report)
                }
              />
            ))
          )}
        </section>

        {/* REPORT PREVIEW */}

        <section className="report-preview">
          {selectedReport ? (
            <ReportPreview
              report={selectedReport}
              onExport={handleExport}
            />
          ) : (
            <EmptyReportPreview />
          )}
        </section>
      </div>
    </div>
  );
}

/* =================================
   REPORT STAT
================================= */

function ReportStat({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="report-stat">
      <span>{label}</span>

      <strong>{value}</strong>
    </div>
  );
}

/* =================================
   FILTER
================================= */

function FilterButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={
        active
          ? "report-filter active"
          : "report-filter"
      }
      onClick={onClick}
    >
      {label}
    </button>
  );
}

/* =================================
   REPORT CARD
================================= */

function ReportCard({
  report,
  selected,
  onClick,
}: {
  report: InvestigationReport;
  selected: boolean;
  onClick: () => void;
}) {
  const findingCount = report.findings.length;

  return (
    <button
      className={
        selected
          ? "report-card selected"
          : "report-card"
      }
      onClick={onClick}
    >
      <div className="report-card-top">
        <span className="report-id">
          {report.id}
        </span>

        <ReportStatus status={report.status} />
      </div>

      <h3>{report.title}</h3>

      <div className="report-card-info">
        <span>{report.caseId}</span>

        <span>
          {findingCount} finding
          {findingCount !== 1 ? "s" : ""}
        </span>

        <span>
          Risk {report.riskScore}
        </span>
      </div>

      <div className="report-card-footer">
        <span>{report.generatedAt}</span>

        <span className="report-open">
          Open →
        </span>
      </div>
    </button>
  );
}

/* =================================
   STATUS
================================= */

function ReportStatus({
  status,
}: {
  status: ReportStatus;
}) {
  return (
    <span
      className={`report-status ${status}`}
    >
      <span className="report-status-dot" />
      {status}
    </span>
  );
}

/* =================================
   REPORT PREVIEW
================================= */

function ReportPreview({
  report,
  onExport,
}: {
  report: InvestigationReport;
  onExport: (reportId: string) => void;
}) {
  const highFindings = report.findings.filter(
    (finding) => finding.severity === "high",
  ).length;

  const mediumFindings = report.findings.filter(
    (finding) => finding.severity === "medium",
  ).length;

  const lowFindings = report.findings.filter(
    (finding) => finding.severity === "low",
  ).length;

  return (
    <div className="report-document">
      {/* HEADER */}

      <div className="report-preview-header">
        <div>
          <span className="report-id">
            {report.id}
          </span>

          <h3>{report.title}</h3>
        </div>

        <ReportStatus status={report.status} />
      </div>

      {/* METADATA */}

      <div className="report-metadata">
        <MetadataItem
          label="CASE"
          value={report.caseId}
        />

        <MetadataItem
          label="GENERATED"
          value={report.generatedAt}
        />

        <MetadataItem
          label="FINDINGS"
          value={String(report.findings.length)}
        />
      </div>

      {/* RISK */}

      <div className="report-risk">
        <div className="report-risk-heading">
          <div>
            <span className="card-label">
              INVESTIGATION RISK
            </span>

            <div className="report-risk-score">
              {report.riskScore}
              <span>/100</span>
            </div>
          </div>

          <span
            className={
              report.riskScore >= 70
                ? "risk-indicator high"
                : "risk-indicator medium"
            }
          >
            {report.riskScore >= 70
              ? "HIGH CONCERN"
              : "REVIEW"}
          </span>
        </div>

        <div className="report-risk-bar">
          <div
            style={{
              width: `${report.riskScore}%`,
            }}
          />
        </div>
      </div>

      {/* FINDING SUMMARY */}

      <div className="finding-summary">
        <FindingSummary
          label="High"
          value={highFindings}
          type="high"
        />

        <FindingSummary
          label="Medium"
          value={mediumFindings}
          type="medium"
        />

        <FindingSummary
          label="Low"
          value={lowFindings}
          type="low"
        />
      </div>

      {/* EXECUTIVE SUMMARY */}

      <section className="report-section">
        <span className="card-label">
          EXECUTIVE FINDINGS
        </span>

        <h3>Key evidence identified</h3>

        <p>
          This report summarizes the evidence and
          findings associated with the investigation.
          Investigators should review the supporting
          evidence before making a final determination.
        </p>
      </section>

      {/* FINDINGS */}

      <section className="report-section">
        <div className="report-section-heading">
          <div>
            <span className="card-label">
              FINDINGS
            </span>

            <h3>Evidence observations</h3>
          </div>

          <span className="evidence-count">
            {report.findings.length}
          </span>
        </div>

        <div className="findings-list">
          {report.findings.map((finding) => (
            <FindingCard
              key={finding.id}
              finding={finding}
            />
          ))}
        </div>
      </section>

      {/* ACTIONS */}

      <section className="report-section report-actions-section">
        <div>
          <span className="card-label">
            REPORT ACTIONS
          </span>

          <p>
            Review the findings before exporting the
            investigation report.
          </p>
        </div>

        <div className="report-actions">
          <button
            className="secondary-button"
            onClick={() => window.print()}
          >
            Preview / Print
          </button>

          <button
            className="primary-button"
            disabled={
              report.status === "exported"
            }
            onClick={() =>
              onExport(report.id)
            }
          >
            {report.status === "exported"
              ? "Exported ✓"
              : "Export Report →"}
          </button>
        </div>
      </section>
    </div>
  );
}

/* =================================
   FINDING CARD
================================= */

function FindingCard({
  finding,
}: {
  finding: InvestigationReport["findings"][number];
}) {
  return (
    <div className="finding">
      <div
        className={`finding-severity ${finding.severity}`}
      />

      <div className="finding-content">
        <div className="finding-top">
          <span>{finding.id}</span>

          <span
            className={`finding-label ${finding.severity}`}
          >
            {finding.severity}
          </span>
        </div>

        <strong>{finding.title}</strong>

        <p>{finding.description}</p>
      </div>
    </div>
  );
}

/* =================================
   FINDING SUMMARY
================================= */

function FindingSummary({
  label,
  value,
  type,
}: {
  label: string;
  value: number;
  type: "high" | "medium" | "low";
}) {
  return (
    <div className="finding-summary-item">
      <span
        className={`finding-summary-dot ${type}`}
      />

      <div>
        <strong>{value}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

/* =================================
   METADATA
================================= */

function MetadataItem({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="metadata-item">
      <span>{label}</span>

      <strong>{value}</strong>
    </div>
  );
}

/* =================================
   EMPTY STATES
================================= */

function EmptyReports() {
  return (
    <div className="reports-empty">
      <div className="empty-icon">
        ⌕
      </div>

      <h3>No reports found</h3>

      <p>
        Try changing your search or report filter.
      </p>
    </div>
  );
}

function EmptyReportPreview() {
  return (
    <div className="empty-report">
      <div className="empty-icon">
        ▤
      </div>

      <h3>Select a report</h3>

      <p>
        Choose an investigation report from the
        library to inspect its findings.
      </p>
    </div>
  );
}

/* =================================
   HELPERS
================================= */

function countStatus(
  reports: InvestigationReport[],
  status: ReportStatus,
) {
  return reports.filter(
    (report) => report.status === status,
  ).length;
}

export default Reports;