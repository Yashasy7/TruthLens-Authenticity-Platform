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
 * JPA entity representing OCR & Visual Text Extraction findings (Module 09).
 *
 * <p>Mapped to the {@code ocr_results} table. Persists extracted text strings,
 * spatial bounding boxes (and temporal keyframe timestamps), detected language,
 * recognition confidence, and visual preprocessing evidence.</p>
 */
@Entity
@Table(name = "ocr_results")
public class OcrResult {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "media_id", nullable = false, unique = true)
    private Media media;

    @Column(name = "extracted_text", columnDefinition = "TEXT")
    private String extractedText;

    @Column(name = "language", nullable = false, length = 50)
    private String language = "en";

    @Column(name = "confidence_score", nullable = false)
    private double confidenceScore = 1.0;

    @Column(name = "regions_count", nullable = false)
    private int regionsCount = 0;

    @Column(name = "bounding_boxes_json", columnDefinition = "TEXT")
    private String boundingBoxesJson;

    @Column(name = "evidence_json", columnDefinition = "TEXT")
    private String evidenceJson;

    @Enumerated(EnumType.STRING)
    @Column(name = "analysis_status", nullable = false, length = 30)
    private AnalysisStatus analysisStatus = AnalysisStatus.COMPLETED;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public OcrResult() {
    }

    public OcrResult(
            Media media,
            String extractedText,
            String language,
            double confidenceScore,
            int regionsCount,
            String boundingBoxesJson,
            String evidenceJson,
            AnalysisStatus analysisStatus) {
        this.media = media;
        this.extractedText = extractedText;
        this.language = (language != null && !language.isBlank()) ? language : "en";
        this.confidenceScore = confidenceScore;
        this.regionsCount = regionsCount;
        this.boundingBoxesJson = boundingBoxesJson;
        this.evidenceJson = evidenceJson;
        this.analysisStatus = analysisStatus != null ? analysisStatus : AnalysisStatus.COMPLETED;
    }

    @PrePersist
    public void onPrePersist() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        if (this.createdAt == null) {
            this.createdAt = now;
        }
        if (this.updatedAt == null) {
            this.updatedAt = now;
        }
    }

    @PreUpdate
    public void onPreUpdate() {
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

    public String getExtractedText() {
        return extractedText;
    }

    public void setExtractedText(String extractedText) {
        this.extractedText = extractedText;
    }

    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }

    public double getConfidenceScore() {
        return confidenceScore;
    }

    public void setConfidenceScore(double confidenceScore) {
        this.confidenceScore = confidenceScore;
    }

    public int getRegionsCount() {
        return regionsCount;
    }

    public void setRegionsCount(int regionsCount) {
        this.regionsCount = regionsCount;
    }

    public String getBoundingBoxesJson() {
        return boundingBoxesJson;
    }

    public void setBoundingBoxesJson(String boundingBoxesJson) {
        this.boundingBoxesJson = boundingBoxesJson;
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
        if (!(o instanceof OcrResult other)) return false;
        return Objects.equals(id, other.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "OcrResult{" +
                "id=" + id +
                ", language='" + language + '\'' +
                ", confidenceScore=" + confidenceScore +
                ", regionsCount=" + regionsCount +
                ", analysisStatus=" + analysisStatus +
                '}';
    }
}
