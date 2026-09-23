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
 * JPA entity representing video deepfake & forensic analysis findings (Module 06).
 *
 * <p>Mapped to the {@code video_analysis} table. Persists aggregate deepfake probabilities,
 * face counts, total sampled frame counts, suspicious timeline markers, and per-frame forensic scores.</p>
 */
@Entity
@Table(name = "video_analysis")
public class VideoAnalysis {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "media_id", nullable = false, unique = true)
    private Media media;

    @Column(name = "deepfake_prob", nullable = false)
    private double deepfakeProb = 0.0;

    @Column(name = "face_count", nullable = false)
    private int faceCount = 0;

    @Column(name = "total_frames_sampled", nullable = false)
    private int totalFramesSampled = 0;

    @Column(name = "suspicious_timestamps_json", columnDefinition = "TEXT")
    private String suspiciousTimestampsJson;

    @Column(name = "frame_scores_json", columnDefinition = "TEXT")
    private String frameScoresJson;

    @Enumerated(EnumType.STRING)
    @Column(name = "analysis_status", nullable = false, length = 30)
    private AnalysisStatus analysisStatus = AnalysisStatus.COMPLETED;

    @Column(name = "model_version", length = 100)
    private String modelVersion;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public VideoAnalysis() {
    }

    public VideoAnalysis(Media media) {
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

    public double getDeepfakeProb() {
        return deepfakeProb;
    }

    public void setDeepfakeProb(double deepfakeProb) {
        this.deepfakeProb = deepfakeProb;
    }

    public int getFaceCount() {
        return faceCount;
    }

    public void setFaceCount(int faceCount) {
        this.faceCount = faceCount;
    }

    public int getTotalFramesSampled() {
        return totalFramesSampled;
    }

    public void setTotalFramesSampled(int totalFramesSampled) {
        this.totalFramesSampled = totalFramesSampled;
    }

    public String getSuspiciousTimestampsJson() {
        return suspiciousTimestampsJson;
    }

    public void setSuspiciousTimestampsJson(String suspiciousTimestampsJson) {
        this.suspiciousTimestampsJson = suspiciousTimestampsJson;
    }

    public String getFrameScoresJson() {
        return frameScoresJson;
    }

    public void setFrameScoresJson(String frameScoresJson) {
        this.frameScoresJson = frameScoresJson;
    }

    public AnalysisStatus getAnalysisStatus() {
        return analysisStatus;
    }

    public void setAnalysisStatus(AnalysisStatus analysisStatus) {
        this.analysisStatus = analysisStatus;
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
        if (o == null || getClass() != o.getClass()) return false;
        VideoAnalysis that = (VideoAnalysis) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "VideoAnalysis{" +
                "id=" + id +
                ", deepfakeProb=" + deepfakeProb +
                ", faceCount=" + faceCount +
                ", totalFramesSampled=" + totalFramesSampled +
                ", analysisStatus=" + analysisStatus +
                ", modelVersion='" + modelVersion + '\'' +
                ", createdAt=" + createdAt +
                '}';
    }
}
