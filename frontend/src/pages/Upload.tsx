import { useRef, useState, useEffect } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { mediaApi } from "../services/api";
import type { MediaUploadResponse } from "../types/media";
import {
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  FileCheck,
  RotateCcw,
  FileText,
  Film,
  Music,
  Image as ImageIcon,
  Shield,
  Trash2,
} from "lucide-react";

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

export function Upload() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const [rawFile, setRawFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<MediaUploadResponse | null>(null);

  // Clean up object URLs on change/unmount
  useEffect(() => {
    if (!rawFile) {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);
      }
      return;
    }

    if (rawFile.type.startsWith("image/") || rawFile.type.startsWith("video/") || rawFile.type.startsWith("audio/")) {
      const url = URL.createObjectURL(rawFile);
      setPreviewUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    }
  }, [rawFile]);

  const validateAndSetFile = (file: File) => {
    setError(null);
    setUploadResult(null);
    setUploadProgress(0);

    if (file.size === 0) {
      setError("The selected file is empty (0 bytes). Please choose a valid media file.");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError(`File size (${formatFileSize(file.size)}) exceeds the maximum allowed limit of 100 MB.`);
      return;
    }

    const isImage = file.type.startsWith("image/");
    const isVideo = file.type.startsWith("video/");
    const isAudio = file.type.startsWith("audio/");
    const isText = file.type === "text/plain" || file.name.endsWith(".txt") || file.name.endsWith(".json") || file.name.endsWith(".csv");

    if (!isImage && !isVideo && !isAudio && !isText) {
      setError(`Unsupported file format: '${file.type || file.name}'. Supported categories: Images (PNG, JPG, WebP), Video (MP4, WebM, MOV), Audio (WAV, MP3, FLAC), and Text.`);
      return;
    }

    setRawFile(file);
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const droppedFile = event.dataTransfer.files?.[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  };

  const removeFile = () => {
    setRawFile(null);
    setError(null);
    setUploadResult(null);
    setUploadProgress(0);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const handleUploadAndAnalyze = async () => {
    if (!rawFile) return;

    try {
      setIsUploading(true);
      setError(null);
      setUploadProgress(30);

      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => (prev < 90 ? prev + 15 : prev));
      }, 150);

      const response = await mediaApi.upload(rawFile);
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadResult(response);

      // Transition smoothly to analysis workspace
      setTimeout(() => {
        navigate(`/analysis?id=${response.id}`);
      }, 1000);
    } catch (err: any) {
      setError(err?.message || "Failed to ingest media into quarantined storage. Please check connectivity or try a different file.");
      setUploadProgress(0);
    } finally {
      setIsUploading(false);
    }
  };

  const isImage = rawFile?.type.startsWith("image/");
  const isVideo = rawFile?.type.startsWith("video/");
  const isAudio = rawFile?.type.startsWith("audio/");
  const isText = rawFile?.type.startsWith("text/") || rawFile?.name.endsWith(".txt");

  return (
    <div className="upload-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">MEDIA INGESTION &amp; SECURITY</span>
          <h2>Start an Investigation</h2>
          <p>
            Upload evidence and send it through the TruthLens multi-modal analysis pipeline.
          </p>
        </div>
      </div>

      {error && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "10px",
            background: "var(--danger-soft)",
            color: "var(--danger)",
            padding: "14px 18px",
            borderRadius: "10px",
            fontSize: "14px",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
          <button
            onClick={handleUploadAndAnalyze}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              fontSize: "12px",
              fontWeight: 600,
              background: "var(--surface)",
              color: "var(--danger)",
              border: "1px solid var(--danger)",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            <RotateCcw size={13} />
            <span>Retry</span>
          </button>
        </div>
      )}

      {uploadResult && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            background: "var(--success-soft)",
            color: "var(--success)",
            padding: "18px 22px",
            borderRadius: "12px",
            fontSize: "14px",
            marginBottom: "20px",
            border: "1px solid rgba(33, 163, 102, 0.2)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", fontWeight: 750, fontSize: "15px" }}>
              <CheckCircle2 size={20} />
              <span>{uploadResult.message || "File uploaded and quarantined successfully!"}</span>
            </div>
            <button
              onClick={() => navigate(`/analysis?id=${uploadResult.id}`)}
              className="primary-button"
              style={{ fontSize: "12px", padding: "6px 14px", display: "inline-flex", alignItems: "center", gap: "6px" }}
            >
              <span>Go to Workspace</span>
              <ArrowRight size={14} />
            </button>
          </div>

          <div style={{ fontSize: "12px", opacity: 0.95, fontFamily: "monospace", display: "flex", flexWrap: "wrap", gap: "16px" }}>
            <span><strong>UUID:</strong> {uploadResult.id}</span>
            <span><strong>MIME:</strong> {uploadResult.mimeType}</span>
            <span><strong>SHA-256:</strong> {uploadResult.sha256Hash?.substring(0, 24)}...</span>
          </div>
        </div>
      )}

      {/* Drag & Drop Zone */}
      <section
        className={`upload-zone ${isDragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        style={{ cursor: isUploading ? "not-allowed" : "pointer" }}
      >
        <input
          ref={inputRef}
          type="file"
          hidden
          accept="image/*,video/*,audio/*,text/plain"
          onChange={handleInputChange}
          disabled={isUploading}
        />

        <div className="upload-icon" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <UploadCloud size={28} />
        </div>

        <h3 style={{ margin: "10px 0 4px", fontSize: "17px", fontWeight: 700 }}>
          {isDragging ? "Drop your file to ingest" : "Drop your evidence here"}
        </h3>
        <p style={{ margin: "0 0 12px", fontSize: "13px", color: "var(--text-secondary)" }}>
          or click to browse from your computer
        </p>

        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", justifyContent: "center", marginTop: "8px" }}>
          <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 8px", borderRadius: "6px", background: "var(--surface-soft)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
            PNG, JPG, WebP
          </span>
          <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 8px", borderRadius: "6px", background: "var(--surface-soft)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
            MP4, MOV, WebM
          </span>
          <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 8px", borderRadius: "6px", background: "var(--surface-soft)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
            WAV, MP3, FLAC
          </span>
          <span style={{ fontSize: "11px", fontWeight: 700, padding: "4px 8px", borderRadius: "6px", background: "var(--surface-soft)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
            Max 100MB
          </span>
        </div>
      </section>

      {/* Selected File Card with Media Preview */}
      {rawFile && (
        <section
          style={{
            marginTop: "20px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "14px",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
              {/* Thumbnail / Indicator */}
              <div
                style={{
                  width: "60px",
                  height: "60px",
                  borderRadius: "10px",
                  background: "var(--surface-soft)",
                  border: "1px solid var(--border)",
                  overflow: "hidden",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {isImage && previewUrl ? (
                  <img src={previewUrl} alt="Thumbnail preview" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : isVideo ? (
                  <Film size={26} color="var(--primary)" />
                ) : isAudio ? (
                  <Music size={26} color="var(--warning)" />
                ) : isText ? (
                  <FileText size={26} color="var(--success)" />
                ) : (
                  <ImageIcon size={26} color="var(--text-muted)" />
                )}
              </div>

              <div>
                <span className="card-label">READY FOR INGESTION</span>
                <h3 style={{ margin: "4px 0 6px", fontSize: "16px", fontWeight: 700 }}>{rawFile.name}</h3>

                <div style={{ display: "flex", gap: "10px", fontSize: "12px", color: "var(--text-secondary)" }}>
                  <span>{rawFile.type || "binary"}</span>
                  <span>•</span>
                  <span>{formatFileSize(rawFile.size)}</span>
                  <span>•</span>
                  <span style={{ fontWeight: 600, color: uploadResult ? "var(--success)" : isUploading ? "var(--primary)" : "var(--text)" }}>
                    {uploadResult ? "QUARANTINED" : isUploading ? "UPLOADING..." : "STAGED"}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={removeFile}
              disabled={isUploading}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid var(--border)",
                background: "var(--surface-soft)",
                color: "var(--danger)",
                fontSize: "12px",
                fontWeight: 600,
                cursor: isUploading ? "not-allowed" : "pointer",
              }}
            >
              <Trash2 size={13} />
              <span>Remove</span>
            </button>
          </div>

          {/* Media Interactive Preview if Audio/Video */}
          {isVideo && previewUrl && (
            <div style={{ marginTop: "6px", borderRadius: "8px", overflow: "hidden", background: "#000", maxWidth: "420px" }}>
              <video src={previewUrl} controls style={{ width: "100%", maxHeight: "200px", display: "block" }} />
            </div>
          )}

          {isAudio && previewUrl && (
            <div style={{ marginTop: "6px", maxWidth: "420px" }}>
              <audio src={previewUrl} controls style={{ width: "100%" }} />
            </div>
          )}

          {/* Upload Progress Bar */}
          {isUploading && (
            <div style={{ marginTop: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px", color: "var(--text-secondary)" }}>
                <span>Transferring to backend quarantine...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div style={{ width: "100%", height: "6px", background: "var(--surface-soft)", borderRadius: "3px", overflow: "hidden" }}>
                <div
                  style={{
                    width: `${uploadProgress}%`,
                    height: "100%",
                    background: "var(--primary)",
                    borderRadius: "3px",
                    transition: "width 0.2s ease",
                  }}
                />
              </div>
            </div>
          )}
        </section>
      )}

      {/* Informational Cards */}
      <section className="upload-info-grid">
        <div className="upload-info-card">
          <span className="info-number">01</span>
          <div>
            <h3>Secure Quarantine</h3>
            <p>Files are validated via Apache Tika magic-bytes, hashed with SHA-256, and stored in isolated quarantine.</p>
          </div>
        </div>

        <div className="upload-info-card">
          <span className="info-number">02</span>
          <div>
            <h3>Multi-Modal Forensics</h3>
            <p>Dispatched through PyTorch deepfake networks, ELA, Grad-CAM, AASIST voice forensics, OCR, and Faster-Whisper.</p>
          </div>
        </div>

        <div className="upload-info-card">
          <span className="info-number">03</span>
          <div>
            <h3>Explainable Evidence</h3>
            <p>Review spatial heatmaps, suspicious timestamps, speech transcripts, and verified claims with provenance hashes.</p>
          </div>
        </div>
      </section>

      {/* Action Button */}
      {rawFile && (
        <div className="upload-action" style={{ marginTop: "24px" }}>
          <button
            className="primary-button"
            onClick={handleUploadAndAnalyze}
            disabled={isUploading || !!uploadResult}
            style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontSize: "14px", padding: "12px 24px" }}
          >
            {isUploading ? (
              <>
                <span className="status-pulse" />
                <span>Ingesting into Quarantine ({uploadProgress}%)...</span>
              </>
            ) : uploadResult ? (
              <>
                <FileCheck size={18} />
                <span>Ingested Successfully!</span>
              </>
            ) : (
              <>
                <Shield size={18} />
                <span>Start Multi-Modal Investigation</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

function formatFileSize(size: number) {
  if (size < 1024 * 1024) {
    return `${Math.round(size / 1024)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export default Upload;