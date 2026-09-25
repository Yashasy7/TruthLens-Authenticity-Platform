import React, { useState } from 'react';
import { Eye, EyeOff, ZoomIn, ZoomOut, RotateCcw, AlertTriangle, Image as ImageIcon } from 'lucide-react';

interface ForensicArtifactViewerProps {
  title: string;
  description: string;
  legend: string;
  src: string;
  originalSrc?: string;
  alt: string;
}

export const ForensicArtifactViewer: React.FC<ForensicArtifactViewerProps> = ({
  title,
  description,
  legend,
  src,
  originalSrc,
  alt,
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isZoomed, setIsZoomed] = useState(false);
  const [showOriginal, setShowOriginal] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  const handleRetry = () => {
    setHasError(false);
    setIsLoading(true);
    setRetryKey((prev) => prev + 1);
  };

  const currentImageSrc = showOriginal && originalSrc ? originalSrc : `${src}${src.includes('?') ? '&' : '?'}v=${retryKey}`;

  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h4 style={{ margin: '0 0 4px', fontSize: '15px', fontWeight: 700, color: 'var(--text)' }}>{title}</h4>
          <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)' }}>{description}</p>
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          {originalSrc && (
            <button
              onClick={() => setShowOriginal(!showOriginal)}
              className="icon-button"
              style={{
                fontSize: '11px',
                padding: '4px 8px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: showOriginal ? 'var(--primary-soft)' : 'var(--surface-soft)',
                color: showOriginal ? 'var(--primary)' : 'var(--text)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
              }}
              title={showOriginal ? 'View Forensic Heatmap' : 'Compare with Original Media'}
            >
              {showOriginal ? <EyeOff size={13} /> : <Eye size={13} />}
              <span>{showOriginal ? 'Showing Original' : 'Compare Original'}</span>
            </button>
          )}

          <button
            onClick={() => setIsZoomed(!isZoomed)}
            className="icon-button"
            style={{
              fontSize: '11px',
              padding: '4px 8px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: isZoomed ? 'var(--primary-soft)' : 'var(--surface-soft)',
              color: isZoomed ? 'var(--primary)' : 'var(--text)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
            }}
            title={isZoomed ? 'Fit to Container' : 'Zoom 100%'}
          >
            {isZoomed ? <ZoomOut size={13} /> : <ZoomIn size={13} />}
            <span>{isZoomed ? 'Fit' : 'Zoom'}</span>
          </button>
        </div>
      </div>

      {/* Visual Frame */}
      <div
        style={{
          position: 'relative',
          background: 'var(--surface-soft)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          overflow: isZoomed ? 'auto' : 'hidden',
          minHeight: '260px',
          maxHeight: isZoomed ? '500px' : '320px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {isLoading && !hasError && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              background: 'var(--surface-soft)',
              color: 'var(--text-secondary)',
            }}
          >
            <div className="status-dot status-pulse" style={{ background: 'var(--primary)', width: 12, height: 12 }} />
            <span style={{ fontSize: '12px' }}>Loading visual artifact...</span>
          </div>
        )}

        {hasError ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              padding: '24px',
              textAlign: 'center',
              color: 'var(--text-muted)',
            }}
          >
            <AlertTriangle size={28} color="var(--warning)" />
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text)' }}>Artifact Unavailable</div>
            <p style={{ margin: 0, fontSize: '11px', maxWidth: '280px' }}>
              The visual heatmap could not be retrieved from the forensic cache or storage.
            </p>
            <button
              onClick={handleRetry}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '12px',
                borderRadius: '6px',
                border: '1px solid var(--border)',
                background: 'var(--surface)',
                color: 'var(--text)',
                cursor: 'pointer',
                marginTop: '6px',
              }}
            >
              <RotateCcw size={13} />
              <span>Retry</span>
            </button>
          </div>
        ) : (
          <img
            key={`${currentImageSrc}-${retryKey}`}
            src={currentImageSrc}
            alt={alt}
            onLoad={() => setIsLoading(false)}
            onError={() => {
              setIsLoading(false);
              setHasError(true);
            }}
            style={{
              display: isLoading ? 'none' : 'block',
              maxWidth: isZoomed ? 'none' : '100%',
              maxHeight: isZoomed ? 'none' : '300px',
              objectFit: 'contain',
              margin: 'auto',
            }}
          />
        )}

        {showOriginal && !hasError && !isLoading && (
          <div
            style={{
              position: 'absolute',
              top: '8px',
              left: '8px',
              background: 'rgba(0, 0, 0, 0.75)',
              color: '#fff',
              fontSize: '10px',
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: '4px',
              letterSpacing: '0.05em',
            }}
          >
            ORIGINAL ASSET
          </div>
        )}
      </div>

      {/* Forensic Legend & Interpretation */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'var(--surface-soft)',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '11px',
          color: 'var(--text-secondary)',
        }}
      >
        <ImageIcon size={14} style={{ flexShrink: 0, color: 'var(--primary)' }} />
        <span>{legend}</span>
      </div>
    </div>
  );
};
