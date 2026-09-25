import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { mediaApi, forensicsApi } from "../services/api";
import type { MediaResponse } from "../types/media";
import type {
  ImageAnalysisResponse,
  VideoAnalysisResponse,
  AudioAnalysisResponse,
} from "../types/forensics";
import {
  UploadCloud,
  ArrowRight,
  Info,
} from "lucide-react";

export function Dashboard() {
  const navigate = useNavigate();
  const [mediaList, setMediaList] = useState<MediaResponse[]>([]);
  const [selectedMedia, setSelectedMedia] = useState<MediaResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Real analysis signals for selected media
  const [imageAnalysis, setImageAnalysis] = useState<ImageAnalysisResponse | null>(null);
  const [videoAnalysis, setVideoAnalysis] = useState<VideoAnalysisResponse | null>(null);
  const [audioAnalysis, setAudioAnalysis] = useState<AudioAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    mediaApi
      .getMyMedia()
      .then((items) => {
        setMediaList(items);
        if (items.length > 0) {
          setSelectedMedia(items[0]);
        }
      })
      .catch(() => {
        // ignore load errors
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedMedia) return;

    setIsAnalyzing(true);
    setImageAnalysis(null);
    setVideoAnalysis(null);
    setAudioAnalysis(null);

    const type = selectedMedia.mediaType?.toUpperCase();
    const id = selectedMedia.id;

    if (type === "IMAGE") {
      forensicsApi
        .getImageAnalysis(id)
        .then(setImageAnalysis)
        .catch(() => null)
        .finally(() => setIsAnalyzing(false));
    } else if (type === "VIDEO") {
      forensicsApi
        .getVideoAnalysis(id)
        .then(setVideoAnalysis)
        .catch(() => null)
        .finally(() => setIsAnalyzing(false));
    } else if (type === "AUDIO") {
      forensicsApi
        .getAudioAnalysis(id)
        .then(setAudioAnalysis)
        .catch(() => null)
        .finally(() => setIsAnalyzing(false));
    } else {
      setIsAnalyzing(false);
    }
  }, [selectedMedia]);

  // Derived real primary score
  let primaryScore: number | null = null;
  let primaryLabel = "AI / Manipulation Likelihood";
  let assessment = "Analysis Ready";

  if (imageAnalysis) {
    primaryScore = Math.round(Math.max(imageAnalysis.aiProb, imageAnalysis.manipulationProb) * 100);
    primaryLabel = imageAnalysis.aiProb > imageAnalysis.manipulationProb ? "AI Probability" : "Manipulation Probability";
    assessment = imageAnalysis.authenticityAssessment;
  } else if (videoAnalysis) {
    primaryScore = Math.round(videoAnalysis.deepfake_prob * 100);
    primaryLabel = "Deepfake Probability";
    assessment = videoAnalysis.authenticity_assessment;
  } else if (audioAnalysis) {
    primaryScore = Math.round(audioAnalysis.synthetic_voice_prob * 100);
    primaryLabel = "Synthetic Voice Probability";
    assessment = audioAnalysis.authenticity_assessment;
  }

  const riskLevel =
    primaryScore !== null
      ? primaryScore >= 70
        ? "high"
        : primaryScore >= 40
        ? "medium"
        : "low"
      : "low";

  const riskBadgeText =
    primaryScore !== null
      ? primaryScore >= 70
        ? "High Risk"
        : primaryScore >= 40
        ? "Medium Risk"
        : "Low Risk"
      : "No Score";

  return (
    <div className="dashboard">
      {/* HEADER */}
      <header className="dashboard-header">
        <div>
          <span className="eyebrow">ANALYSIS OVERVIEW</span>
          <h2>Investigation Dashboard</h2>
          <p>Review real evidence and multi-modal authenticity signals across active investigations.</p>
        </div>

        <div className="dashboard-header-actions">
          {selectedMedia ? (
            <>
              <div className="media-id">
                <span>MEDIA ID</span>
                <strong>{selectedMedia.id.substring(0, 8)}...</strong>
              </div>

              <button
                className="primary-button"
                onClick={() => navigate(`/analysis?id=${selectedMedia.id}`)}
              >
                View Full Analysis →
              </button>
            </>
          ) : (
            <button
              className="primary-button"
              onClick={() => navigate("/upload")}
            >
              Upload Evidence →
            </button>
          )}
        </div>
      </header>

      {/* RISK HERO (REAL DATA ONLY) */}
      {isLoading ? (
        <section
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "16px",
            padding: "48px 24px",
            textAlign: "center",
            marginBottom: "24px",
          }}
        >
          <div className="status-dot" style={{ width: 14, height: 14, margin: "0 auto 12px", background: "var(--primary)" }} />
          <p style={{ margin: 0, fontSize: "14px", color: "var(--text-secondary)" }}>
            Loading active investigations from backend...
          </p>
        </section>
      ) : selectedMedia ? (
        <section className="risk-hero">
          <div className="risk-hero-main">
            <div className="risk-heading">
              <span className="card-label">{primaryLabel.toUpperCase()}</span>
              {primaryScore !== null && (
                <span className={`risk-pill ${riskLevel}`}>
                  <span className="risk-pill-dot" />
                  {riskBadgeText}
                </span>
              )}
            </div>

            <div className="risk-number">
              {isAnalyzing ? (
                <span style={{ fontSize: "32px", color: "var(--text-muted)" }}>Analyzing...</span>
              ) : primaryScore !== null ? (
                <>
                  {primaryScore}
                  <span>/100</span>
                </>
              ) : (
                <span style={{ fontSize: "28px", color: "var(--text-muted)" }}>Pending</span>
              )}
            </div>

            {primaryScore !== null && (
              <div className="risk-meter">
                <div style={{ width: `${primaryScore}%` }} />
              </div>
            )}

            <p className="risk-caption">
              Primary forensic authenticity signal for <strong>{selectedMedia.originalFilename}</strong> ({selectedMedia.mediaType}).
            </p>
          </div>

          <div className="risk-hero-explanation">
            <span className="card-label">AUTHENTICITY VERDICT</span>
            <h3>{assessment}</h3>

            <div style={{ margin: "14px 0", fontSize: "13px", color: "#b0b4bd", lineHeight: "1.6" }}>
              <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "6px" }}>
                <Info size={15} style={{ flexShrink: 0, color: "var(--primary)" }} />
                <span>
                  <strong>Module 15 Risk Engine:</strong> Weighted aggregate risk engine is pending backend module implementation. Displaying verified neural network signals above.
                </span>
              </div>
            </div>

            <button
              className="hero-link"
              onClick={() => navigate(`/analysis?id=${selectedMedia.id}`)}
            >
              Explore supporting evidence
              <span>→</span>
            </button>
          </div>
        </section>
      ) : (
        <section
          style={{
            background: "var(--surface)",
            border: "1px dashed var(--border)",
            borderRadius: "16px",
            padding: "48px 24px",
            textAlign: "center",
            marginBottom: "24px",
          }}
        >
          <div style={{ width: 44, height: 44, borderRadius: 10, background: "var(--primary-soft)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
            <UploadCloud size={24} />
          </div>
          <h3 style={{ margin: "0 0 6px", fontSize: "18px", fontWeight: 700 }}>No Active Investigations</h3>
          <p style={{ margin: "0 0 18px", fontSize: "13px", color: "var(--text-secondary)" }}>
            Upload media to begin multi-modal forensic authenticity detection.
          </p>
          <button className="primary-button" onClick={() => navigate("/upload")}>
            Start First Upload →
          </button>
        </section>
      )}

      {/* RECENT INVESTIGATIONS LIST */}
      <section className="dashboard-section" style={{ marginTop: "24px" }}>
        <div className="section-heading">
          <div>
            <span className="card-label">INGESTED EVIDENCE</span>
            <h3>Your Recent Media Uploads</h3>
          </div>

          <span className="section-hint">
            {mediaList.length} Asset(s) Quarantined
          </span>
        </div>

        {mediaList.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {mediaList.map((m) => {
              const isSelected = selectedMedia?.id === m.id;
              return (
                <div
                  key={m.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: "12px",
                    background: isSelected ? "var(--surface)" : "var(--surface-soft)",
                    border: `1px solid ${isSelected ? "var(--primary)" : "var(--border)"}`,
                    borderRadius: "10px",
                    padding: "14px 18px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                    <div
                      style={{
                        width: "36px",
                        height: "36px",
                        borderRadius: "8px",
                        background: "var(--primary-soft)",
                        color: "var(--primary)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "12px",
                        fontWeight: 700,
                      }}
                    >
                      {m.mediaType?.substring(0, 3)}
                    </div>
                    <div>
                      <div style={{ fontWeight: 650, fontSize: "14px", color: "var(--text)" }}>
                        {m.originalFilename}
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                        ID: {m.id.substring(0, 8)}... · {(m.fileSize / 1024).toFixed(1)} KB · {new Date(m.createdAt).toLocaleDateString()}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <button
                      onClick={() => setSelectedMedia(m)}
                      style={{
                        padding: "6px 12px",
                        borderRadius: "6px",
                        border: "1px solid var(--border)",
                        background: "transparent",
                        fontSize: "12px",
                        fontWeight: 600,
                        color: "var(--text)",
                      }}
                    >
                      Feature in Hero
                    </button>
                    <button
                      className="primary-button"
                      style={{ fontSize: "12px", padding: "6px 14px", display: "inline-flex", alignItems: "center", gap: "6px" }}
                      onClick={() => navigate(`/analysis?id=${m.id}`)}
                    >
                      <span>Analyze</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
            No uploads found. Ingest media through the Upload page.
          </div>
        )}
      </section>

      {/* EXPLAINABILITY PANEL */}
      <section className="explainability-panel" style={{ marginTop: "24px" }}>
        <div className="explainability-copy">
          <span className="card-label">EXPLAINABLE AI ARCHITECTURE</span>
          <h3>Signals Grounded in Science</h3>
          <p>
            TruthLens avoids black-box verdicts. Every assessment combines frequency analysis (FFT), error-level analysis (ELA), spatial Grad-CAM attention, acoustic graphs (AASIST), and semantic triples.
          </p>
        </div>

        <div className="explainability-flow">
          <div className="flow-step">
            <span className="flow-number">01</span>
            <strong>Multi-Modal Ingestion</strong>
            <p>Magic-bytes verified, quarantined, and hashed with SHA-256.</p>
          </div>
          <div className="flow-line" />
          <div className="flow-step">
            <span className="flow-number">02</span>
            <strong>Forensic Extraction</strong>
            <p>PyTorch models evaluate localized tampering and diffusion artifacts.</p>
          </div>
          <div className="flow-line" />
          <div className="flow-step">
            <span className="flow-number">03</span>
            <strong>Claim Grounding</strong>
            <p>Visual text (OCR) and spoken audio (ASR) decomposed into verifiable facts.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Dashboard;