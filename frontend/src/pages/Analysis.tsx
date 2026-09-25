import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { mediaApi, forensicsApi } from "../services/api";
import type { MediaResponse } from "../types/media";
import type {
  ImageAnalysisResponse,
  VideoAnalysisResponse,
  AudioAnalysisResponse,
  AvSyncAnalysisResponse,
  OcrResultResponse,
  TranscriptResponse,
  MetadataResponse,
  FingerprintResponse,
  DuplicateMatchResponse,
} from "../types/forensics";
import type { ClaimAnalysisResponse } from "../types/claim";
import { ClaimList } from "../components/claims/ClaimList";
import {
  AlertCircle,
  RefreshCw,
  Scan,
  ExternalLink,
} from "lucide-react";

type AnalysisTab =
  | "overview"
  | "image"
  | "video"
  | "audio"
  | "avsync"
  | "ocr"
  | "transcript"
  | "claims"
  | "metadata";

export function Analysis() {
  const [searchParams, setSearchParams] = useSearchParams();
  const mediaIdParam = searchParams.get("id");

  const [activeTab, setActiveTab] = useState<AnalysisTab>("overview");
  const [mediaList, setMediaList] = useState<MediaResponse[]>([]);
  const [selectedMedia, setSelectedMedia] = useState<MediaResponse | null>(null);

  // Module state
  const [isLoadingMedia, setIsLoadingMedia] = useState(false);
  const [mediaError, setMediaError] = useState<string | null>(null);

  // Domain states
  const [imageAnalysis, setImageAnalysis] = useState<ImageAnalysisResponse | null>(null);
  const [videoAnalysis, setVideoAnalysis] = useState<VideoAnalysisResponse | null>(null);
  const [audioAnalysis, setAudioAnalysis] = useState<AudioAnalysisResponse | null>(null);
  const [avSyncAnalysis, setAvSyncAnalysis] = useState<AvSyncAnalysisResponse | null>(null);
  const [ocrResult, setOcrResult] = useState<OcrResultResponse | null>(null);
  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null);
  const [claimsData, setClaimsData] = useState<ClaimAnalysisResponse | null>(null);
  const [metadata, setMetadata] = useState<MetadataResponse | null>(null);
  const [fingerprint, setFingerprint] = useState<FingerprintResponse | null>(null);
  const [duplicates, setDuplicates] = useState<DuplicateMatchResponse[]>([]);

  // Sub-tab loading & error states
  const [tabLoading, setTabLoading] = useState(false);
  const [tabError, setTabError] = useState<string | null>(null);
  const [isReanalyzing, setIsReanalyzing] = useState(false);

  // 1. Load user uploads for quick selector
  useEffect(() => {
    mediaApi
      .getMyMedia()
      .then((items) => {
        setMediaList(items);
        if (!mediaIdParam && items.length > 0) {
          // Auto-select latest media if none in URL
          setSearchParams({ id: items[0].id });
        }
      })
      .catch(() => {
        // user may not have uploads yet
      });
  }, [mediaIdParam, setSearchParams]);

  // 2. Load selected media record
  useEffect(() => {
    if (!mediaIdParam) {
      setSelectedMedia(null);
      return;
    }

    setIsLoadingMedia(true);
    setMediaError(null);

    mediaApi
      .getById(mediaIdParam)
      .then((media) => {
        setSelectedMedia(media);
        // Reset sub-analysis states
        setImageAnalysis(null);
        setVideoAnalysis(null);
        setAudioAnalysis(null);
        setAvSyncAnalysis(null);
        setOcrResult(null);
        setTranscript(null);
        setClaimsData(null);
        setMetadata(null);
        setFingerprint(null);
        setDuplicates([]);
      })
      .catch((err: any) => {
        setMediaError(err?.message || "Failed to load media details.");
        setSelectedMedia(null);
      })
      .finally(() => {
        setIsLoadingMedia(false);
      });
  }, [mediaIdParam]);

  // 3. Load tab data on demand
  useEffect(() => {
    if (!selectedMedia) return;
    const mediaId = selectedMedia.id;
    const mediaType = selectedMedia.mediaType?.toUpperCase();

    setTabLoading(true);
    setTabError(null);

    const loadTabData = async () => {
      try {
        if (activeTab === "overview") {
          const [fp, dup, meta] = await Promise.allSettled([
            forensicsApi.getFingerprint(mediaId),
            forensicsApi.getDuplicates(mediaId),
            forensicsApi.getMetadata(mediaId),
          ]);
          if (fp.status === "fulfilled") setFingerprint(fp.value);
          if (dup.status === "fulfilled") setDuplicates(dup.value);
          if (meta.status === "fulfilled") setMetadata(meta.value);
        } else if (activeTab === "image") {
          if (mediaType === "IMAGE") {
            const res = await forensicsApi.getImageAnalysis(mediaId);
            setImageAnalysis(res);
          }
        } else if (activeTab === "video") {
          if (mediaType === "VIDEO") {
            const res = await forensicsApi.getVideoAnalysis(mediaId);
            setVideoAnalysis(res);
          }
        } else if (activeTab === "audio") {
          if (mediaType === "AUDIO" || mediaType === "VIDEO") {
            const res = await forensicsApi.getAudioAnalysis(mediaId);
            setAudioAnalysis(res);
          }
        } else if (activeTab === "avsync") {
          if (mediaType === "VIDEO") {
            const res = await forensicsApi.getAvSyncAnalysis(mediaId);
            setAvSyncAnalysis(res);
          }
        } else if (activeTab === "ocr") {
          const res = await forensicsApi.getOcr(mediaId);
          setOcrResult(res);
        } else if (activeTab === "transcript") {
          const res = await forensicsApi.getTranscript(mediaId);
          setTranscript(res);
        } else if (activeTab === "claims") {
          const res = await forensicsApi.getClaims(mediaId);
          setClaimsData(res);
        } else if (activeTab === "metadata") {
          const res = await forensicsApi.getMetadata(mediaId);
          setMetadata(res);
        }
      } catch (err: any) {
        setTabError(err?.message || `Failed to retrieve ${activeTab} analysis findings.`);
      } finally {
        setTabLoading(false);
      }
    };

    loadTabData();
  }, [activeTab, selectedMedia]);

  const handleMediaChange = (id: string) => {
    setSearchParams({ id });
  };

  const currentType = selectedMedia?.mediaType?.toUpperCase();

  return (
    <div className="analysis-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">FORENSIC ANALYSIS</span>
          <h2>Analysis Workspace</h2>
          <p>Inspect real forensic authenticity signals, heatmaps, transcripts, and verified claims.</p>
        </div>

        {selectedMedia && (
          <div className="analysis-id">
            <span>MEDIA ID</span>
            <strong>{selectedMedia.id.substring(0, 8)}...</strong>
          </div>
        )}
      </div>

      {/* Media Selector Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "12px",
          padding: "12px 18px",
          marginBottom: "20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "11px", fontWeight: 750, color: "var(--text-secondary)", textTransform: "uppercase" }}>
            Investigating:
          </span>
          {mediaList.length > 0 ? (
            <select
              value={selectedMedia?.id || ""}
              onChange={(e) => handleMediaChange(e.target.value)}
              style={{
                padding: "6px 12px",
                borderRadius: "6px",
                border: "1px solid var(--border)",
                background: "var(--surface-soft)",
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--text)",
              }}
            >
              {mediaList.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.originalFilename} ({m.mediaType})
                </option>
              ))}
            </select>
          ) : (
            <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              No media uploaded yet.
            </span>
          )}
        </div>

        <Link
          to="/upload"
          className="primary-button"
          style={{ fontSize: "12px", padding: "6px 14px", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px" }}
        >
          <span>Upload New Evidence</span>
          <ExternalLink size={13} />
        </Link>
      </div>

      {isLoadingMedia && (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>
          <div className="status-dot" style={{ margin: "0 auto 12px", background: "var(--primary)" }} />
          <span>Loading media asset...</span>
        </div>
      )}

      {mediaError && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            background: "var(--danger-soft)",
            color: "var(--danger)",
            padding: "16px 20px",
            borderRadius: "10px",
            fontSize: "14px",
            marginBottom: "20px",
          }}
        >
          <AlertCircle size={18} />
          <span>{mediaError}</span>
        </div>
      )}

      {!selectedMedia && !isLoadingMedia && !mediaError && (
        <div
          style={{
            background: "var(--surface)",
            border: "1px dashed var(--border)",
            borderRadius: "16px",
            padding: "60px 20px",
            textAlign: "center",
          }}
        >
          <div style={{ width: 48, height: 48, borderRadius: 12, background: "var(--primary-soft)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 14px" }}>
            <Scan size={24} />
          </div>
          <h3 style={{ margin: "0 0 8px", fontSize: "18px", fontWeight: 700 }}>No Media Selected</h3>
          <p style={{ margin: "0 0 20px", fontSize: "14px", color: "var(--text-secondary)" }}>
            Upload evidence or select an existing asset to view detailed forensic analysis.
          </p>
          <Link to="/upload" className="primary-button" style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
            <span>Go to Upload</span>
          </Link>
        </div>
      )}

      {selectedMedia && (
        <>
          {/* Navigation Tabs */}
          <div className="analysis-tabs">
            <button
              className={activeTab === "overview" ? "analysis-tab active" : "analysis-tab"}
              onClick={() => setActiveTab("overview")}
            >
              Overview
            </button>

            {currentType === "IMAGE" && (
              <button
                className={activeTab === "image" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("image")}
              >
                Image Authenticity
              </button>
            )}

            {currentType === "VIDEO" && (
              <button
                className={activeTab === "video" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("video")}
              >
                Video Deepfake
              </button>
            )}

            {(currentType === "AUDIO" || currentType === "VIDEO") && (
              <button
                className={activeTab === "audio" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("audio")}
              >
                Audio & Voice
              </button>
            )}

            {currentType === "VIDEO" && (
              <button
                className={activeTab === "avsync" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("avsync")}
              >
                AV Lip-Sync
              </button>
            )}

            {(currentType === "IMAGE" || currentType === "VIDEO") && (
              <button
                className={activeTab === "ocr" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("ocr")}
              >
                OCR Text
              </button>
            )}

            {(currentType === "AUDIO" || currentType === "VIDEO") && (
              <button
                className={activeTab === "transcript" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("transcript")}
              >
                Transcript (ASR)
              </button>
            )}

            <button
              className={activeTab === "claims" ? "analysis-tab active" : "analysis-tab"}
              onClick={() => setActiveTab("claims")}
            >
              Claims & Entities
            </button>

            <button
              className={activeTab === "metadata" ? "analysis-tab active" : "analysis-tab"}
              onClick={() => setActiveTab("metadata")}
            >
              EXIF & Forensics
            </button>
          </div>

          {tabLoading && (
            <div style={{ padding: "30px", textAlign: "center", color: "var(--text-secondary)" }}>
              <div className="status-dot" style={{ margin: "0 auto 10px", background: "var(--primary)" }} />
              <span>Querying internal AI/ML forensic service...</span>
            </div>
          )}

          {tabError && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                background: "var(--warning-soft)",
                color: "var(--warning)",
                padding: "14px 18px",
                borderRadius: "10px",
                fontSize: "14px",
                marginBottom: "20px",
              }}
            >
              <AlertCircle size={18} />
              <span>{tabError}</span>
            </div>
          )}

          {/* TAB 1: OVERVIEW */}
          {activeTab === "overview" && (
            <div>
              <div className="analysis-overview-grid">
                <div className="analysis-summary-card">
                  <span className="card-label">ASSET DETAILS</span>
                  <div style={{ fontSize: "16px", fontWeight: 700, margin: "8px 0 4px" }}>
                    {selectedMedia.originalFilename}
                  </div>
                  <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                    MIME: {selectedMedia.mimeType} · Size: {(selectedMedia.fileSize / 1024).toFixed(1)} KB
                  </p>
                  <p style={{ marginTop: "8px", fontSize: "11px", fontFamily: "monospace", color: "var(--text-muted)", wordBreak: "break-all" }}>
                    SHA-256: {selectedMedia.sha256Hash}
                  </p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">STATUS & QUARANTINE</span>
                  <div className="analysis-status" style={{ margin: "8px 0" }}>
                    <span className="status-dot" style={{ background: "var(--success)" }} />
                    {selectedMedia.uploadStatus}
                  </div>
                  <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                    Quarantined: {new Date(selectedMedia.createdAt).toLocaleString()}
                  </p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">DUPLICATE / PROVENANCE</span>
                  <div style={{ fontSize: "20px", fontWeight: 800, margin: "6px 0", color: duplicates.length > 0 ? "var(--warning)" : "var(--success)" }}>
                    {duplicates.length > 0 ? `${duplicates.length} Match(es) Found` : "Unique Asset"}
                  </div>
                  <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                    {fingerprint?.perceptualHash
                      ? `pHash: ${fingerprint.perceptualHash}`
                      : "Perceptual hashing generated"}
                  </p>
                </div>
              </div>

              {/* Forensic Pipeline Matrix */}
              <section className="analysis-section" style={{ marginTop: "24px" }}>
                <div className="section-title-row">
                  <div>
                    <span className="card-label">PIPELINE INTEGRATION</span>
                    <h3>Available Forensics for {selectedMedia.mediaType}</h3>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
                  <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                    <strong>M03 Duplicate Matching</strong>
                    <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--text-secondary)" }}>
                      Perceptual hashing and collision detection.
                    </p>
                  </div>
                  <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                    <strong>M04 Digital Forensics</strong>
                    <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--text-secondary)" }}>
                      EXIF metadata, lens info, and tampering anomalies.
                    </p>
                  </div>
                  {currentType === "IMAGE" && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <strong>M05 Image Authenticity</strong>
                      <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--text-secondary)" }}>
                        PyTorch diffusion classifier + ELA & Grad-CAM.
                      </p>
                    </div>
                  )}
                  {currentType === "VIDEO" && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <strong>M06 Video Deepfake</strong>
                      <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--text-secondary)" }}>
                        3D-CNN temporal tracking and frame anomalies.
                      </p>
                    </div>
                  )}
                  {(currentType === "AUDIO" || currentType === "VIDEO") && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <strong>M07 Audio Forensics</strong>
                      <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--text-secondary)" }}>
                        AASIST synthetic voice and pitch variance.
                      </p>
                    </div>
                  )}
                  {currentType === "VIDEO" && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <strong>M08 AV Sync Lip-Sync</strong>
                      <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--text-secondary)" }}>
                        MediaPipe lip tracking and envelope correlation.
                      </p>
                    </div>
                  )}
                  <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                    <strong>M11 Claims & Entities</strong>
                    <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--text-secondary)" }}>
                      spaCy NER, SVO decomposition & claim hashing.
                    </p>
                  </div>
                </div>
              </section>
            </div>
          )}

          {/* TAB 2: IMAGE AUTHENTICITY (MODULE 05) */}
          {activeTab === "image" && imageAnalysis && (
            <section className="analysis-section">
              <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span className="card-label">MODULE 05 — IMAGE AUTHENTICITY</span>
                  <h3>Visual Forensics & Explainable Heatmaps</h3>
                </div>
                <button
                  className="icon-button"
                  title="Re-run Image Analysis"
                  onClick={async () => {
                    setIsReanalyzing(true);
                    try {
                      const res = await forensicsApi.reanalyzeImage(selectedMedia.id);
                      setImageAnalysis(res);
                    } catch (e: any) {
                      setTabError(e.message);
                    } finally {
                      setIsReanalyzing(false);
                    }
                  }}
                  disabled={isReanalyzing}
                  style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
                >
                  <RefreshCw size={14} className={isReanalyzing ? "status-pulse" : ""} />
                  <span>Re-analyze</span>
                </button>
              </div>

              <div className="analysis-overview-grid" style={{ marginBottom: "24px" }}>
                <div className="analysis-summary-card">
                  <span className="card-label">AI GENERATION PROBABILITY</span>
                  <strong className="analysis-number" style={{ color: imageAnalysis.aiProb > 0.5 ? "var(--danger)" : "var(--success)" }}>
                    {(imageAnalysis.aiProb * 100).toFixed(1)}%
                  </strong>
                  <p>PyTorch Diffusion Classifier Confidence</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">MANIPULATION PROBABILITY</span>
                  <strong className="analysis-number" style={{ color: imageAnalysis.manipulationProb > 0.5 ? "var(--danger)" : "var(--success)" }}>
                    {(imageAnalysis.manipulationProb * 100).toFixed(1)}%
                  </strong>
                  <p>Copy-Move & Splicing Inconsistency</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">ASSESSMENT</span>
                  <div style={{ fontSize: "18px", fontWeight: 750, marginTop: "8px" }}>
                    {imageAnalysis.authenticityAssessment}
                  </div>
                  <p>Status: {imageAnalysis.analysisStatus}</p>
                </div>
              </div>

              {/* Artifacts: ELA & Grad-CAM */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
                <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                  <h4 style={{ margin: "0 0 10px", fontSize: "14px" }}>Error Level Analysis (ELA)</h4>
                  <p style={{ margin: "0 0 12px", fontSize: "12px", color: "var(--text-secondary)" }}>
                    Reveals compression inconsistencies and splicing boundaries.
                  </p>
                  <div style={{ background: "#000", borderRadius: "8px", overflow: "hidden", minHeight: "200px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <img
                      src={forensicsApi.getImageArtifactUrl(selectedMedia.id, "ela")}
                      alt="ELA Heatmap"
                      style={{ maxWidth: "100%", maxHeight: "300px", display: "block" }}
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = "none";
                      }}
                    />
                  </div>
                </div>

                <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                  <h4 style={{ margin: "0 0 10px", fontSize: "14px" }}>Grad-CAM Attention Heatmap</h4>
                  <p style={{ margin: "0 0 12px", fontSize: "12px", color: "var(--text-secondary)" }}>
                    Spatial gradients highlighting neural network attention regions.
                  </p>
                  <div style={{ background: "#000", borderRadius: "8px", overflow: "hidden", minHeight: "200px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <img
                      src={forensicsApi.getImageArtifactUrl(selectedMedia.id, "gradcam")}
                      alt="Grad-CAM Heatmap"
                      style={{ maxWidth: "100%", maxHeight: "300px", display: "block" }}
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = "none";
                      }}
                    />
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* TAB 3: VIDEO DEEPFAKE (MODULE 06) */}
          {activeTab === "video" && videoAnalysis && (
            <section className="analysis-section">
              <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span className="card-label">MODULE 06 — VIDEO DEEPFAKE DETECTION</span>
                  <h3>Temporal Face Inconsistency & Deepfake Probability</h3>
                </div>
                <button
                  className="icon-button"
                  title="Re-run Video Analysis"
                  onClick={async () => {
                    setIsReanalyzing(true);
                    try {
                      const res = await forensicsApi.reanalyzeVideo(selectedMedia.id);
                      setVideoAnalysis(res);
                    } catch (e: any) {
                      setTabError(e.message);
                    } finally {
                      setIsReanalyzing(false);
                    }
                  }}
                  disabled={isReanalyzing}
                  style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
                >
                  <RefreshCw size={14} className={isReanalyzing ? "status-pulse" : ""} />
                  <span>Re-analyze</span>
                </button>
              </div>

              <div className="analysis-overview-grid" style={{ marginBottom: "24px" }}>
                <div className="analysis-summary-card">
                  <span className="card-label">DEEPFAKE PROBABILITY</span>
                  <strong className="analysis-number" style={{ color: videoAnalysis.deepfake_prob > 0.5 ? "var(--danger)" : "var(--success)" }}>
                    {(videoAnalysis.deepfake_prob * 100).toFixed(1)}%
                  </strong>
                  <p>3D-CNN Model Prediction</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">FACE TRACKING METRICS</span>
                  <div style={{ fontSize: "20px", fontWeight: 800, margin: "8px 0" }}>
                    {videoAnalysis.face_count} Face(s) Detected
                  </div>
                  <p>{videoAnalysis.total_frames_sampled} frames sampled deterministically</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">VERDICT</span>
                  <div style={{ fontSize: "18px", fontWeight: 750, marginTop: "8px" }}>
                    {videoAnalysis.authenticity_assessment}
                  </div>
                  <p>Status: {videoAnalysis.analysis_status}</p>
                </div>
              </div>

              {/* Suspicious Timestamps */}
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                <h4 style={{ margin: "0 0 14px", fontSize: "14px" }}>Suspicious Temporal Markers</h4>
                {videoAnalysis.suspicious_timestamps && videoAnalysis.suspicious_timestamps.length > 0 ? (
                  <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--text-secondary)" }}>
                        <th style={{ padding: "8px" }}>Timestamp</th>
                        <th style={{ padding: "8px" }}>Frame #</th>
                        <th style={{ padding: "8px" }}>Anomaly Score</th>
                        <th style={{ padding: "8px" }}>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {videoAnalysis.suspicious_timestamps.map((t, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "8px", fontWeight: 600 }}>{t.timestamp_seconds.toFixed(2)}s</td>
                          <td style={{ padding: "8px" }}>{t.frame_index}</td>
                          <td style={{ padding: "8px", color: "var(--danger)" }}>{(t.anomaly_score * 100).toFixed(1)}%</td>
                          <td style={{ padding: "8px" }}>{t.reason || "Facial boundary anomaly"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted)" }}>
                    No suspicious timestamp discontinuities detected in sampled video keyframes.
                  </p>
                )}
              </div>
            </section>
          )}

          {/* TAB 4: AUDIO AUTHENTICITY (MODULE 07) */}
          {activeTab === "audio" && audioAnalysis && (
            <section className="analysis-section">
              <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span className="card-label">MODULE 07 — AUDIO AUTHENTICITY & VOICE FORENSICS</span>
                  <h3>Synthetic Speech & Acoustic Forensics</h3>
                </div>
                <button
                  className="icon-button"
                  title="Re-run Audio Analysis"
                  onClick={async () => {
                    setIsReanalyzing(true);
                    try {
                      const res = await forensicsApi.reanalyzeAudio(selectedMedia.id);
                      setAudioAnalysis(res);
                    } catch (e: any) {
                      setTabError(e.message);
                    } finally {
                      setIsReanalyzing(false);
                    }
                  }}
                  disabled={isReanalyzing}
                  style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
                >
                  <RefreshCw size={14} className={isReanalyzing ? "status-pulse" : ""} />
                  <span>Re-analyze</span>
                </button>
              </div>

              <div className="analysis-overview-grid" style={{ marginBottom: "24px" }}>
                <div className="analysis-summary-card">
                  <span className="card-label">SYNTHETIC VOICE PROBABILITY</span>
                  <strong className="analysis-number" style={{ color: audioAnalysis.synthetic_voice_prob > 0.5 ? "var(--danger)" : "var(--success)" }}>
                    {(audioAnalysis.synthetic_voice_prob * 100).toFixed(1)}%
                  </strong>
                  <p>AASIST Graph Attention Model</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">ACOUSTIC INDICATORS</span>
                  <div style={{ fontSize: "14px", margin: "8px 0" }}>
                    <div>Pitch Variance: <strong>{audioAnalysis.pitch_variance.toFixed(2)}</strong></div>
                    <div style={{ marginTop: "4px" }}>Phase Discontinuity: <strong>{audioAnalysis.phase_discontinuity.toFixed(2)}</strong></div>
                  </div>
                  <p>STFT & Fundamental Frequency (YIN)</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">ASSESSMENT</span>
                  <div style={{ fontSize: "18px", fontWeight: 750, marginTop: "8px" }}>
                    {audioAnalysis.authenticity_assessment}
                  </div>
                  <p>Splice Markers: {audioAnalysis.splice_markers?.length || 0}</p>
                </div>
              </div>

              {audioAnalysis.spectrogram_base64 && (
                <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px", marginBottom: "20px" }}>
                  <h4 style={{ margin: "0 0 10px", fontSize: "14px" }}>80-Band Mel-Spectrogram</h4>
                  <img
                    src={`data:image/png;base64,${audioAnalysis.spectrogram_base64}`}
                    alt="Spectrogram"
                    style={{ maxWidth: "100%", maxHeight: "260px", display: "block", borderRadius: "6px" }}
                  />
                </div>
              )}
            </section>
          )}

          {/* TAB 5: AV SYNC (MODULE 08) */}
          {activeTab === "avsync" && avSyncAnalysis && (
            <section className="analysis-section">
              <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span className="card-label">MODULE 08 — AUDIO-VISUAL SYNCHRONIZATION</span>
                  <h3>Lip-Sync Drift & Mismatch Intervals</h3>
                </div>
                <button
                  className="icon-button"
                  title="Re-run AV Sync Analysis"
                  onClick={async () => {
                    setIsReanalyzing(true);
                    try {
                      const res = await forensicsApi.reanalyzeAvSync(selectedMedia.id);
                      setAvSyncAnalysis(res);
                    } catch (e: any) {
                      setTabError(e.message);
                    } finally {
                      setIsReanalyzing(false);
                    }
                  }}
                  disabled={isReanalyzing}
                  style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
                >
                  <RefreshCw size={14} className={isReanalyzing ? "status-pulse" : ""} />
                  <span>Re-analyze</span>
                </button>
              </div>

              <div className="analysis-overview-grid" style={{ marginBottom: "24px" }}>
                <div className="analysis-summary-card">
                  <span className="card-label">SYNC SCORE</span>
                  <strong className="analysis-number" style={{ color: avSyncAnalysis.syncScore < 0.5 ? "var(--danger)" : "var(--success)" }}>
                    {(avSyncAnalysis.syncScore * 100).toFixed(1)}%
                  </strong>
                  <p>Cross-Modal Embedding Alignment</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">LIP OFFSET</span>
                  <div style={{ fontSize: "24px", fontWeight: 800, margin: "8px 0" }}>
                    {avSyncAnalysis.lipOffsetMs > 0 ? `+${avSyncAnalysis.lipOffsetMs}` : avSyncAnalysis.lipOffsetMs} ms
                  </div>
                  <p>Confidence: {(avSyncAnalysis.confidence * 100).toFixed(1)}%</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">ASSESSMENT</span>
                  <div style={{ fontSize: "18px", fontWeight: 750, marginTop: "8px" }}>
                    {avSyncAnalysis.assessment}
                  </div>
                  <p>Mismatches: {avSyncAnalysis.mismatchSegments?.length || 0}</p>
                </div>
              </div>
            </section>
          )}

          {/* TAB 6: OCR (MODULE 09) */}
          {activeTab === "ocr" && ocrResult && (
            <section className="analysis-section">
              <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span className="card-label">MODULE 09 — OPTICAL CHARACTER RECOGNITION</span>
                  <h3>Visual Text & Embedded News Banners</h3>
                </div>
                <button
                  className="icon-button"
                  title="Re-run OCR"
                  onClick={async () => {
                    setIsReanalyzing(true);
                    try {
                      const res = await forensicsApi.reanalyzeOcr(selectedMedia.id);
                      setOcrResult(res);
                    } catch (e: any) {
                      setTabError(e.message);
                    } finally {
                      setIsReanalyzing(false);
                    }
                  }}
                  disabled={isReanalyzing}
                  style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
                >
                  <RefreshCw size={14} className={isReanalyzing ? "status-pulse" : ""} />
                  <span>Re-analyze</span>
                </button>
              </div>

              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px", marginBottom: "20px" }}>
                <span className="card-label">EXTRACTED VISUAL TEXT</span>
                <p style={{ fontSize: "15px", lineHeight: "1.6", whiteSpace: "pre-wrap", margin: "10px 0" }}>
                  {ocrResult.extractedText || "(No visual text detected in this media asset)"}
                </p>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", gap: "16px" }}>
                  <span>Language: <strong>{ocrResult.language}</strong></span>
                  <span>Confidence: <strong>{(ocrResult.confidenceScore * 100).toFixed(1)}%</strong></span>
                  <span>Regions: <strong>{ocrResult.regionsCount}</strong></span>
                </div>
              </div>
            </section>
          )}

          {/* TAB 7: TRANSCRIPT (MODULE 10) */}
          {activeTab === "transcript" && transcript && (
            <section className="analysis-section">
              <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span className="card-label">MODULE 10 — SPEECH-TO-TEXT & TRANSCRIPTION</span>
                  <h3>Faster-Whisper Spoken Audio Extraction</h3>
                </div>
                <button
                  className="icon-button"
                  title="Re-run Transcription"
                  onClick={async () => {
                    setIsReanalyzing(true);
                    try {
                      const res = await forensicsApi.reanalyzeTranscript(selectedMedia.id);
                      setTranscript(res);
                    } catch (e: any) {
                      setTabError(e.message);
                    } finally {
                      setIsReanalyzing(false);
                    }
                  }}
                  disabled={isReanalyzing}
                  style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
                >
                  <RefreshCw size={14} className={isReanalyzing ? "status-pulse" : ""} />
                  <span>Re-transcribe</span>
                </button>
              </div>

              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px", marginBottom: "20px" }}>
                <span className="card-label">FULL TRANSCRIPT</span>
                <p style={{ fontSize: "15px", lineHeight: "1.6", whiteSpace: "pre-wrap", margin: "10px 0" }}>
                  {transcript.fullText || "(No speech detected in this media track)"}
                </p>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", gap: "16px" }}>
                  <span>Language: <strong>{transcript.language}</strong></span>
                  <span>Confidence: <strong>{(transcript.confidenceScore * 100).toFixed(1)}%</strong></span>
                  <span>Duration: <strong>{transcript.durationSeconds.toFixed(1)}s</strong></span>
                  <span>Words: <strong>{transcript.wordsCount}</strong></span>
                </div>
              </div>

              {transcript.segments && transcript.segments.length > 0 && (
                <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                  <h4 style={{ margin: "0 0 12px", fontSize: "14px" }}>Timestamped Segments</h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {transcript.segments.map((seg) => (
                      <div
                        key={seg.segment_id}
                        style={{
                          display: "flex",
                          gap: "12px",
                          padding: "8px 12px",
                          borderRadius: "6px",
                          background: "var(--surface-soft)",
                          fontSize: "13px",
                        }}
                      >
                        <span style={{ fontFamily: "monospace", color: "var(--primary)", minWidth: "90px" }}>
                          [{seg.start_seconds.toFixed(2)}s - {seg.end_seconds.toFixed(2)}s]
                        </span>
                        <span style={{ flex: 1 }}>{seg.text}</span>
                        <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                          {(seg.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          {/* TAB 8: CLAIMS (MODULE 11) */}
          {activeTab === "claims" && (
            <section className="analysis-section">
              <ClaimList
                mediaId={selectedMedia.id}
                initialData={claimsData}
                isLoading={tabLoading}
                onReanalyze={async () => {
                  const res = await forensicsApi.reanalyzeClaims(selectedMedia.id);
                  setClaimsData(res);
                }}
                onAnalyzeDirectText={async (text) => {
                  return await forensicsApi.extractTextClaims(text);
                }}
              />
            </section>
          )}

          {/* TAB 9: EXIF & FORENSICS (MODULE 04) */}
          {activeTab === "metadata" && (
            <section className="analysis-section">
              <div className="section-title-row">
                <div>
                  <span className="card-label">MODULE 04 — METADATA FORENSICS</span>
                  <h3>Camera Make, Model, Timestamps & Anomalies</h3>
                </div>
              </div>

              {metadata ? (
                <div>
                  <div className="analysis-overview-grid" style={{ marginBottom: "20px" }}>
                    <div className="analysis-summary-card">
                      <span className="card-label">DEVICE & HARDWARE</span>
                      <div style={{ fontSize: "16px", fontWeight: 700, margin: "6px 0" }}>
                        {metadata.cameraMake || "Unknown Make"} {metadata.cameraModel || ""}
                      </div>
                      <p>Lens: {metadata.lensModel || "N/A"}</p>
                    </div>

                    <div className="analysis-summary-card">
                      <span className="card-label">TIMESTAMP & SOFTWARE</span>
                      <div style={{ fontSize: "14px", fontWeight: 600, margin: "6px 0" }}>
                        {metadata.dateTimeOriginal || "No timestamp tag"}
                      </div>
                      <p>Software: {metadata.software || "None recorded"}</p>
                    </div>

                    <div className="analysis-summary-card">
                      <span className="card-label">ANOMALIES & INTEGRITY</span>
                      <div style={{ fontSize: "20px", fontWeight: 800, margin: "6px 0", color: metadata.anomaliesCount > 0 ? "var(--warning)" : "var(--success)" }}>
                        {metadata.anomaliesCount} Anomaly(s)
                      </div>
                      <p>Forensic Score: {metadata.forensicScore.toFixed(2)}</p>
                    </div>
                  </div>

                  {metadata.anomalies && metadata.anomalies.length > 0 && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                      <h4 style={{ margin: "0 0 12px", fontSize: "14px" }}>Detected Metadata Anomalies</h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {metadata.anomalies.map((a, i) => (
                          <div key={i} style={{ padding: "10px 14px", borderRadius: "6px", background: "var(--warning-soft)", color: "var(--warning)", fontSize: "13px" }}>
                            <strong>[{a.tag}] {a.anomalyType}:</strong> {a.description}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>
                  No EXIF metadata findings available.
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default Analysis;