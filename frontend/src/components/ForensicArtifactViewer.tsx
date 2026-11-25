import React, { useState, useEffect } from 'react';
import { Eye, EyeOff, ZoomIn, ZoomOut, RotateCcw, AlertTriangle, Image as ImageIcon } from 'lucide-react';
import { getToken } from '../services/api';

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
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [originalBlobUrl, setOriginalBlobUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isZoomed, setIsZoomed] = useState(false);
  const [showOriginal, setShowOriginal] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  const isAvailable = Boolean(src && src.trim().length > 0);

  const handleRetry = () => {
    setHasError(false);
    setIsLoading(true);
    setRetryKey((prev) => prev + 1);
  };

  // Fetch original media stream authenticated
  useEffect(() => {
    if (!originalSrc) {
      setOriginalBlobUrl(null);
      return;
    }

    let isMounted = true;
    let activeOrigUrl: string | null = null;

    const fetchOriginal = async () => {
      try {
        const headers = new Headers();
        const token = getToken();
        if (token) {
          headers.set('Authorization', `Bearer ${token}`);
        }

        const response = await fetch(originalSrc, {
          method: 'GET',
          headers,
        });

        if (!response.ok) {
          throw new Error(`Failed to load original media: ${response.status}`);
        }

        const blob = await response.blob();
        if (!isMounted) return;

        activeOrigUrl = URL.createObjectURL(blob);
        setOriginalBlobUrl(activeOrigUrl);
      } catch {
        if (isMounted) {
          setOriginalBlobUrl(null);
        }
      }
    };

    fetchOriginal();

    return () => {
      isMounted = false;
      if (activeOrigUrl) {
        URL.revokeObjectURL(activeOrigUrl);
      }
    };
  }, [originalSrc]);

  // Fetch forensic heatmap artifact authenticated
  useEffect(() => {
    if (!isAvailable) {
      setIsLoading(false);
      setBlobUrl(null);
      return;
    }

    if (src.startsWith('data:')) {
      setHasError(false);
      setIsLoading(false);
      setBlobUrl(src);
      return;
    }

    let isMounted = true;
    let activeObjectUrl: string | null = null;

    const fetchArtifact = async () => {
      setIsLoading(true);
      setHasError(false);

      try {
        const headers = new Headers();
        const token = getToken();
        if (token) {
          headers.set('Authorization', `Bearer ${token}`);
        }

        const response = await fetch(src, {
          method: 'GET',
          headers,
        });

        if (!response.ok) {
          throw new Error(`Failed to load artifact: ${response.status}`);
        }

        const blob = await response.blob();
        if (!isMounted) return;

        activeObjectUrl = URL.createObjectURL(blob);
        setBlobUrl(activeObjectUrl);
        setIsLoading(false);
      } catch {
        if (isMounted) {
          setHasError(true);
          setIsLoading(false);
        }
      }
    };

    fetchArtifact();

    return () => {
      isMounted = false;
      if (activeObjectUrl) {
        URL.revokeObjectURL(activeObjectUrl);
      }
    };
  }, [src, isAvailable, retryKey]);

  const currentImageSrc = showOriginal && originalBlobUrl ? originalBlobUrl : (blobUrl || '');

  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: '14px',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
      }}
    >
      {/* Header and Controls Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '14px',
          marginBottom: '16px',
        }}
      >
        <div style={{ minWidth: '220px', flex: '1 1 auto' }}>
          <h4 style={{ margin: '0 0 4px', fontSize: '16px', fontWeight: 700, color: 'var(--text)' }}>{title}</h4>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>{description}</p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {originalSrc && (
            <button
              onClick={() => setShowOriginal(!showOriginal)}
              style={{
                minHeight: '40px',
                padding: '0 16px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '13px',
                fontWeight: 600,
                background: showOriginal ? 'var(--primary)' : 'var(--surface-soft)',
                color: showOriginal ? '#ffffff' : 'var(--text)',
                border: showOriginal ? '1px solid var(--primary)' : '1px solid var(--border)',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                boxShadow: showOriginal ? '0 2px 6px rgba(79, 70, 229, 0.25)' : '0 1px 2px rgba(0,0,0,0.03)',
              }}
              title={showOriginal ? 'Switch to Forensic Heatmap' : 'Compare with Original Media'}
            >
              {showOriginal ? <EyeOff size={16} /> : <Eye size={16} />}
              <span>{showOriginal ? 'Showing Original' : 'Compare Original'}</span>
            </button>
          )}

          <button
            onClick={() => setIsZoomed(!isZoomed)}
            style={{
              minHeight: '40px',
              padding: '0 16px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '13px',
              fontWeight: 600,
              background: isZoomed ? 'var(--primary)' : 'var(--surface-soft)',
              color: isZoomed ? '#ffffff' : 'var(--text)',
              border: isZoomed ? '1px solid var(--primary)' : '1px solid var(--border)',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              boxShadow: isZoomed ? '0 2px 6px rgba(79, 70, 229, 0.25)' : '0 1px 2px rgba(0,0,0,0.03)',
            }}
            title={isZoomed ? 'Fit to Container' : 'Zoom Full Resolution'}
          >
            {isZoomed ? <ZoomOut size={16} /> : <ZoomIn size={16} />}
            <span>{isZoomed ? 'Fit to Frame' : 'Zoom 100%'}</span>
          </button>
        </div>
      </div>

      {/* Visual Frame */}
      <div
        style={{
          position: 'relative',
          background: 'var(--surface-soft)',
          border: '1px solid var(--border)',
          borderRadius: '10px',
          overflow: isZoomed ? 'auto' : 'hidden',
          minHeight: '280px',
          maxHeight: isZoomed ? '540px' : '360px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '14px',
        }}
      >
        {!isAvailable && !showOriginal ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              padding: '36px 24px',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: '52px',
                height: '52px',
                borderRadius: '12px',
                background: 'var(--primary-soft)',
                color: 'var(--primary)',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <ImageIcon size={26} />
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text)', marginBottom: '4px' }}>
                {title.includes('Grad-CAM')
                  ? 'Grad-CAM Attention Map Deferred'
                  : title.includes('Spectrogram')
                  ? 'Mel-Spectrogram Not Available'
                  : 'Forensic Heatmap Not Generated'}
              </div>
              <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '380px', lineHeight: 1.5 }}>
                {title.includes('Grad-CAM')
                  ? 'Grad-CAM spatial overlays are deferred for the active Vision Transformer (CLIP ViT-L/14) detector. Physical ELA and noise/FFT forensics remain active.'
                  : title.includes('Spectrogram')
                  ? 'The 80-band log Mel-spectrogram artifact is generated during completed audio forensic analysis.'
                  : 'Error Level Analysis (ELA) is available once the compression difference artifact is computed.'}
              </p>
            </div>
          </div>
        ) : hasError ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              padding: '36px 24px',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: '52px',
                height: '52px',
                borderRadius: '12px',
                background: 'var(--warning-soft)',
                color: 'var(--warning)',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <AlertTriangle size={26} />
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text)', marginBottom: '4px' }}>
                Artifact Stream Unavailable
              </div>
              <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '340px', lineHeight: 1.5 }}>
                The visual heatmap could not be retrieved from the forensic cache or backend storage.
              </p>
            </div>
            <button
              onClick={handleRetry}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                minHeight: '38px',
                padding: '0 16px',
                fontSize: '13px',
                fontWeight: 600,
                borderRadius: '8px',
                border: '1px solid var(--border)',
                background: 'var(--surface)',
                color: 'var(--text)',
                cursor: 'pointer',
                marginTop: '4px',
                boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
              }}
            >
              <RotateCcw size={15} />
              <span>Retry Loading</span>
            </button>
          </div>
        ) : (
          <>
            {isLoading && (
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
                <span style={{ fontSize: '13px', fontWeight: 500 }}>Loading visual artifact...</span>
              </div>
            )}
            <img
              key={`${src}-${retryKey}-${showOriginal ? 'orig' : 'art'}`}
              src={currentImageSrc}
              alt={alt}
              style={{
                display: isLoading ? 'none' : 'block',
                maxWidth: isZoomed ? 'none' : '100%',
                maxHeight: isZoomed ? 'none' : '340px',
                objectFit: 'contain',
                margin: 'auto',
              }}
            />
          </>
        )}

        {showOriginal && !hasError && !isLoading && (
          <div
            style={{
              position: 'absolute',
              top: '12px',
              left: '12px',
              background: 'rgba(15, 23, 42, 0.82)',
              color: '#ffffff',
              fontSize: '11px',
              fontWeight: 700,
              padding: '4px 10px',
              borderRadius: '6px',
              letterSpacing: '0.05em',
              backdropFilter: 'blur(4px)',
            }}
          >
            ORIGINAL MEDIA
          </div>
        )}
      </div>

      {/* Forensic Legend & Interpretation */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: 'var(--surface-soft)',
          padding: '10px 14px',
          borderRadius: '8px',
          fontSize: '12px',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border)',
        }}
      >
        <ImageIcon size={15} style={{ flexShrink: 0, color: 'var(--primary)' }} />
        <span>{legend}</span>
      </div>
    </div>
  );
};
