import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { mediaApi } from "../services/api";
import type { MediaUploadResponse } from "../types/media";
import { UploadCloud, CheckCircle2, AlertCircle, ArrowRight, FileCheck } from "lucide-react";

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

function Upload() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const [rawFile, setRawFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<MediaUploadResponse | null>(null);

  const validateAndSetFile = (file: File) => {
    setError(null);
    setUploadResult(null);

    if (file.size > MAX_FILE_SIZE) {
      setError(`File size (${formatFileSize(file.size)}) exceeds the maximum allowed limit of 100 MB.`);
      return;
    }

    const isImage = file.type.startsWith("image/");
    const isVideo = file.type.startsWith("video/");
    const isAudio = file.type.startsWith("audio/");
    const isText = file.type === "text/plain" || file.name.endsWith(".txt");

    if (!isImage && !isVideo && !isAudio && !isText) {
      setError(`Unsupported file type: '${file.type || file.name}'. Allowed: Images, Videos, Audio, and Text files.`);
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
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const handleUploadAndAnalyze = async () => {
    if (!rawFile) return;

    try {
      setIsUploading(true);
      setError(null);

      const response = await mediaApi.upload(rawFile);
      setUploadResult(response);

      // Transition to analysis workspace for this specific media ID
      setTimeout(() => {
        navigate(`/analysis?id=${response.id}`);
      }, 1200);
    } catch (err: any) {
      setError(err?.message || "Failed to upload media. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">MEDIA INGESTION</span>
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
            gap: "10px",
            background: "var(--danger-soft)",
            color: "var(--danger)",
            padding: "14px 18px",
            borderRadius: "10px",
            fontSize: "14px",
            marginBottom: "20px",
          }}
        >
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {uploadResult && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            background: "var(--success-soft)",
            color: "var(--success)",
            padding: "16px 20px",
            borderRadius: "10px",
            fontSize: "14px",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", fontWeight: 700 }}>
            <CheckCircle2 size={18} />
            <span>{uploadResult.message || "File uploaded and quarantined successfully!"}</span>
          </div>
          <div style={{ fontSize: "12px", opacity: 0.9, fontFamily: "monospace" }}>
            ID: {uploadResult.id} · SHA-256: {uploadResult.sha256Hash?.substring(0, 16)}...
          </div>
          <div style={{ fontSize: "13px", fontWeight: 600, marginTop: "4px" }}>
            Redirecting to Analysis Workspace...
          </div>
        </div>
      )}

      <section
        className={`upload-zone ${isDragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          hidden
          accept="image/*,video/*,audio/*,text/plain"
          onChange={handleInputChange}
        />

        <div className="upload-icon" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <UploadCloud size={28} />
        </div>

        <h3>Drop your evidence here</h3>
        <p>or click to browse from your computer</p>

        <span className="upload-formats">
          IMAGE · VIDEO · AUDIO · TEXT (MAX 100MB)
        </span>
      </section>

      {rawFile && (
        <section className="selected-file">
          <div>
            <span className="card-label">SELECTED EVIDENCE</span>
            <h3>{rawFile.name}</h3>

            <div className="file-meta">
              <span>{rawFile.type || "UNKNOWN TYPE"}</span>
              <span>{formatFileSize(rawFile.size)}</span>
              <span>{isUploading ? "UPLOADING..." : uploadResult ? "QUARANTINED" : "READY"}</span>
            </div>
          </div>

          <button
            className="remove-button"
            onClick={removeFile}
            disabled={isUploading}
          >
            Remove
          </button>
        </section>
      )}

      <section className="upload-info-grid">
        <div className="upload-info-card">
          <span className="info-number">01</span>
          <div>
            <h3>Secure Quarantine</h3>
            <p>Files are validated via magic-bytes, hashed with SHA-256, and isolated in quarantined storage.</p>
          </div>
        </div>

        <div className="upload-info-card">
          <span className="info-number">02</span>
          <div>
            <h3>Forensic Pipeline</h3>
            <p>Dispatched through PyTorch deepfake classifiers, ELA, AASIST, OCR, Whisper, and claim extraction.</p>
          </div>
        </div>

        <div className="upload-info-card">
          <span className="info-number">03</span>
          <div>
            <h3>Investigate & Report</h3>
            <p>Review explainable heatmaps, suspicious timestamps, speech transcripts, and verifiable claims.</p>
          </div>
        </div>
      </section>

      {rawFile && (
        <div className="upload-action">
          <button
            className="primary-button"
            onClick={handleUploadAndAnalyze}
            disabled={isUploading || !!uploadResult}
            style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
          >
            {isUploading ? (
              <>
                <span className="status-pulse" />
                <span>Uploading to Backend Quarantine...</span>
              </>
            ) : uploadResult ? (
              <>
                <FileCheck size={16} />
                <span>Uploaded Successfully!</span>
              </>
            ) : (
              <>
                <span>Start Multi-Modal Analysis</span>
                <ArrowRight size={16} />
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