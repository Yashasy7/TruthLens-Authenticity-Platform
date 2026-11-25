import { useMemo, useState } from "react";
import {
  Search,
  Filter,
  Download,
  Calendar,
  ArrowRight,
  X,
  CheckCircle2,
} from "lucide-react";
import type { InvestigationReport, ReportStatus } from "../types/report";
import { reportMock } from "../utils/reportMock";

export function Reports() {
  const [reports, setReports] = useState<InvestigationReport[]>(reportMock);
  const [selectedReport, setSelectedReport] = useState<InvestigationReport | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | ReportStatus>("all");

  const filteredReports = useMemo(() => {
    const query = search.trim().toLowerCase();
    return reports.filter((report) => {
      const matchesSearch =
        !query ||
        report.title.toLowerCase().includes(query) ||
        report.id.toLowerCase().includes(query) ||
        report.caseId.toLowerCase().includes(query);

      const matchesStatus = statusFilter === "all" || report.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [reports, search, statusFilter]);

  const handleExport = (reportId: string) => {
    setReports((current) =>
      current.map((r) => (r.id === reportId ? { ...r, status: "exported" } : r))
    );
    if (selectedReport?.id === reportId) {
      setSelectedReport((prev) => (prev ? { ...prev, status: "exported" } : null));
    }
  };

  return (
    <div className="reports-page" style={{ maxWidth: "1200px", margin: "0 auto", paddingBottom: "40px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "1.2px", color: "var(--primary)", textTransform: "uppercase" }}>
            Documentation
          </span>
          <h2 style={{ fontSize: "26px", fontWeight: 700, margin: "4px 0 6px", color: "var(--text)" }}>
            Investigation Reports
          </h2>
          <p style={{ margin: 0, fontSize: "14px", color: "var(--text-secondary)" }}>
            Review structured evidence summaries, authenticity assessments, and export forensic audit trails.
          </p>
        </div>

        <button
          onClick={() => {
            if (reports.length > 0) setSelectedReport(reports[0]);
          }}
          className="primary-button"
          style={{ padding: "9px 18px", fontSize: "13px" }}
        >
          View Latest Report →
        </button>
      </div>

      {/* Search and Filters */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "16px",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "12px",
          padding: "12px 16px",
          marginBottom: "24px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: "220px" }}>
          <Search size={16} style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search reports by title, ID, or case number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              border: "none",
              outline: "none",
              width: "100%",
              background: "transparent",
              fontSize: "14px",
              color: "var(--text)",
            }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Filter size={15} style={{ color: "var(--text-muted)" }} />
          {(["all", "draft", "ready", "exported"] as const).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              style={{
                padding: "6px 12px",
                borderRadius: "6px",
                border: statusFilter === status ? "1px solid var(--primary)" : "1px solid var(--border)",
                background: statusFilter === status ? "var(--primary-soft)" : "transparent",
                color: statusFilter === status ? "var(--primary)" : "var(--text-secondary)",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                textTransform: "capitalize",
              }}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Reports Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: "20px" }}>
        {filteredReports.map((report) => (
          <div
            key={report.id}
            onClick={() => setSelectedReport(report)}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "14px",
              padding: "20px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
              cursor: "pointer",
              transition: "all 0.15s ease",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
          >
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                <span style={{ fontSize: "11px", fontWeight: 700, padding: "3px 8px", borderRadius: "4px", background: "var(--surface-soft)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                  {report.caseId}
                </span>

                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "3px 8px",
                    borderRadius: "999px",
                    background: report.status === "exported" ? "var(--success-soft)" : "var(--surface-soft)",
                    color: report.status === "exported" ? "var(--success)" : "var(--text-secondary)",
                  }}
                >
                  {report.status.toUpperCase()}
                </span>
              </div>

              <h3 style={{ margin: "0 0 6px", fontSize: "16px", fontWeight: 750, color: "var(--text)" }}>
                {report.title}
              </h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                {report.summary}
              </p>
            </div>

            <div style={{ marginTop: "18px", paddingTop: "14px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-muted)" }}>
                <Calendar size={13} />
                <span>{report.metadata?.generatedAt || "Recent"}</span>
              </div>

              <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--primary)", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                <span>View Details</span>
                <ArrowRight size={13} />
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Selected Report Modal */}
      {selectedReport && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.45)",
            backdropFilter: "blur(4px)",
            display: "grid",
            placeItems: "center",
            padding: "20px",
            zIndex: 100,
          }}
          onClick={() => setSelectedReport(null)}
        >
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "16px",
              padding: "28px",
              maxWidth: "680px",
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
              <div>
                <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--primary)", textTransform: "uppercase" }}>
                  {selectedReport.caseId} &bull; {selectedReport.id}
                </span>
                <h3 style={{ margin: "4px 0", fontSize: "20px", fontWeight: 750, color: "var(--text)" }}>
                  {selectedReport.title}
                </h3>
                <small style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Generated by {selectedReport.metadata?.generatedBy || "Investigator"} on {selectedReport.metadata?.generatedAt || "Recent"}
                </small>
              </div>

              <button
                onClick={() => setSelectedReport(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "4px" }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Verdict Card */}
            <div
              style={{
                padding: "16px",
                borderRadius: "10px",
                background: "var(--surface-soft)",
                border: "1px solid var(--border)",
                marginBottom: "20px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <small style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>AUTHENTICITY ASSESSMENT</small>
                  <p style={{ margin: "4px 0 0", fontSize: "16px", fontWeight: 750, color: "var(--text)" }}>
                    {selectedReport.riskScore >= 70 ? "HIGH RISK (SYNTHETIC DETECTED)" : "LOW RISK (AUTHENTIC)"}
                  </p>
                </div>
                <div style={{ textAlign: "right" }}>
                  <small style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>RISK SCORE</small>
                  <p style={{ margin: "4px 0 0", fontSize: "20px", fontWeight: 800, color: selectedReport.riskScore >= 70 ? "var(--danger)" : "var(--primary)" }}>
                    {selectedReport.riskScore}/100
                  </p>
                </div>
              </div>
            </div>

            {/* Summary */}
            <div style={{ marginBottom: "20px" }}>
              <h4 style={{ margin: "0 0 8px", fontSize: "14px", fontWeight: 700, color: "var(--text)" }}>Executive Summary</h4>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6 }}>{selectedReport.summary}</p>
            </div>

            {/* Evidence Checklist */}
            {selectedReport.findings && selectedReport.findings.length > 0 && (
              <div style={{ marginBottom: "24px" }}>
                <h4 style={{ margin: "0 0 10px", fontSize: "14px", fontWeight: 700, color: "var(--text)" }}>Forensic Findings</h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {selectedReport.findings.map((finding) => (
                    <div key={finding.id} style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 12px", borderRadius: "8px", background: "var(--surface-soft)", border: "1px solid var(--border)" }}>
                      <CheckCircle2 size={16} style={{ color: "var(--success)", flexShrink: 0 }} />
                      <div style={{ flex: 1, fontSize: "13px", color: "var(--text)" }}>
                        <strong>{finding.title}</strong>: {finding.description}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", paddingTop: "16px", borderTop: "1px solid var(--border)" }}>
              <button
                onClick={() => setSelectedReport(null)}
                style={{ padding: "8px 16px", borderRadius: "8px", border: "1px solid var(--border)", background: "var(--surface-soft)", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}
              >
                Close
              </button>

              <button
                onClick={() => handleExport(selectedReport.id)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "8px 18px",
                  borderRadius: "8px",
                  border: "none",
                  background: "var(--primary)",
                  color: "#ffffff",
                  fontSize: "13px",
                  fontWeight: 650,
                  cursor: "pointer",
                }}
              >
                <Download size={14} />
                <span>Export Report (JSON)</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Reports;
