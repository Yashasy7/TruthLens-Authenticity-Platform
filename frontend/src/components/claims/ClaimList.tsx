import React, { useState, useMemo } from 'react';
import {
  Claim,
  ClaimType,
  ClaimEntityType,
  ClaimAnalysisResponse,
} from '../../types/claim';
import './ClaimList.css';

export interface ClaimListProps {
  mediaId?: string;
  initialData?: ClaimAnalysisResponse | null;
  isLoading?: boolean;
  onReanalyze?: (source?: string) => Promise<void>;
  onAnalyzeDirectText?: (text: string) => Promise<ClaimAnalysisResponse>;
}

export const ClaimList: React.FC<ClaimListProps> = ({
  mediaId,
  initialData,
  isLoading = false,
  onReanalyze,
  onAnalyzeDirectText,
}) => {
  const [data, setData] = useState<ClaimAnalysisResponse | null>(initialData || null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [selectedEntity, setSelectedEntity] = useState<string>('ALL');
  const [adHocText, setAdHocText] = useState('');
  const [isAdHocLoading, setIsAdHocLoading] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Sync prop changes
  React.useEffect(() => {
    if (initialData) {
      setData(initialData);
    }
  }, [initialData]);

  const claims = useMemo(() => data?.claims || [], [data]);

  // Summary Metrics
  const stats = useMemo(() => {
    const total = claims.length;
    const factual = claims.filter((c) => c.claimType === 'FACTUAL_CLAIM').length;
    const opinions = claims.filter((c) => c.claimType === 'OPINION').length;
    const questions = claims.filter((c) => c.claimType === 'QUESTION').length;
    const entitiesCount = data?.entities?.length || 0;
    return { total, factual, opinions, questions, entitiesCount };
  }, [claims, data]);

  // Filtered Claims
  const filteredClaims = useMemo(() => {
    return claims.filter((claim) => {
      // Type filter
      if (selectedType !== 'ALL' && claim.claimType !== selectedType) {
        return false;
      }
      // Entity type filter
      if (selectedEntity !== 'ALL' && claim.entityType !== selectedEntity) {
        return false;
      }
      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesText = claim.claimText.toLowerCase().includes(q);
        const matchesSubj = claim.subject?.toLowerCase().includes(q) || false;
        const matchesAct = claim.action?.toLowerCase().includes(q) || false;
        const matchesVal = claim.value?.toLowerCase().includes(q) || false;
        return matchesText || matchesSubj || matchesAct || matchesVal;
      }
      return true;
    });
  }, [claims, selectedType, selectedEntity, searchQuery]);

  const handleCopyHash = (hash: string) => {
    navigator.clipboard?.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleAdHocSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adHocText.trim() || !onAnalyzeDirectText) return;
    try {
      setIsAdHocLoading(true);
      const res = await onAnalyzeDirectText(adHocText);
      setData(res);
    } finally {
      setIsAdHocLoading(false);
    }
  };

  const getBadgeClass = (type: ClaimType) => {
    switch (type) {
      case 'FACTUAL_CLAIM':
        return 'claim-badge-factual';
      case 'OPINION':
        return 'claim-badge-opinion';
      case 'QUESTION':
        return 'claim-badge-question';
      case 'NON_CLAIM':
        return 'claim-badge-nonclaim';
      case 'UNCERTAIN':
      default:
        return 'claim-badge-uncertain';
    }
  };

  return (
    <div className="claim-list-container">
      {/* Header */}
      <div className="claim-header">
        <div className="claim-header-title">
          <h2>Text & Claim Analysis</h2>
          <span className="claim-nlp-badge">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            spaCy / en_core_web_sm
          </span>
        </div>

        <div className="claim-header-actions">
          {onReanalyze && mediaId && (
            <button
              className="claim-btn claim-btn-primary"
              disabled={isLoading}
              onClick={() => onReanalyze()}
            >
              {isLoading ? 'Extracting Claims...' : 'Re-Analyze Media'}
            </button>
          )}
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="claim-stats-grid">
        <div className="claim-stat-card">
          <span className="claim-stat-label">Total Claims</span>
          <span className="claim-stat-val">{stats.total}</span>
        </div>
        <div className="claim-stat-card">
          <span className="claim-stat-label">Factual Statements</span>
          <span className="claim-stat-val" style={{ color: 'var(--tl-accent-emerald)' }}>
            {stats.factual}
          </span>
        </div>
        <div className="claim-stat-card">
          <span className="claim-stat-label">Opinions / Subjective</span>
          <span className="claim-stat-val" style={{ color: 'var(--tl-accent-amber)' }}>
            {stats.opinions}
          </span>
        </div>
        <div className="claim-stat-card">
          <span className="claim-stat-label">Questions</span>
          <span className="claim-stat-val" style={{ color: 'var(--tl-accent-purple)' }}>
            {stats.questions}
          </span>
        </div>
        <div className="claim-stat-card">
          <span className="claim-stat-label">Named Entities</span>
          <span className="claim-stat-val" style={{ color: 'var(--tl-accent-blue)' }}>
            {stats.entitiesCount}
          </span>
        </div>
      </div>

      {/* Ad-Hoc Direct Text Decomposition Playground */}
      {onAnalyzeDirectText && (
        <div className="claim-adhoc-box">
          <div className="claim-adhoc-title">Direct Text Claim Extraction Playground</div>
          <form onSubmit={handleAdHocSubmit}>
            <textarea
              className="claim-adhoc-textarea"
              placeholder="Paste raw transcript, OCR text, or claim sentence to decompose into (Subject, Action, Value)..."
              value={adHocText}
              onChange={(e) => setAdHocText(e.target.value)}
            />
            <button
              type="submit"
              className="claim-btn claim-btn-secondary"
              disabled={isAdHocLoading || !adHocText.trim()}
            >
              {isAdHocLoading ? 'Decomposing...' : 'Decompose Text into Claims'}
            </button>
          </form>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="claim-toolbar">
        <div className="claim-search-box">
          <input
            type="text"
            className="claim-search-input"
            placeholder="Search claims by text, subject, action, value..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="claim-filters-group">
          <select
            className="claim-select"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="ALL">All Types</option>
            <option value="FACTUAL_CLAIM">Factual Claim</option>
            <option value="OPINION">Opinion</option>
            <option value="QUESTION">Question</option>
            <option value="NON_CLAIM">Non-Claim</option>
            <option value="UNCERTAIN">Uncertain</option>
          </select>

          <select
            className="claim-select"
            value={selectedEntity}
            onChange={(e) => setSelectedEntity(e.target.value)}
          >
            <option value="ALL">All Entities</option>
            <option value="PERSON">Person</option>
            <option value="ORG">Organization</option>
            <option value="LOCATION">Location</option>
            <option value="DATE">Date</option>
            <option value="MONEY">Money</option>
            <option value="QUANTITY">Quantity</option>
            <option value="EVENT">Event</option>
            <option value="GENERAL">General</option>
          </select>
        </div>
      </div>

      {/* Claims List */}
      {filteredClaims.length === 0 ? (
        <div className="claim-empty-state">
          <h3>No claims found</h3>
          <p>
            {claims.length === 0
              ? 'No factual claims or assertions have been extracted yet from this media.'
              : 'No claims match your current filter and search criteria.'}
          </p>
        </div>
      ) : (
        <div className="claim-cards-list">
          {filteredClaims.map((claim) => (
            <div key={claim.id || claim.claimHash} className="claim-card">
              <div className="claim-card-header">
                <div className="claim-card-meta">
                  <span className="claim-index-tag">#{claim.sentenceIndex + 1}</span>
                  <span className={`claim-badge ${getBadgeClass(claim.claimType)}`}>
                    {claim.claimType.replace('_', ' ')}
                  </span>
                  <span className="claim-source-badge">{claim.sourceType}</span>
                </div>

                <div className="claim-confidence-container">
                  <span style={{ fontSize: '0.75rem', color: 'var(--tl-text-muted)' }}>
                    Confidence {Math.round(claim.confidenceScore * 100)}%
                  </span>
                  <div className="claim-confidence-bar">
                    <div
                      className="claim-confidence-fill"
                      style={{ width: `${Math.round(claim.confidenceScore * 100)}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Surface Text */}
              <div className="claim-text-body">"{claim.claimText}"</div>

              {/* Semantic Decomposition */}
              {(claim.subject || claim.action || claim.value) && (
                <div className="claim-decomposition-box">
                  {claim.subject && (
                    <div className="claim-decomp-item">
                      <span className="claim-decomp-label">Subject</span>
                      <span className="claim-decomp-value">{claim.subject}</span>
                    </div>
                  )}
                  {claim.action && (
                    <div className="claim-decomp-item">
                      <span className="claim-decomp-label">Action / Verb</span>
                      <span className="claim-decomp-value">{claim.action}</span>
                    </div>
                  )}
                  {claim.value && (
                    <div className="claim-decomp-item">
                      <span className="claim-decomp-label">Value / Target</span>
                      <span className="claim-decomp-value">{claim.value}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Named Entity Chips */}
              {claim.entities && claim.entities.length > 0 && (
                <div className="claim-entities-row">
                  {claim.entities.map((ent, idx) => (
                    <span key={idx} className="claim-entity-chip">
                      <span>{ent.text}</span>
                      <span className="claim-entity-tag">{ent.normalized_label || ent.label}</span>
                    </span>
                  ))}
                </div>
              )}

              {/* Card Footer */}
              <div className="claim-card-footer">
                <span
                  className="claim-hash-pill"
                  title="Click to copy canonical SHA-256 claim hash"
                  onClick={() => handleCopyHash(claim.claimHash)}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                  {copiedHash === claim.claimHash ? 'Copied!' : `${claim.claimHash.slice(0, 16)}...`}
                </span>

                <span>
                  Span: [{claim.startChar} - {claim.endChar}]
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ClaimList;
