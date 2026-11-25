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
  Music,
  Image as ImageIcon,
  FileCheck,
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

  useEffect(() => {
    if (!rawFile) {
      setPreviewUrl(null);
      return;
    }

    if (rawFile.type.startsWith("image/")) {
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
      setError(`File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the maximum allowed limit of 100 MB.`);
      return;
    }

    const isImage = file.type.startsWith("image/");
    const lowerName = file.name.toLowerCase();
    const isSupportedAudioExt =
      lowerName.endsWith(".wav") ||
      lowerName.endsWith(".flac") ||
      lowerName.endsWith(".ogg") ||
      lowerName.endsWith(".mp3");
    const isAudio = file.type.startsWith("audio/") || isSupportedAudioExt;

    if (!isImage && !isAudio) {
      setError(`Unsupported file format. Supported categories: Images (PNG, JPG, WebP) and Audio (WAV, FLAC, OGG, MP3).`);
      return;
    }

    if (isAudio && !isSupportedAudioExt && !["audio/wav", "audio/x-wav", "audio/wave", "audio/flac", "audio/x-flac", "audio/ogg", "audio/mpeg", "audio/mp3"].includes(file.type.toLowerCase())) {
      setError(`Unsupported audio format. Supported audio formats: WAV, FLAC, OGG, and MP3.`);
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
      setUploadProgress(25);

      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => (prev < 85 ? prev + 15 : prev));
      }, 150);

      const response = await mediaApi.upload(rawFile);
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadResult(response);
    } catch (err: any) {
      setError(err?.message || "Failed to upload file. Please check backend service connectivity.");
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const isImage = rawFile?.type.startsWith("image/");
  const isAudio = rawFile?.type.startsWith("audio/");

  return (
    <div className="upload-page" style={{ maxWidth: "800px", margin: "0 auto", paddingBottom: "40px" }}>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "32px" }}>
        <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "1.2px", color: "var(--primary)", textTransform: "uppercase" }}>
          Media Ingestion
        </span>
        <h2 style={{ fontSize: "28px", fontWeight: 700, margin: "6px 0 8px", color: "var(--text)", letterSpacing: "-0.5px" }}>
          Upload & Inspect Evidence
        </h2>
        <p style={{ margin: 0, fontSize: "14px", color: "var(--text-secondary)", maxWidth: "520px", marginLeft: "auto", marginRight: "auto", lineHeight: 1.5 }}>
          Upload image or audio evidence into secure quarantine storage for automated authenticity analysis.
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "14px 18px",
            background: "var(--danger-soft)",
            border: "1px solid #fecaca",
            borderRadius: "10px",
            color: "var(--danger)",
            fontSize: "13px",
            marginBottom: "20px",
          }}
        >
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {/* Success Alert */}
      {uploadResult && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "14px",
            padding: "16px 20px",
            background: "var(--success-soft)",
            border: "1px solid #bbf7d0",
            borderRadius: "12px",
            color: "var(--success)",
            fontSize: "14px",
            marginBottom: "24px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <CheckCircle2 size={20} style={{ flexShrink: 0 }} />
            <div>
              <strong style={{ display: "block" }}>Upload Complete</strong>
              <small style={{ color: "var(--text-secondary)", fontSize: "12px" }}>
                File successfully ingested and quarantined.
              </small>
            </div>
          </div>

          <button
            onClick={() => navigate(`/analysis?id=${uploadResult.id}`)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "9px 16px",
              borderRadius: "8px",
              background: "var(--success)",
              color: "#ffffff",
              border: "none",
              fontSize: "13px",
              fontWeight: 650,
              cursor: "pointer",
            }}
          >
            <span>View Analysis Results</span>
            <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: isDragging ? "2px dashed var(--primary)" : "2px dashed var(--border)",
          borderRadius: "16px",
          background: isDragging ? "var(--primary-soft)" : "var(--surface)",
          padding: "48px 24px",
          textAlign: "center",
          cursor: isUploading ? "not-allowed" : "pointer",
          transition: "all 0.15s ease",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.03)",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          hidden
          accept="image/*,.wav,.flac,.ogg,.mp3,audio/wav,audio/x-wav,audio/flac,audio/ogg,audio/mpeg"
          onChange={handleInputChange}
          disabled={isUploading}
        />

        <div
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "14px",
            background: "var(--primary-soft)",
            color: "var(--primary)",
            display: "grid",
            placeItems: "center",
            margin: "0 auto 16px",
          }}
        >
          <UploadCloud size={28} />
        </div>

        <h3 style={{ margin: "0 0 6px", fontSize: "17px", fontWeight: 700, color: "var(--text)" }}>
          {isDragging ? "Drop your file to ingest" : "Drag and drop your file here"}
        </h3>
        <p style={{ margin: "0 0 18px", fontSize: "13px", color: "var(--text-secondary)" }}>
          or <span style={{ color: "var(--primary)", fontWeight: 600 }}>browse files</span> from your computer
        </p>

        {/* Supported formats */}
        <div style={{ display: "flex", gap: "8px", justifyContent: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, padding: "4px 10px", borderRadius: "6px", background: "var(--surface-soft)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
            PNG, JPG, WebP
          </span>
          <span style={{ fontSize: "11px", fontWeight: 600, padding: "4px 10px", borderRadius: "6px", background: "var(--surface-soft)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
            WAV, MP3, FLAC
          </span>
          <span style={{ fontSize: "11px", fontWeight: 600, padding: "4px 10px", borderRadius: "6px", background: "var(--surface-soft)", color: "var(--text-muted)", border: "1px solid var(--border)" }}>
            Up to 100 MB
          </span>
        </div>
      </div>

      {/* Selected File Card */}
      {rawFile && (
        <div
          style={{
            marginTop: "20px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "14px",
            padding: "20px",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
              <div
                style={{
                  width: "52px",
                  height: "52px",
                  borderRadius: "10px",
                  background: "var(--surface-soft)",
                  border: "1px solid var(--border)",
                  overflow: "hidden",
                  display: "grid",
                  placeItems: "center",
                  flexShrink: 0,
                }}
              >
                {isImage && previewUrl ? (
                  <img src={previewUrl} alt="Preview" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : isAudio ? (
                  <Music size={24} style={{ color: "#f59e0b" }} />
                ) : (
                  <ImageIcon size={24} style={{ color: "var(--primary)" }} />
                )}
              </div>

              <div>
                <p style={{ margin: "0 0 2px", fontSize: "15px", fontWeight: 650, color: "var(--text)" }}>
                  {rawFile.name}
                </p>
                <small style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  {formatFileSize(rawFile.size)} &bull; {rawFile.type || "binary"}
                </small>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <button
                onClick={removeFile}
                disabled={isUploading}
                style={{
                  padding: "8px 12px",
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                  background: "var(--surface-soft)",
                  color: "var(--text-secondary)",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: isUploading ? "not-allowed" : "pointer",
                }}
              >
                Remove
              </button>

              <button
                onClick={handleUploadAndAnalyze}
                disabled={isUploading || !!uploadResult}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 18px",
                  borderRadius: "8px",
                  border: "none",
                  background: isUploading ? "var(--text-muted)" : "var(--primary)",
                  color: "#ffffff",
                  fontSize: "13px",
                  fontWeight: 650,
                  cursor: isUploading ? "not-allowed" : "pointer",
                  transition: "background 0.15s ease",
                }}
              >
                {isUploading ? (
                  <>
                    <div
                      style={{
                        width: "14px",
                        height: "14px",
                        border: "2px solid #ffffff",
                        borderTopColor: "transparent",
                        borderRadius: "50%",
                        animation: "spin 0.8s linear infinite",
                      }}
                    />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <FileCheck size={16} />
                    <span>Upload & Analyze</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Upload Progress Bar */}
          {isUploading && (
            <div style={{ marginTop: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                <span>Quarantining and sending to FastAPI Vision Microservice...</span>
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
        </div>
      )}
    </div>
  );
}

export default Upload;
