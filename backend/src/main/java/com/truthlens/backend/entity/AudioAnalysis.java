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
 * JPA entity representing audio authenticity & voice forensics analysis findings (Module 07).
 *
 * <p>Mapped to the {@code audio_analysis} table. Persists synthetic voice cloning probabilities,
 * 80-band Mel-spectrogram artifact URLs, pitch variance metrics, phase discontinuity scores,
 * detected splice boundary markers, and granular acoustic forensic evidence.</p>
 */
@Entity
@Table(name = "audio_analysis")
public class AudioAnalysis {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "media_id", nullable = false, unique = true)
    private Media media;

    @Column(name = "synthetic_voice_prob", nullable = false)
    private double syntheticVoiceProb = 0.0;

    @Column(name = "spectrogram_url", length = 1024)
    private String spectrogramUrl;

    @Column(name = "pitch_variance", nullable = false)
    private double pitchVariance = 0.0;

    @Column(name = "phase_discontinuity", nullable = false)
    private double phaseDiscontinuity = 0.0;

    @Column(name = "splice_markers_json", columnDefinition = "TEXT")
    private String spliceMarkersJson;

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

    public AudioAnalysis() {
    }

    public AudioAnalysis(Media media) {
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

    public double getSyntheticVoiceProb() {
        return syntheticVoiceProb;
    }

    public void setSyntheticVoiceProb(double syntheticVoiceProb) {
        this.syntheticVoiceProb = syntheticVoiceProb;
    }

    public String getSpectrogramUrl() {
        return spectrogramUrl;
    }

    public void setSpectrogramUrl(String spectrogramUrl) {
        this.spectrogramUrl = spectrogramUrl;
    }

    public double getPitchVariance() {
        return pitchVariance;
    }

    public void setPitchVariance(double pitchVariance) {
        this.pitchVariance = pitchVariance;
    }

    public double getPhaseDiscontinuity() {
        return phaseDiscontinuity;
    }

    public void setPhaseDiscontinuity(double phaseDiscontinuity) {
        this.phaseDiscontinuity = phaseDiscontinuity;
    }

    public String getSpliceMarkersJson() {
        return spliceMarkersJson;
    }

    public void setSpliceMarkersJson(String spliceMarkersJson) {
        this.spliceMarkersJson = spliceMarkersJson;
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
        if (o == null || getClass() != o.getClass()) return false;
        AudioAnalysis that = (AudioAnalysis) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "AudioAnalysis{" +
                "id=" + id +
                ", syntheticVoiceProb=" + syntheticVoiceProb +
                ", pitchVariance=" + pitchVariance +
                ", phaseDiscontinuity=" + phaseDiscontinuity +
                ", analysisStatus=" + analysisStatus +
                ", modelName='" + modelName + '\'' +
                ", modelVersion='" + modelVersion + '\'' +
                ", createdAt=" + createdAt +
                '}';
    }
}
