import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import type { MediaFile, MediaType } from "../types/media";

function Upload() {
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<MediaFile | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = (selectedFile: File) => {
    const type = getMediaType(selectedFile);

    if (!type) {
      alert("Please upload an image, video, or audio file.");
      return;
    }

    setFile({
      id: `MEDIA-${Date.now()}`,
      name: selectedFile.name,
      type,
      size: selectedFile.size,
      status: "ready",
    });
  };

  const handleInputChange = (
    event: ChangeEvent<HTMLInputElement>,
  ) => {
    const selectedFile = event.target.files?.[0];

    if (selectedFile) {
      handleFile(selectedFile);
    }
  };

  const handleDrop = (
    event: DragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault();

    setIsDragging(false);

    const droppedFile = event.dataTransfer.files?.[0];

    if (droppedFile) {
      handleFile(droppedFile);
    }
  };

  const removeFile = () => {
    setFile(null);

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const startAnalysis = () => {
    if (!file) return;

    setFile({
      ...file,
      status: "uploading",
    });

    setTimeout(() => {
      setFile((current) =>
        current
          ? {
              ...current,
              status: "uploaded",
            }
          : null,
      );
    }, 1200);
  };

  return (
    <div className="upload-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            MEDIA INGESTION
          </span>

          <h2>Start an Investigation</h2>

          <p>
            Upload evidence and send it through the
            TruthLens analysis pipeline.
          </p>
        </div>
      </div>

      <section
        className={`upload-zone ${
          isDragging ? "dragging" : ""
        }`}
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
          accept="image/*,video/*,audio/*"
          onChange={handleInputChange}
        />

        <div className="upload-icon">↑</div>

        <h3>
          Drop your evidence here
        </h3>

        <p>
          or click to browse from your computer
        </p>

        <span className="upload-formats">
          IMAGE · VIDEO · AUDIO
        </span>
      </section>

      {file && (
        <section className="selected-file">
          <div>
            <span className="card-label">
              SELECTED MEDIA
            </span>

            <h3>{file.name}</h3>

            <div className="file-meta">
              <span>{file.type.toUpperCase()}</span>
              <span>{formatFileSize(file.size)}</span>
              <span>{file.status.toUpperCase()}</span>
            </div>
          </div>

          <button
            className="remove-button"
            onClick={removeFile}
          >
            Remove
          </button>
        </section>
      )}

      <section className="upload-info-grid">
        <div className="upload-info-card">
          <span className="info-number">01</span>

          <div>
            <h3>Upload</h3>
            <p>
              Select the media you want TruthLens to
              investigate.
            </p>
          </div>
        </div>

        <div className="upload-info-card">
          <span className="info-number">02</span>

          <div>
            <h3>Analyze</h3>
            <p>
              The analysis pipeline examines available
              forensic signals.
            </p>
          </div>
        </div>

        <div className="upload-info-card">
          <span className="info-number">03</span>

          <div>
            <h3>Investigate</h3>
            <p>
              Review the results and create a case when
              further investigation is required.
            </p>
          </div>
        </div>
      </section>

      {file && (
        <div className="upload-action">
          <button
            className="primary-button"
            onClick={startAnalysis}
            disabled={
              file.status === "uploading" ||
              file.status === "uploaded"
            }
          >
            {file.status === "ready" &&
              "Start Analysis →"}

            {file.status === "uploading" &&
              "Uploading..."}

            {file.status === "uploaded" &&
              "Analysis Started ✓"}
          </button>
        </div>
      )}
    </div>
  );
}

function getMediaType(
  file: File,
): MediaType | null {
  if (file.type.startsWith("image/")) {
    return "image";
  }

  if (file.type.startsWith("video/")) {
    return "video";
  }

  if (file.type.startsWith("audio/")) {
    return "audio";
  }

  return null;
}

function formatFileSize(size: number) {
  if (size < 1024 * 1024) {
    return `${Math.round(size / 1024)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export default Upload;