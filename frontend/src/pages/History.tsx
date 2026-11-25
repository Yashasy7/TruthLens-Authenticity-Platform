import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { mediaApi } from "../services/api";
import type { MediaResponse } from "../types/media";
import {
  History as HistoryIcon,
  Search,
  Music,
  ArrowRight,
  Filter,
  RefreshCw,
  Clock,
  FileQuestion,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";

export function History() {
  const navigate = useNavigate();
  const [mediaList, setMediaList] = useState<MediaResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");

  const loadHistory = () => {
    setIsLoading(true);
    mediaApi
      .getMyMedia()
      .then((items) => {
        setMediaList(items || []);
      })
      .catch(() => {
        setMediaList([]);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const filteredItems = useMemo(() => {
    return mediaList.filter((item) => {
      const matchesSearch =
        !search.trim() ||
        item.originalFilename.toLowerCase().includes(search.toLowerCase()) ||
        item.id.toLowerCase().includes(search.toLowerCase());

      const matchesType =
        typeFilter === "ALL" ||
        item.mediaType?.toUpperCase() === typeFilter.toUpperCase();

      return matchesSearch && matchesType;
    });
  }, [mediaList, search, typeFilter]);

  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes <= 0) return "—";
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "—";
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="history-page" style={{ maxWidth: "1240px", margin: "0 auto", paddingBottom: "50px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "1.2px", color: "var(--primary)", textTransform: "uppercase" }}>
            Forensic Audit Log
          </span>
          <h1 style={{ fontSize: "26px", fontWeight: 800, margin: "4px 0 6px", color: "var(--text)", letterSpacing: "-0.5px" }}>
            Analysis History & Evidence Archive
          </h1>
          <p style={{ margin: 0, fontSize: "14px", color: "var(--text-secondary)" }}>
            Inspect past authenticity evaluations, cryptographic hashes, and forensic telemetry across all media.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={() => navigate("/analysis")}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "7px",
              padding: "9px 16px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)",
              color: "#ffffff",
              border: "none",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: "0 2px 8px rgba(79, 70, 229, 0.25)",
            }}
          >
            <UploadCloud size={15} />
            <span>Analyze New Image</span>
          </button>

          <button
            onClick={loadHistory}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "9px 14px",
              borderRadius: "8px",
              border: "1px solid var(--border)",
              background: "var(--surface)",
              color: "var(--text-secondary)",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "16px",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "12px",
          padding: "12px 18px",
          marginBottom: "20px",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.03)",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: "1", minWidth: "260px" }}>
          <Search size={16} style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search by filename or UUID..."
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
          {["ALL", "IMAGE", "AUDIO"].map((type) => (
            <button
              key={type}
              onClick={() => setTypeFilter(type)}
              style={{
                padding: "6px 12px",
                borderRadius: "6px",
                border: typeFilter === type ? "1px solid var(--primary)" : "1px solid var(--border)",
                background: typeFilter === type ? "var(--primary-soft)" : "transparent",
                color: typeFilter === type ? "var(--primary)" : "var(--text-secondary)",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {type === "ALL" ? "All Media" : type === "IMAGE" ? "Images" : "Audio"}
            </button>
          ))}
        </div>
      </div>

      {/* Table Content */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "14px",
          overflow: "hidden",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
        }}
      >
        {isLoading ? (
          <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--text-secondary)" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                border: "2px solid var(--border)",
                borderTopColor: "var(--primary)",
                borderRadius: "50%",
                margin: "0 auto 12px",
                animation: "spin 0.8s linear infinite",
              }}
            />
            <p style={{ margin: 0, fontSize: "14px" }}>Loading media audit log...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div style={{ padding: "60px 20px", textAlign: "center" }}>
            <HistoryIcon size={40} style={{ color: "var(--text-muted)", margin: "0 auto 12px" }} />
            <h3 style={{ margin: "0 0 6px", fontSize: "16px", color: "var(--text)" }}>No inspection records found</h3>
            <p style={{ margin: "0 0 20px", fontSize: "13px", color: "var(--text-secondary)" }}>
              {search || typeFilter !== "ALL"
                ? "No matching records found. Try adjusting your search query or filters."
                : "You have not uploaded or analyzed any media assets yet."}
            </p>
            <button
              onClick={() => navigate("/analysis")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 18px",
                borderRadius: "8px",
                background: "var(--primary)",
                color: "#ffffff",
                border: "none",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Start First Analysis →
            </button>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
              <thead>
                <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "12px 20px", fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Asset & Preview</th>
                  <th style={{ padding: "12px 20px", fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Type</th>
                  <th style={{ padding: "12px 20px", fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>File Size</th>
                  <th style={{ padding: "12px 20px", fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Upload Date</th>
                  <th style={{ padding: "12px 20px", fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Ingestion Status</th>
                  <th style={{ padding: "12px 20px", fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const isImage = item.mediaType?.toUpperCase() === "IMAGE";
                  return (
                    <tr
                      key={item.id}
                      style={{
                        borderBottom: "1px solid var(--border)",
                        transition: "background 0.15s ease",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--surface-soft)")}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                    >
                      <td style={{ padding: "14px 20px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                          <div
                            style={{
                              width: "44px",
                              height: "44px",
                              borderRadius: "8px",
                              overflow: "hidden",
                              border: "1px solid var(--border)",
                              background: "#0f172a",
                              display: "grid",
                              placeItems: "center",
                              flexShrink: 0,
                            }}
                          >
                            {isImage ? (
                              <img
                                src={mediaApi.getContentUrl(item.id)}
                                alt={item.originalFilename}
                                style={{ width: "100%", height: "100%", objectFit: "cover" }}
                                onError={(e) => {
                                  (e.target as HTMLElement).style.display = "none";
                                }}
                              />
                            ) : item.mediaType?.toUpperCase() === "AUDIO" ? (
                              <Music size={20} style={{ color: "#f59e0b" }} />
                            ) : (
                              <FileQuestion size={20} style={{ color: "#94a3b8" }} />
                            )}
                          </div>

                          <div style={{ overflow: "hidden" }}>
                            <p style={{ margin: "0 0 2px", fontSize: "14px", fontWeight: 600, color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "280px" }}>
                              {item.originalFilename}
                            </p>
                            <small style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "monospace" }}>
                              UUID: {item.id.substring(0, 8)}... • SHA: {item.sha256Hash ? item.sha256Hash.substring(0, 10) : "—"}
                            </small>
                          </div>
                        </div>
                      </td>

                      <td style={{ padding: "14px 20px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: "4px",
                            background: isImage ? "rgba(99, 102, 241, 0.1)" : "var(--surface-soft)",
                            color: isImage ? "#4f46e5" : "var(--text-secondary)",
                            border: isImage ? "1px solid rgba(99, 102, 241, 0.2)" : "1px solid var(--border)",
                          }}
                        >
                          {item.mediaType || "IMAGE"}
                        </span>
                      </td>

                      <td style={{ padding: "14px 20px", fontSize: "13px", color: "var(--text-secondary)" }}>
                        {formatFileSize(item.fileSize)}
                      </td>

                      <td style={{ padding: "14px 20px", fontSize: "13px", color: "var(--text-secondary)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <Clock size={13} style={{ color: "var(--text-muted)" }} />
                          <span>{formatDate(item.createdAt)}</span>
                        </div>
                      </td>

                      <td style={{ padding: "14px 20px" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: "4px",
                            background: "rgba(16, 185, 129, 0.12)",
                            color: "#10b981",
                            border: "1px solid rgba(16, 185, 129, 0.25)",
                          }}
                        >
                          <ShieldCheck size={12} />
                          <span>{item.uploadStatus || "PROCESSED"}</span>
                        </span>
                      </td>

                      <td style={{ padding: "14px 20px", textAlign: "right" }}>
                        <button
                          onClick={() => navigate(`/analysis?id=${item.id}`)}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "7px 14px",
                            borderRadius: "7px",
                            border: "1px solid var(--primary)",
                            background: "var(--primary-soft)",
                            color: "var(--primary)",
                            fontSize: "12px",
                            fontWeight: 600,
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                        >
                          <span>Inspect Analysis</span>
                          <ArrowRight size={13} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default History;
