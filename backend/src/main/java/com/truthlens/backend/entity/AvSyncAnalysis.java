package com.truthlens.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Objects;
import java.util.UUID;

/**
 * JPA entity representing Audio-Video Synchronization Analysis findings (Module 08).
 *
 * <p>Mapped to the {@code av_sync_analysis} table. Persists overall synchronization scores,
 * measured lip/audio temporal offsets in milliseconds, mismatch timestamps/segments,
 * and granular cross-modal forensic evidence.</p>
 */
@Entity
@Table(name = "av_sync_analysis")
public class AvSyncAnalysis {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "media_id", nullable = false, unique = true)
    private Media media;

    @Column(name = "sync_score", nullable = false)
    private double syncScore = 0.0;

    @Column(name = "lip_offset_ms", nullable = false)
    private double lipOffsetMs = 0.0;

    @Column(name = "confidence", nullable = false)
    private double confidence = 0.0;

    @Column(name = "mismatch_segments_json", columnDefinition = "TEXT")
    private String mismatchSegmentsJson;

    @Column(name = "evidence_json", columnDefinition = "TEXT")
    private String evidenceJson;

    @Enumerated(EnumType.STRING)
    @Column(name = "analysis_status", nullable = false, length = 30)
    private AnalysisStatus analysisStatus = AnalysisStatus.COMPLETED;

    @Column(name = "model_name", length = 100)
    private String modelName;

    @Column(name = "model_version", length = 100)
    private String modelVersion;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public AvSyncAnalysis() {
    }

    public AvSyncAnalysis(Media media) {
        this.media = media;
    }

    @PrePersist
    protected void onCreate() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        if (createdAt == null) {
            createdAt = now;
        }
        if (updatedAt == null) {
            updatedAt = now;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = OffsetDateTime.now(ZoneOffset.UTC);
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public Media getMedia() {
        return media;
    }

    public void setMedia(Media media) {
        this.media = media;
    }

    public double getSyncScore() {
        return syncScore;
    }

    public void setSyncScore(double syncScore) {
        this.syncScore = syncScore;
    }

    public double getLipOffsetMs() {
        return lipOffsetMs;
    }

    public void setLipOffsetMs(double lipOffsetMs) {
        this.lipOffsetMs = lipOffsetMs;
    }

    public double getConfidence() {
        return confidence;
    }

    public void setConfidence(double confidence) {
        this.confidence = confidence;
    }

    public String getMismatchSegmentsJson() {
        return mismatchSegmentsJson;
    }

    public void setMismatchSegmentsJson(String mismatchSegmentsJson) {
        this.mismatchSegmentsJson = mismatchSegmentsJson;
    }

    public String getEvidenceJson() {
        return evidenceJson;
    }

    public void setEvidenceJson(String evidenceJson) {
        this.evidenceJson = evidenceJson;
    }

    public AnalysisStatus getAnalysisStatus() {
        return analysisStatus;
    }

    public void setAnalysisStatus(AnalysisStatus analysisStatus) {
        this.analysisStatus = analysisStatus;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(OffsetDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(OffsetDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof AvSyncAnalysis that)) return false;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "AvSyncAnalysis{" +
                "id=" + id +
                ", syncScore=" + syncScore +
                ", lipOffsetMs=" + lipOffsetMs +
                ", confidence=" + confidence +
                ", analysisStatus=" + analysisStatus +
                ", modelName='" + modelName + '\'' +
                ", modelVersion='" + modelVersion + '\'' +
                '}';
    }
}
