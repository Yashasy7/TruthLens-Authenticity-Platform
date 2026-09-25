package com.truthlens.backend.dto;

import com.truthlens.backend.entity.AnalysisStatus;

import java.time.OffsetDateTime;
import java.util.Collections;
import java.util.List;
import java.util.UUID;

/**
 * Client-facing REST response DTO for Speech-to-Text transcript analysis (Module 10).
 */
public class TranscriptResponse {

    private UUID id;
    private UUID mediaId;
    private String fullText;
    private String language;
    private double confidenceScore;
    private double durationSeconds;
    private int segmentsCount;
    private int wordsCount;
    private List<TranscriptSegmentDto> segments = Collections.emptyList();
    private TranscriptEvidenceDto evidence;
    private AnalysisStatus analysisStatus;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    public TranscriptResponse() {
    }

    public TranscriptResponse(
            UUID id,
            UUID mediaId,
            String fullText,
            String language,
            double confidenceScore,
            double durationSeconds,
            int segmentsCount,
            int wordsCount,
            List<TranscriptSegmentDto> segments,
            TranscriptEvidenceDto evidence,
            AnalysisStatus analysisStatus,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt) {
        this.id = id;
        this.mediaId = mediaId;
        this.fullText = fullText;
        this.language = language;
        this.confidenceScore = confidenceScore;
        this.durationSeconds = durationSeconds;
        this.segmentsCount = segmentsCount;
        this.wordsCount = wordsCount;
        this.segments = segments != null ? segments : Collections.emptyList();
        this.evidence = evidence;
        this.analysisStatus = analysisStatus;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public UUID getMediaId() {
        return mediaId;
    }

    public void setMediaId(UUID mediaId) {
        this.mediaId = mediaId;
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

    public List<TranscriptSegmentDto> getSegments() {
        return segments;
    }

    public void setSegments(List<TranscriptSegmentDto> segments) {
        this.segments = segments != null ? segments : Collections.emptyList();
    }

    public TranscriptEvidenceDto getEvidence() {
        return evidence;
    }

    public void setEvidence(TranscriptEvidenceDto evidence) {
        this.evidence = evidence;
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
}
