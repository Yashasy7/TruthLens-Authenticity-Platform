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
import { ForensicArtifactViewer } from "../components/ForensicArtifactViewer";
import {
  AlertCircle,
  RefreshCw,
  Scan,
  ExternalLink,
  Copy,
  Check,
  Camera,
  MapPin,
  Cpu,
  FileText,
  Volume2,
  Film,
  Sparkles,
  Fingerprint as FingerprintIcon,
} from "lucide-react";

type AnalysisTab =
  | "overview"
  | "image"
  | "video"
  | "audio"
  | "avsync"
  | "ocr"
  | "transcript"
  | "fingerprint"
  | "metadata"
  | "claims";

export function Analysis() {
  const [searchParams, setSearchParams] = useSearchParams();
  const mediaIdParam = searchParams.get("id");

  const [activeTab, setActiveTab] = useState<AnalysisTab>("overview");
  const [mediaList, setMediaList] = useState<MediaResponse[]>([]);
  const [selectedMedia, setSelectedMedia] = useState<MediaResponse | null>(null);

  // Loading states
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
  const [copiedSha, setCopiedSha] = useState(false);
  const [copiedText, setCopiedText] = useState(false);

  // 1. Load user uploads
  useEffect(() => {
    mediaApi
      .getMyMedia()
      .then((items) => {
        setMediaList(items);
        if (!mediaIdParam && items.length > 0) {
          setSearchParams({ id: items[0].id });
        }
      })
      .catch(() => {});
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

  // Ensure activeTab is valid for media type
  const currentType = selectedMedia?.mediaType?.toUpperCase();
  useEffect(() => {
    if (!currentType) return;
    if (currentType === "IMAGE" && (activeTab === "video" || activeTab === "audio" || activeTab === "avsync" || activeTab === "transcript")) {
      setActiveTab("overview");
    } else if (currentType === "AUDIO" && (activeTab === "image" || activeTab === "video" || activeTab === "avsync" || activeTab === "ocr")) {
      setActiveTab("overview");
    }
  }, [currentType, activeTab]);

  // 3. Load tab data on demand
  useEffect(() => {
    if (!selectedMedia) return;
    const mediaId = selectedMedia.id;
    const mediaType = selectedMedia.mediaType?.toUpperCase();

    setTabLoading(true);
    setTabError(null);

    const loadTabData = async () => {
      try {
        if (activeTab === "overview" || activeTab === "fingerprint") {
          const [fp, dup, meta] = await Promise.allSettled([
            forensicsApi.getFingerprint(mediaId),
            forensicsApi.getDuplicates(mediaId),
            forensicsApi.getMetadata(mediaId),
          ]);
          if (fp.status === "fulfilled") setFingerprint(fp.value);
          if (dup.status === "fulfilled") setDuplicates(dup.value);
          if (meta.status === "fulfilled") setMetadata(meta.value);
        } else if (activeTab === "image" && mediaType === "IMAGE") {
          const res = await forensicsApi.getImageAnalysis(mediaId);
          setImageAnalysis(res);
        } else if (activeTab === "video" && mediaType === "VIDEO") {
          const res = await forensicsApi.getVideoAnalysis(mediaId);
          setVideoAnalysis(res);
        } else if (activeTab === "audio" && (mediaType === "AUDIO" || mediaType === "VIDEO")) {
          const res = await forensicsApi.getAudioAnalysis(mediaId);
          setAudioAnalysis(res);
        } else if (activeTab === "avsync" && mediaType === "VIDEO") {
          const res = await forensicsApi.getAvSyncAnalysis(mediaId);
          setAvSyncAnalysis(res);
        } else if (activeTab === "ocr" && (mediaType === "IMAGE" || mediaType === "VIDEO")) {
          const res = await forensicsApi.getOcr(mediaId);
          setOcrResult(res);
        } else if (activeTab === "transcript" && (mediaType === "AUDIO" || mediaType === "VIDEO")) {
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

  const handleCopySha256 = (sha: string) => {
    navigator.clipboard?.writeText(sha);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2000);
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  return (
    <div className="analysis-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">FORENSIC ANALYSIS &amp; VERIFICATION</span>
          <h2>Analysis Workspace</h2>
          <p>Inspect real forensic authenticity signals, spatial heatmaps, transcripts, and verified claims.</p>
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
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
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

          {selectedMedia && (
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                padding: "3px 8px",
                borderRadius: "4px",
                background: "var(--primary-soft)",
                color: "var(--primary)",
              }}
            >
              {selectedMedia.mimeType}
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
          <div className="status-dot status-pulse" style={{ margin: "0 auto 12px", background: "var(--primary)", width: 14, height: 14 }} />
          <span>Loading verified media asset...</span>
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
            <span>Start an Investigation</span>
          </Link>
        </div>
      )}

      {selectedMedia && (
        <>
          {/* Media-Specific Navigation Tabs */}
          <div className="analysis-tabs" style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginBottom: "20px" }}>
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
                Image Authenticity (M05)
              </button>
            )}

            {currentType === "VIDEO" && (
              <button
                className={activeTab === "video" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("video")}
              >
                Video Deepfake (M06)
              </button>
            )}

            {(currentType === "AUDIO" || currentType === "VIDEO") && (
              <button
                className={activeTab === "audio" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("audio")}
              >
                Audio &amp; Voice (M07)
              </button>
            )}

            {currentType === "VIDEO" && (
              <button
                className={activeTab === "avsync" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("avsync")}
              >
                AV Lip-Sync (M08)
              </button>
            )}

            {(currentType === "IMAGE" || currentType === "VIDEO") && (
              <button
                className={activeTab === "ocr" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("ocr")}
              >
                OCR Text (M09)
              </button>
            )}

            {(currentType === "AUDIO" || currentType === "VIDEO") && (
              <button
                className={activeTab === "transcript" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("transcript")}
              >
                Transcript (M10)
              </button>
            )}

            <button
              className={activeTab === "fingerprint" ? "analysis-tab active" : "analysis-tab"}
              onClick={() => setActiveTab("fingerprint")}
            >
              Fingerprint &amp; Duplicates (M03)
            </button>

            {(currentType === "IMAGE" || currentType === "VIDEO") && (
              <button
                className={activeTab === "metadata" ? "analysis-tab active" : "analysis-tab"}
                onClick={() => setActiveTab("metadata")}
              >
                EXIF Metadata (M04)
              </button>
            )}

            <button
              className={activeTab === "claims" ? "analysis-tab active" : "analysis-tab"}
              onClick={() => setActiveTab("claims")}
            >
              Claims &amp; Entities (M11)
            </button>
          </div>

          {/* Tab Loading Spinner */}
          {tabLoading && (
            <div style={{ padding: "30px", textAlign: "center", color: "var(--text-secondary)" }}>
              <div className="status-dot status-pulse" style={{ margin: "0 auto 10px", background: "var(--primary)", width: 12, height: 12 }} />
              <span style={{ fontSize: "13px" }}>Fetching {activeTab} findings from forensic engine...</span>
            </div>
          )}

          {/* Tab Error Banner */}
          {tabError && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                background: "var(--danger-soft)",
                color: "var(--danger)",
                padding: "14px 18px",
                borderRadius: "8px",
                fontSize: "13px",
                marginBottom: "20px",
              }}
            >
              <AlertCircle size={16} />
              <span>{tabError}</span>
            </div>
          )}

          {/* TAB 1: OVERVIEW */}
          {activeTab === "overview" && (
            <div>
              {/* Asset Identity Card */}
              <div className="analysis-overview-grid">
                <div className="analysis-summary-card">
                  <span className="card-label">ASSET DETAILS</span>
                  <div style={{ fontSize: "16px", fontWeight: 700, margin: "6px 0 2px" }}>
                    {selectedMedia.originalFilename}
                  </div>
                  <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                    Type: {selectedMedia.mediaType} · MIME: {selectedMedia.mimeType}
                  </p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">CRYPTOGRAPHIC SHA-256</span>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", margin: "6px 0" }}>
                    <code style={{ fontSize: "12px", fontFamily: "monospace", color: "var(--text)" }}>
                      {selectedMedia.sha256Hash?.substring(0, 16)}...
                    </code>
                    <button
                      onClick={() => handleCopySha256(selectedMedia.sha256Hash)}
                      className="icon-button"
                      title="Copy SHA-256"
                      style={{ padding: "4px", border: "none", background: "none", cursor: "pointer", color: copiedSha ? "var(--success)" : "var(--text-muted)" }}
                    >
                      {copiedSha ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  </div>
                  <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                    Quarantine Status: {selectedMedia.uploadStatus}
                  </p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">CATALOG STATUS</span>
                  <div style={{ fontSize: "16px", fontWeight: 750, margin: "6px 0", color: duplicates.length > 0 ? "var(--warning)" : "var(--success)" }}>
                    {duplicates.length > 0 ? `${duplicates.length} Duplicate Match Found` : "Unique Ingestion"}
                  </div>
                  <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                    Timestamp: {new Date(selectedMedia.createdAt).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Forensic Pipeline Available For This Media */}
              <section className="analysis-section" style={{ marginTop: "24px" }}>
                <div className="section-title-row">
                  <div>
                    <span className="card-label">PIPELINE INTEGRATION</span>
                    <h3>Active Forensic Modules for {selectedMedia.mediaType}</h3>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
                  <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                      <FingerprintIcon size={16} color="var(--primary)" />
                      <strong>M03 Fingerprint</strong>
                    </div>
                    <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                      Cryptographic and perceptual hash duplicate detection.
                    </p>
                  </div>

                  {(currentType === "IMAGE" || currentType === "VIDEO") && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                        <Camera size={16} color="var(--primary)" />
                        <strong>M04 EXIF Forensics</strong>
                      </div>
                      <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                        EXIF camera tags, GPS metadata, and anomaly integrity.
                      </p>
                    </div>
                  )}

                  {currentType === "IMAGE" && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                        <Sparkles size={16} color="var(--primary)" />
                        <strong>M05 Image Authenticity</strong>
                      </div>
                      <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                        PyTorch diffusion classifier, ELA and Grad-CAM heatmaps.
                      </p>
                    </div>
                  )}

                  {currentType === "VIDEO" && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                        <Film size={16} color="var(--primary)" />
                        <strong>M06 Video Deepfake</strong>
                      </div>
                      <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                        3D-CNN temporal inconsistency and suspicious intervals.
                      </p>
                    </div>
                  )}

                  {(currentType === "AUDIO" || currentType === "VIDEO") && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                        <Volume2 size={16} color="var(--primary)" />
                        <strong>M07 Audio Forensics</strong>
                      </div>
                      <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                        AASIST synthetic speech, pitch variance, and Mel-spectrogram.
                      </p>
                    </div>
                  )}

                  {currentType === "VIDEO" && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                        <Scan size={16} color="var(--primary)" />
                        <strong>M08 AV Sync</strong>
                      </div>
                      <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                        Lip-sync offset, SyncNet confidence, and desync intervals.
                      </p>
                    </div>
                  )}

                  <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                      <FileText size={16} color="var(--primary)" />
                      <strong>M11 Claims &amp; Entities</strong>
                    </div>
                    <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                      spaCy NER, SVO decomposition, and claim hashing.
                    </p>
                  </div>
                </div>
              </section>
            </div>
          )}

          {/* TAB 2: IMAGE AUTHENTICITY (MODULE 05) */}
          {activeTab === "image" && imageAnalysis && (
            <section className="analysis-section">
              <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <span className="card-label">MODULE 05 — IMAGE AUTHENTICITY</span>
                  <h3>Visual Forensics &amp; Explainable Heatmaps</h3>
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
                  <p>PyTorch ResNet Classifier</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">MANIPULATION PROBABILITY</span>
                  <strong className="analysis-number" style={{ color: imageAnalysis.manipulationProb > 0.5 ? "var(--danger)" : "var(--success)" }}>
                    {(imageAnalysis.manipulationProb * 100).toFixed(1)}%
                  </strong>
                  <p>Copy-Move &amp; Splicing Inconsistency</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">VERDICT &amp; STATUS</span>
                  <div style={{ fontSize: "16px", fontWeight: 750, margin: "6px 0", color: imageAnalysis.aiProb > 0.5 || imageAnalysis.manipulationProb > 0.5 ? "var(--danger)" : "var(--success)" }}>
                    {imageAnalysis.authenticityAssessment}
                  </div>
                  <p>Status: {imageAnalysis.analysisStatus}</p>
                </div>
              </div>

              {/* Explainable Heatmap Visualizers */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "20px" }}>
                <ForensicArtifactViewer
                  title="Error Level Analysis (ELA)"
                  description="Reveals localized compression differentials, highlighting spliced edges and inserted artifacts."
                  legend="Uniform dark noise indicates authentic compression. Bright distinct edges or blocks indicate digital tampering."
                  src={forensicsApi.getImageArtifactUrl(selectedMedia.id, "ela")}
                  alt="ELA Heatmap"
                />

                <ForensicArtifactViewer
                  title="Grad-CAM Neural Attention Heatmap"
                  description="Gradient-weighted Class Activation Mapping showing which spatial regions influenced the classifier's verdict."
                  legend="Warm colors (Yellow / Red) highlight neural network focus regions responsible for the authenticity prediction."
                  src={forensicsApi.getImageArtifactUrl(selectedMedia.id, "gradcam")}
                  alt="Grad-CAM Heatmap"
                />
              </div>

              {/* Physical Forensic Indicators */}
              <div style={{ marginTop: "24px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px" }}>
                <h4 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 700 }}>Physical Forensic Signals</h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
                  <div style={{ background: "var(--surface-soft)", padding: "12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 700 }}>FFT ANOMALY SCORE</div>
                    <div style={{ fontSize: "16px", fontWeight: 750, marginTop: "4px" }}>
                      {imageAnalysis.fftAnomalyScore !== null && imageAnalysis.fftAnomalyScore !== undefined
                        ? imageAnalysis.fftAnomalyScore.toFixed(3)
                        : "N/A"}
                    </div>
                  </div>

                  <div style={{ background: "var(--surface-soft)", padding: "12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 700 }}>NOISE VARIANCE</div>
                    <div style={{ fontSize: "16px", fontWeight: 750, marginTop: "4px" }}>
                      {imageAnalysis.noiseVariance !== null && imageAnalysis.noiseVariance !== undefined
                        ? imageAnalysis.noiseVariance.toFixed(1)
                        : "N/A"}
                    </div>
                  </div>

                  <div style={{ background: "var(--surface-soft)", padding: "12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 700 }}>COPY-MOVE DETECTED</div>
                    <div style={{ fontSize: "16px", fontWeight: 750, marginTop: "4px", color: imageAnalysis.copyMoveDetected ? "var(--danger)" : "var(--success)" }}>
                      {imageAnalysis.copyMoveDetected ? "POSITIVE" : "NEGATIVE"}
                    </div>
                  </div>

                  <div style={{ background: "var(--surface-soft)", padding: "12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 700 }}>SPLICING DETECTED</div>
                    <div style={{ fontSize: "16px", fontWeight: 750, marginTop: "4px", color: imageAnalysis.splicingDetected ? "var(--danger)" : "var(--success)" }}>
                      {imageAnalysis.splicingDetected ? "POSITIVE" : "NEGATIVE"}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* TAB 3: VIDEO DEEPFAKE (MODULE 06) */}
          {activeTab === "video" && videoAnalysis && (
            <section className="analysis-section">
              <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <span className="card-label">MODULE 06 — VIDEO DEEPFAKE DETECTION</span>
                  <h3>Temporal Face Inconsistency &amp; Deepfake Probability</h3>
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
                  <div style={{ fontSize: "18px", fontWeight: 800, margin: "6px 0" }}>
                    {videoAnalysis.face_count} Face Track(s) Detected
                  </div>
                  <p>{videoAnalysis.total_frames_sampled} frames sampled deterministically</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">ASSESSMENT</span>
                  <div style={{ fontSize: "16px", fontWeight: 750, margin: "6px 0" }}>
                    {videoAnalysis.authenticity_assessment}
                  </div>
                  <p>Status: {videoAnalysis.analysis_status}</p>
                </div>
              </div>

              {/* Sampled Frames Timeline */}
              {videoAnalysis.evidence?.frame_scores && videoAnalysis.evidence.frame_scores.length > 0 && (
                <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px", marginBottom: "20px" }}>
                  <h4 style={{ margin: "0 0 8px", fontSize: "15px", fontWeight: 700 }}>Sampled Frame Anomaly Timeline</h4>
                  <p style={{ margin: "0 0 16px", fontSize: "12px", color: "var(--text-secondary)" }}>
                    Per-frame deepfake scores evaluated along video duration. Higher bars indicate localized facial artifacts or blending seams.
                  </p>

                  <div style={{ display: "flex", alignItems: "flex-end", gap: "8px", height: "120px", background: "var(--surface-soft)", padding: "12px", borderRadius: "8px", overflowX: "auto" }}>
                    {videoAnalysis.evidence.frame_scores.map((frame, i) => {
                      const heightPercent = Math.min(100, Math.max(10, Math.round(frame.deepfake_score * 100)));
                      const isHighRisk = frame.deepfake_score > 0.5;
                      return (
                        <div
                          key={i}
                          title={`Frame #${frame.frame_index} (${frame.timestamp_seconds.toFixed(2)}s): Score ${(frame.deepfake_score * 100).toFixed(1)}%`}
                          style={{
                            flex: "1 0 20px",
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            height: "100%",
                            justifyContent: "flex-end",
                          }}
                        >
                          <div
                            style={{
                              width: "100%",
                              height: `${heightPercent}%`,
                              background: isHighRisk ? "var(--danger)" : "var(--primary)",
                              borderRadius: "4px 4px 0 0",
                              transition: "height 0.3s ease",
                            }}
                          />
                          <span style={{ fontSize: "9px", marginTop: "4px", color: "var(--text-muted)" }}>
                            {frame.timestamp_seconds.toFixed(1)}s
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Suspicious Timestamps Table */}
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                <h4 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 700 }}>Suspicious Temporal Markers</h4>
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
                          <td style={{ padding: "8px", color: "var(--danger)", fontWeight: 700 }}>{(t.anomaly_score * 100).toFixed(1)}%</td>
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
              <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <span className="card-label">MODULE 07 — AUDIO AUTHENTICITY &amp; VOICE FORENSICS</span>
                  <h3>Synthetic Speech &amp; Acoustic Forensics</h3>
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
                  <span className="card-label">ACOUSTIC INTEGRITY</span>
                  <div style={{ fontSize: "14px", margin: "8px 0" }}>
                    <div>Pitch Variance: <strong>{audioAnalysis.pitch_variance.toFixed(2)}</strong></div>
                    <div style={{ marginTop: "4px" }}>Phase Discontinuity: <strong>{audioAnalysis.phase_discontinuity.toFixed(2)}</strong></div>
                  </div>
                  <p>STFT &amp; Fundamental Frequency (YIN)</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">ASSESSMENT</span>
                  <div style={{ fontSize: "16px", fontWeight: 750, margin: "6px 0" }}>
                    {audioAnalysis.authenticity_assessment}
                  </div>
                  <p>Detected Splice Markers: {audioAnalysis.splice_markers?.length || 0}</p>
                </div>
              </div>

              {/* 80-Band Mel-Spectrogram Card */}
              {audioAnalysis.spectrogram_base64 && (
                <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px", marginBottom: "20px" }}>
                  <h4 style={{ margin: "0 0 8px", fontSize: "15px", fontWeight: 700 }}>80-Band Mel-Spectrogram</h4>
                  <p style={{ margin: "0 0 14px", fontSize: "12px", color: "var(--text-secondary)" }}>
                    Time-frequency acoustic representation highlighting spectral gaps, synthetic harmonics, and frequency cutoffs.
                  </p>
                  <div style={{ background: "#0f172a", borderRadius: "8px", overflow: "hidden", padding: "12px", display: "flex", justifyContent: "center" }}>
                    <img
                      src={`data:image/png;base64,${audioAnalysis.spectrogram_base64}`}
                      alt="Mel Spectrogram"
                      style={{ maxWidth: "100%", maxHeight: "280px", objectFit: "contain", borderRadius: "4px" }}
                    />
                  </div>
                </div>
              )}

              {/* Spectral Statistics Metrics Grid */}
              {audioAnalysis.evidence && (
                <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px" }}>
                  <h4 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 700 }}>Acoustic Evidence Features</h4>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
                    <div style={{ background: "var(--surface-soft)", padding: "12px", borderRadius: "8px" }}>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 700 }}>SPECTRAL CENTROID</div>
                      <div style={{ fontSize: "16px", fontWeight: 750, marginTop: "4px" }}>
                        {audioAnalysis.evidence.spectral_centroid_mean !== undefined ? `${audioAnalysis.evidence.spectral_centroid_mean.toFixed(1)} Hz` : "N/A"}
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-soft)", padding: "12px", borderRadius: "8px" }}>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 700 }}>SPECTRAL BANDWIDTH</div>
                      <div style={{ fontSize: "16px", fontWeight: 750, marginTop: "4px" }}>
                        {audioAnalysis.evidence.spectral_bandwidth_mean !== undefined ? `${audioAnalysis.evidence.spectral_bandwidth_mean.toFixed(1)} Hz` : "N/A"}
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-soft)", padding: "12px", borderRadius: "8px" }}>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 700 }}>ZERO CROSSING RATE</div>
                      <div style={{ fontSize: "16px", fontWeight: 750, marginTop: "4px" }}>
                        {audioAnalysis.evidence.zero_crossing_rate_mean !== undefined ? audioAnalysis.evidence.zero_crossing_rate_mean.toFixed(3) : "N/A"}
                      </div>
                    </div>

                    <div style={{ background: "var(--surface-soft)", padding: "12px", borderRadius: "8px" }}>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 700 }}>SPECTRAL ROLLOFF</div>
                      <div style={{ fontSize: "16px", fontWeight: 750, marginTop: "4px" }}>
                        {audioAnalysis.evidence.spectral_rolloff_mean !== undefined ? `${audioAnalysis.evidence.spectral_rolloff_mean.toFixed(1)} Hz` : "N/A"}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* TAB 5: AV SYNC (MODULE 08) */}
          {activeTab === "avsync" && avSyncAnalysis && (
            <section className="analysis-section">
              <div className="section-title-row">
                <div>
                  <span className="card-label">MODULE 08 — AUDIO-VIDEO SYNCHRONIZATION</span>
                  <h3>SyncNet Lip-Sync Consistency &amp; Dubbing Detection</h3>
                </div>
              </div>

              <div className="analysis-overview-grid" style={{ marginBottom: "24px" }}>
                <div className="analysis-summary-card">
                  <span className="card-label">SYNC CONFIDENCE</span>
                  <strong className="analysis-number" style={{ color: avSyncAnalysis.confidence > 0.7 ? "var(--success)" : "var(--warning)" }}>
                    {(avSyncAnalysis.confidence * 100).toFixed(1)}%
                  </strong>
                  <p>SyncNet Lip Correlation</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">LIP OFFSET</span>
                  <div style={{ fontSize: "20px", fontWeight: 800, margin: "6px 0" }}>
                    {avSyncAnalysis.lipOffsetMs.toFixed(1)} ms
                  </div>
                  <p>Temporal Speech-to-Mouth Shift</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">ASSESSMENT</span>
                  <div style={{ fontSize: "16px", fontWeight: 750, margin: "6px 0", color: avSyncAnalysis.syncScore === 0 ? "var(--warning)" : "var(--success)" }}>
                    {avSyncAnalysis.assessment}
                  </div>
                  <p>Status: {avSyncAnalysis.analysisStatus}</p>
                </div>
              </div>

              {/* Mismatch Segments */}
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                <h4 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 700 }}>Audio-Visual Mismatch Intervals</h4>
                {avSyncAnalysis.mismatchSegments && avSyncAnalysis.mismatchSegments.length > 0 ? (
                  <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--text-secondary)" }}>
                        <th style={{ padding: "8px" }}>Interval</th>
                        <th style={{ padding: "8px" }}>Offset (ms)</th>
                        <th style={{ padding: "8px" }}>Confidence</th>
                        <th style={{ padding: "8px" }}>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {avSyncAnalysis.mismatchSegments.map((s, idx) => {
                        const start = s.start_time !== undefined ? s.start_time : s.start_seconds || 0;
                        const end = s.end_time !== undefined ? s.end_time : s.end_seconds || 0;
                        const offset = s.offset_ms !== undefined ? s.offset_ms : s.drift_ms || 0;
                        return (
                          <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                            <td style={{ padding: "8px", fontWeight: 600 }}>{start.toFixed(2)}s – {end.toFixed(2)}s</td>
                            <td style={{ padding: "8px" }}>{offset.toFixed(1)}ms</td>
                            <td style={{ padding: "8px", fontWeight: 600 }}>{(s.confidence * 100).toFixed(0)}%</td>
                            <td style={{ padding: "8px", color: "var(--text-secondary)" }}>{s.reason || "Lip envelope desynchronization"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted)" }}>
                    No significant audio-visual synchronization mismatches detected.
                  </p>
                )}
              </div>
            </section>
          )}

          {/* TAB 6: OCR (MODULE 09) */}
          {activeTab === "ocr" && ocrResult && (
            <section className="analysis-section">
              <div className="section-title-row">
                <div>
                  <span className="card-label">MODULE 09 — OCR VISUAL TEXT EXTRACTION</span>
                  <h3>Embedded Visual Text &amp; Bounding Boxes</h3>
                </div>
              </div>

              <div className="analysis-overview-grid" style={{ marginBottom: "20px" }}>
                <div className="analysis-summary-card">
                  <span className="card-label">CONFIDENCE SCORE</span>
                  <strong className="analysis-number" style={{ color: "var(--primary)" }}>
                    {(ocrResult.confidenceScore * 100).toFixed(1)}%
                  </strong>
                  <p>OCR Recognition Confidence</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">REGIONS EXTRACTED</span>
                  <div style={{ fontSize: "20px", fontWeight: 800, margin: "6px 0" }}>
                    {ocrResult.regionsCount} Text Region(s)
                  </div>
                  <p>Language: {ocrResult.language?.toUpperCase() || "EN"}</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">EXTRACTION ENGINE</span>
                  <div style={{ fontSize: "15px", fontWeight: 700, margin: "6px 0" }}>
                    {ocrResult.evidence?.engine_used || "OCR Engine"}
                  </div>
                  <p>Status: {ocrResult.analysisStatus}</p>
                </div>
              </div>

              {/* Full Extracted Text Card */}
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px", marginBottom: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h4 style={{ margin: 0, fontSize: "15px", fontWeight: 700 }}>Extracted Text Body</h4>
                  <button
                    onClick={() => handleCopyText(ocrResult.extractedText || "")}
                    className="icon-button"
                    style={{ fontSize: "12px", display: "inline-flex", alignItems: "center", gap: "6px", padding: "5px 10px" }}
                  >
                    {copiedText ? <Check size={14} color="var(--success)" /> : <Copy size={14} />}
                    <span>{copiedText ? "Copied!" : "Copy Text"}</span>
                  </button>
                </div>
                <div style={{ background: "var(--surface-soft)", padding: "14px", borderRadius: "8px", fontSize: "14px", whiteSpace: "pre-wrap", fontFamily: "inherit", lineHeight: 1.6 }}>
                  {ocrResult.extractedText || "No embedded visual text detected in this asset."}
                </div>
              </div>

              {/* Bounding Boxes Table */}
              {ocrResult.regions && ocrResult.regions.length > 0 && (
                <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                  <h4 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 700 }}>Detected Spatial Regions</h4>
                  <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--text-secondary)" }}>
                        <th style={{ padding: "8px" }}>Region Text</th>
                        <th style={{ padding: "8px" }}>Confidence</th>
                        <th style={{ padding: "8px" }}>Coordinates [X, Y, W, H]</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ocrResult.regions.map((reg, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "8px", fontWeight: 600 }}>{reg.text}</td>
                          <td style={{ padding: "8px" }}>{(reg.confidence * 100).toFixed(1)}%</td>
                          <td style={{ padding: "8px", fontFamily: "monospace", color: "var(--text-secondary)" }}>
                            {reg.bounding_box ? `[${reg.bounding_box.x}, ${reg.bounding_box.y}, ${reg.bounding_box.width}, ${reg.bounding_box.height}]` : "N/A"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}

          {/* TAB 7: TRANSCRIPT (MODULE 10) */}
          {activeTab === "transcript" && transcript && (
            <section className="analysis-section">
              <div className="section-title-row">
                <div>
                  <span className="card-label">MODULE 10 — SPEECH-TO-TEXT TRANSCRIPT</span>
                  <h3>Faster-Whisper Timestamped Speech Recognition</h3>
                </div>
              </div>

              <div className="analysis-overview-grid" style={{ marginBottom: "20px" }}>
                <div className="analysis-summary-card">
                  <span className="card-label">TRANSCRIPTION CONFIDENCE</span>
                  <strong className="analysis-number" style={{ color: "var(--primary)" }}>
                    {(transcript.confidenceScore * 100).toFixed(1)}%
                  </strong>
                  <p>Faster-Whisper ASR</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">SEGMENTS &amp; WORDS</span>
                  <div style={{ fontSize: "18px", fontWeight: 800, margin: "6px 0" }}>
                    {transcript.segmentsCount} Segments · {transcript.wordsCount} Words
                  </div>
                  <p>Duration: {transcript.durationSeconds.toFixed(1)}s</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">LANGUAGE</span>
                  <div style={{ fontSize: "16px", fontWeight: 750, margin: "6px 0" }}>
                    {transcript.language?.toUpperCase() || "EN"}
                  </div>
                  <p>Status: {transcript.analysisStatus}</p>
                </div>
              </div>

              {/* Timestamped Segments Interactive List */}
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                  <h4 style={{ margin: 0, fontSize: "15px", fontWeight: 700 }}>Interactive Spoken Segments</h4>
                  <button
                    onClick={() => handleCopyText(transcript.fullText || "")}
                    className="icon-button"
                    style={{ fontSize: "12px", display: "inline-flex", alignItems: "center", gap: "6px", padding: "5px 10px" }}
                  >
                    {copiedText ? <Check size={14} color="var(--success)" /> : <Copy size={14} />}
                    <span>{copiedText ? "Copied!" : "Copy Full Transcript"}</span>
                  </button>
                </div>

                {transcript.segments && transcript.segments.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {transcript.segments.map((seg, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: "flex",
                          gap: "14px",
                          padding: "12px 16px",
                          borderRadius: "8px",
                          background: "var(--surface-soft)",
                          alignItems: "flex-start",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: "monospace",
                            fontSize: "12px",
                            fontWeight: 700,
                            color: "var(--primary)",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            background: "var(--primary-soft)",
                            flexShrink: 0,
                          }}
                        >
                          {(seg.start ?? seg.start_seconds ?? 0).toFixed(2)}s – {(seg.end ?? seg.end_seconds ?? 0).toFixed(2)}s
                        </span>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: "14px", lineHeight: 1.5 }}>{seg.text}</div>
                          {seg.words && seg.words.length > 0 && (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
                              {seg.words.map((w, wIdx) => {
                                const wStart = w.start ?? w.start_seconds ?? 0;
                                const wEnd = w.end ?? w.end_seconds ?? 0;
                                const wProb = w.probability ?? w.confidence ?? 0;
                                return (
                                  <span
                                    key={wIdx}
                                    style={{
                                      fontSize: "10px",
                                      padding: "2px 6px",
                                      borderRadius: "4px",
                                      background: "var(--surface)",
                                      border: "1px solid var(--border)",
                                      color: "var(--text-secondary)",
                                    }}
                                    title={`Timing: ${wStart.toFixed(2)}s - ${wEnd.toFixed(2)}s · Prob: ${(wProb * 100).toFixed(0)}%`}
                                  >
                                    {w.word}
                                  </span>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted)" }}>
                    No speech audio segments transcribed in this asset.
                  </p>
                )}
              </div>
            </section>
          )}

          {/* TAB 8: FINGERPRINT (MODULE 03) */}
          {activeTab === "fingerprint" && (
            <section className="analysis-section">
              <div className="section-title-row">
                <div>
                  <span className="card-label">MODULE 03 — FINGERPRINTING &amp; DUPLICATE DETECTION</span>
                  <h3>Cryptographic Identity &amp; Cross-Catalog Matching</h3>
                </div>
              </div>

              <div className="analysis-overview-grid" style={{ marginBottom: "20px" }}>
                <div className="analysis-summary-card">
                  <span className="card-label">CRYPTOGRAPHIC SHA-256</span>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", margin: "8px 0" }}>
                    <code style={{ fontSize: "12px", fontFamily: "monospace", color: "var(--text)" }}>
                      {selectedMedia.sha256Hash?.substring(0, 20)}...
                    </code>
                    <button
                      onClick={() => handleCopySha256(selectedMedia.sha256Hash)}
                      className="icon-button"
                      title="Copy SHA-256"
                      style={{ padding: "4px", border: "none", background: "none", cursor: "pointer", color: copiedSha ? "var(--success)" : "var(--text-muted)" }}
                    >
                      {copiedSha ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  </div>
                  <p>Collision-resistant cryptographic checksum</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">PERCEPTUAL HASH (pHash)</span>
                  <div style={{ fontSize: "14px", fontFamily: "monospace", fontWeight: 700, margin: "8px 0" }}>
                    {fingerprint?.perceptualHash || "Available upon full catalog pass"}
                  </div>
                  <p>Resistant to resizing, compression &amp; watermarks</p>
                </div>

                <div className="analysis-summary-card">
                  <span className="card-label">DUPLICATE STATUS</span>
                  <div style={{ fontSize: "16px", fontWeight: 750, margin: "8px 0", color: duplicates.length > 0 ? "var(--warning)" : "var(--success)" }}>
                    {duplicates.length > 0 ? "Duplicate Match Detected" : "No Catalog Duplicates"}
                  </div>
                  <p>{duplicates.length} matching asset(s) in catalog</p>
                </div>
              </div>

              {/* Duplicate Matches Table */}
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                <h4 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 700 }}>Duplicate Matching Catalog</h4>
                {duplicates && duplicates.length > 0 ? (
                  <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--text-secondary)" }}>
                        <th style={{ padding: "8px" }}>Matched Media ID</th>
                        <th style={{ padding: "8px" }}>Match Type</th>
                        <th style={{ padding: "8px" }}>Similarity Score</th>
                        <th style={{ padding: "8px" }}>Matched Asset Name</th>
                      </tr>
                    </thead>
                    <tbody>
                      {duplicates.map((d, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "8px", fontFamily: "monospace" }}>{d.matchedMediaId}</td>
                          <td style={{ padding: "8px" }}>
                            <span style={{ fontSize: "11px", fontWeight: 700, padding: "3px 8px", borderRadius: "4px", background: "var(--warning-soft)", color: "var(--warning)" }}>
                              {d.matchType}
                            </span>
                          </td>
                          <td style={{ padding: "8px", fontWeight: 700 }}>{(d.similarityScore * 100).toFixed(1)}%</td>
                          <td style={{ padding: "8px" }}>{d.originalFilename || "Prior Evidence Asset"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted)" }}>
                    No exact or perceptual duplicate collisions identified in the TruthLens evidence catalog.
                  </p>
                )}
              </div>
            </section>
          )}

          {/* TAB 9: METADATA FORENSICS (MODULE 04) */}
          {activeTab === "metadata" && (
            <section className="analysis-section">
              <div className="section-title-row">
                <div>
                  <span className="card-label">MODULE 04 — METADATA FORENSICS</span>
                  <h3>Camera Make, Model, Timestamps &amp; Tampering Anomalies</h3>
                </div>
              </div>

              {metadata ? (
                <div>
                  <div className="analysis-overview-grid" style={{ marginBottom: "20px" }}>
                    <div className="analysis-summary-card">
                      <span className="card-label">HARDWARE IDENTITY</span>
                      <div style={{ fontSize: "16px", fontWeight: 700, margin: "6px 0" }}>
                        {metadata.cameraMake || "Unknown Manufacturer"} {metadata.cameraModel || ""}
                      </div>
                      <p>Lens: {metadata.lensModel || "Standard optical assembly"}</p>
                    </div>

                    <div className="analysis-summary-card">
                      <span className="card-label">TIMESTAMP TAGS</span>
                      <div style={{ fontSize: "14px", fontWeight: 600, margin: "6px 0" }}>
                        {metadata.capturedAt || metadata.dateTimeOriginal || "No capture timestamp"}
                      </div>
                      <p>Software: {metadata.software || metadata.softwareTag || "Camera Firmware (Untampered)"}</p>
                    </div>

                    <div className="analysis-summary-card">
                      <span className="card-label">INTEGRITY &amp; ANOMALIES</span>
                      <div style={{ fontSize: "18px", fontWeight: 800, margin: "6px 0", color: (metadata.anomalyCount || metadata.anomaliesCount || 0) > 0 ? "var(--warning)" : "var(--success)" }}>
                        {metadata.anomalyCount || metadata.anomaliesCount || 0} Anomaly(s)
                      </div>
                      <p>Forensic Integrity Score: {metadata.forensicScore.toFixed(2)}</p>
                    </div>
                  </div>

                  {/* Structured Forensic Metadata Grid */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginBottom: "20px" }}>
                    {/* Camera Card */}
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                        <Camera size={16} color="var(--primary)" />
                        <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700 }}>Camera &amp; Optics</h4>
                      </div>
                      <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "6px" }}>
                        <div><strong>Make:</strong> {metadata.cameraMake || <span style={{ color: "var(--text-muted)" }}>Missing</span>}</div>
                        <div><strong>Model:</strong> {metadata.cameraModel || <span style={{ color: "var(--text-muted)" }}>Missing</span>}</div>
                        <div><strong>Lens:</strong> {metadata.lensModel || <span style={{ color: "var(--text-muted)" }}>Missing</span>}</div>
                      </div>
                    </div>

                    {/* Geolocation Card */}
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                        <MapPin size={16} color="var(--primary)" />
                        <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700 }}>Geospatial Location</h4>
                      </div>
                      <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "6px" }}>
                        {metadata.gpsLatitude !== null && metadata.gpsLatitude !== undefined && metadata.gpsLongitude !== null && metadata.gpsLongitude !== undefined ? (
                          <>
                            <div><strong>Latitude:</strong> {metadata.gpsLatitude.toFixed(6)}°</div>
                            <div><strong>Longitude:</strong> {metadata.gpsLongitude.toFixed(6)}°</div>
                            <div><strong>Altitude:</strong> {metadata.gpsAltitude !== null && metadata.gpsAltitude !== undefined ? `${metadata.gpsAltitude.toFixed(1)}m` : "N/A"}</div>
                          </>
                        ) : (
                          <div style={{ color: "var(--text-muted)" }}>
                            Not Geotagged — No embedded GPS coordinates in container EXIF.
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Technical & Container */}
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                        <Cpu size={16} color="var(--primary)" />
                        <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700 }}>Technical Container</h4>
                      </div>
                      <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "6px" }}>
                        <div><strong>Dimensions:</strong> {metadata.width && metadata.height ? `${metadata.width} × ${metadata.height} px` : "Recorded in file header"}</div>
                        <div><strong>Format / Codec:</strong> {metadata.containerFormat || metadata.videoCodec || selectedMedia.mimeType}</div>
                        <div><strong>Engine:</strong> {metadata.extractionEngine || "Composite Metadata Engine"}</div>
                      </div>
                    </div>
                  </div>

                  {/* Detected Metadata Anomalies */}
                  {metadata.anomalies && metadata.anomalies.length > 0 && (
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "18px" }}>
                      <h4 style={{ margin: "0 0 12px", fontSize: "15px", fontWeight: 700 }}>Detected Tampering &amp; Metadata Anomalies</h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {metadata.anomalies.map((a, i) => (
                          <div key={i} style={{ padding: "10px 14px", borderRadius: "6px", background: "var(--warning-soft)", color: "var(--warning)", fontSize: "13px" }}>
                            <strong>[{a.severity || "WARNING"}] {a.title || a.anomalyType || a.ruleId}:</strong> {a.description}
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

          {/* TAB 10: CLAIMS & NLP ENTITIES (MODULE 11) */}
          {activeTab === "claims" && (
            <section className="analysis-section" style={{ padding: 0, background: "transparent", border: "none" }}>
              <ClaimList
                mediaId={selectedMedia.id}
                initialData={claimsData}
                isLoading={tabLoading}
                onReanalyze={async (source) => {
                  const res = await forensicsApi.reanalyzeClaims(selectedMedia.id, source);
                  setClaimsData(res);
                }}
                onAnalyzeDirectText={async (text) => {
                  return await forensicsApi.extractDirectClaims(text);
                }}
              />
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default Analysis;