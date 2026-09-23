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
 * JPA entity representing image authenticity analysis findings (Module 05).
 *
 * <p>Mapped to the {@code image_analysis} table. Stores synthetic AI generation probabilities,
 * physical localized manipulation probabilities, ELA / Grad-CAM heatmap artifact references,
 * noise variance metrics, FFT spectral scores, and structured explainable evidence.</p>
 */
@Entity
@Table(name = "image_analysis")
public class ImageAnalysis {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "media_id", nullable = false, unique = true)
    private Media media;

    @Column(name = "ai_prob", nullable = false)
    private double aiProb = 0.0;

    @Column(name = "manipulation_prob", nullable = false)
    private double manipulationProb = 0.0;

    @Column(name = "ela_heatmap_url", length = 500)
    private String elaHeatmapUrl;

    @Column(name = "gradcam_heatmap_url", length = 500)
    private String gradcamHeatmapUrl;

    @Column(name = "noise_variance")
    private Double noiseVariance;

    @Column(name = "fft_anomaly_score")
    private Double fftAnomalyScore;

    @Column(name = "copy_move_detected", nullable = false)
    private boolean copyMoveDetected = false;

    @Column(name = "splicing_detected", nullable = false)
    private boolean splicingDetected = false;

    @Enumerated(EnumType.STRING)
    @Column(name = "analysis_status", nullable = false, length = 30)
    private AnalysisStatus analysisStatus = AnalysisStatus.COMPLETED;

    @Column(name = "model_version", length = 100)
    private String modelVersion;

    @Column(name = "evidence_json", columnDefinition = "TEXT")
    private String evidenceJson;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public ImageAnalysis() {
    }

    public ImageAnalysis(Media media) {
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
        updatedAt = OffsetDateTime.now(ZoneOffset.UTC);
    }

    // Getters and Setters

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

    public double getAiProb() {
        return aiProb;
    }

    public void setAiProb(double aiProb) {
        this.aiProb = aiProb;
    }

    public double getManipulationProb() {
        return manipulationProb;
    }

    public void setManipulationProb(double manipulationProb) {
        this.manipulationProb = manipulationProb;
    }

    public String getElaHeatmapUrl() {
        return elaHeatmapUrl;
    }

    public void setElaHeatmapUrl(String elaHeatmapUrl) {
        this.elaHeatmapUrl = elaHeatmapUrl;
    }

    public String getGradcamHeatmapUrl() {
        return gradcamHeatmapUrl;
    }

    public void setGradcamHeatmapUrl(String gradcamHeatmapUrl) {
        this.gradcamHeatmapUrl = gradcamHeatmapUrl;
    }

    public Double getNoiseVariance() {
        return noiseVariance;
    }

    public void setNoiseVariance(Double noiseVariance) {
        this.noiseVariance = noiseVariance;
    }

    public Double getFftAnomalyScore() {
        return fftAnomalyScore;
    }

    public void setFftAnomalyScore(Double fftAnomalyScore) {
        this.fftAnomalyScore = fftAnomalyScore;
    }

    public boolean isCopyMoveDetected() {
        return copyMoveDetected;
    }

    public void setCopyMoveDetected(boolean copyMoveDetected) {
        this.copyMoveDetected = copyMoveDetected;
    }

    public boolean isSplicingDetected() {
        return splicingDetected;
    }

    public void setSplicingDetected(boolean splicingDetected) {
        this.splicingDetected = splicingDetected;
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

    public String getEvidenceJson() {
        return evidenceJson;
    }

    public void setEvidenceJson(String evidenceJson) {
        this.evidenceJson = evidenceJson;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof ImageAnalysis that)) return false;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
