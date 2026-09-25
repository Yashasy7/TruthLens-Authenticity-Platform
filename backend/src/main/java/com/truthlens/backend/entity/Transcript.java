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
 * JPA entity representing Speech-to-Text & Transcript findings (Module 10).
 *
 * <p>Mapped to the {@code transcripts} table. Persists complete transcript text,
 * timestamped segments with word-level offsets, detected language, confidence scores,
 * and Faster-Whisper ASR evidence.</p>
 */
@Entity
@Table(name = "transcripts")
public class Transcript {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "media_id", nullable = false, unique = true)
    private Media media;

    @Column(name = "full_text", columnDefinition = "TEXT")
    private String fullText;

    @Column(name = "language", nullable = false, length = 50)
    private String language = "en";

    @Column(name = "confidence_score", nullable = false)
    private double confidenceScore = 1.0;

    @Column(name = "duration_seconds", nullable = false)
    private double durationSeconds = 0.0;

    @Column(name = "segments_count", nullable = false)
    private int segmentsCount = 0;

    @Column(name = "words_count", nullable = false)
    private int wordsCount = 0;

    @Column(name = "timestamp_segments_json", columnDefinition = "TEXT")
    private String timestampSegmentsJson;

    @Column(name = "evidence_json", columnDefinition = "TEXT")
    private String evidenceJson;

    @Enumerated(EnumType.STRING)
    @Column(name = "analysis_status", nullable = false, length = 30)
    private AnalysisStatus analysisStatus = AnalysisStatus.COMPLETED;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public Transcript() {
    }

    public Transcript(
            Media media,
            String fullText,
            String language,
            double confidenceScore,
            double durationSeconds,
            int segmentsCount,
            int wordsCount,
            String timestampSegmentsJson,
            String evidenceJson,
            AnalysisStatus analysisStatus) {
        this.media = media;
        this.fullText = fullText;
        this.language = (language != null && !language.isBlank()) ? language : "en";
        this.confidenceScore = confidenceScore;
        this.durationSeconds = durationSeconds;
        this.segmentsCount = segmentsCount;
        this.wordsCount = wordsCount;
        this.timestampSegmentsJson = timestampSegmentsJson;
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

    public String getFullText() {
        return fullText;
    }

    public void setFullText(String fullText) {
        this.fullText = fullText;
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

    public double getDurationSeconds() {
        return durationSeconds;
    }

    public void setDurationSeconds(double durationSeconds) {
        this.durationSeconds = durationSeconds;
    }

    public int getSegmentsCount() {
        return segmentsCount;
    }

    public void setSegmentsCount(int segmentsCount) {
        this.segmentsCount = segmentsCount;
    }

    public int getWordsCount() {
        return wordsCount;
    }

    public void setWordsCount(int wordsCount) {
        this.wordsCount = wordsCount;
    }

    public String getTimestampSegmentsJson() {
        return timestampSegmentsJson;
    }

    public void setTimestampSegmentsJson(String timestampSegmentsJson) {
        this.timestampSegmentsJson = timestampSegmentsJson;
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

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Transcript that = (Transcript) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
