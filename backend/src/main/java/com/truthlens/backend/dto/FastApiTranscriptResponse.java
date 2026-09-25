package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Collections;
import java.util.List;

/**
 * DTO matching the raw JSON response returned by the Python FastAPI Speech-to-Text service.
 */
public class FastApiTranscriptResponse {

    @JsonProperty("full_text")
    private String fullText;

    private String language;

    @JsonProperty("confidence_score")
    private double confidenceScore;

    @JsonProperty("duration_seconds")
    private double durationSeconds;

    @JsonProperty("segments_count")
    private int segmentsCount;

    @JsonProperty("words_count")
    private int wordsCount;

    private List<TranscriptSegmentDto> segments = Collections.emptyList();

    private TranscriptEvidenceDto evidence;

    private String status;

    @JsonProperty("error_message")
    private String errorMessage;

    public FastApiTranscriptResponse() {
    }

    public FastApiTranscriptResponse(
            String fullText,
            String language,
            double confidenceScore,
            double durationSeconds,
            int segmentsCount,
            int wordsCount,
            List<TranscriptSegmentDto> segments,
            TranscriptEvidenceDto evidence,
            String status,
            String errorMessage) {
        this.fullText = fullText;
        this.language = language;
        this.confidenceScore = confidenceScore;
        this.durationSeconds = durationSeconds;
        this.segmentsCount = segmentsCount;
        this.wordsCount = wordsCount;
        this.segments = segments != null ? segments : Collections.emptyList();
        this.evidence = evidence;
        this.status = status;
        this.errorMessage = errorMessage;
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

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }
}
