package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Collections;
import java.util.Map;

/**
 * DTO representing Faster-Whisper ASR model metadata, acoustic extraction parameters, and diagnostic metrics.
 */
public class TranscriptEvidenceDto {

    @JsonProperty("model_name")
    private String modelName = "Faster-Whisper";

    @JsonProperty("model_size")
    private String modelSize = "tiny";

    @JsonProperty("compute_type")
    private String computeType = "int8";

    private String device = "cpu";

    @JsonProperty("detected_language")
    private String detectedLanguage = "en";

    @JsonProperty("language_probability")
    private double languageProbability = 1.0;

    @JsonProperty("duration_seconds")
    private double durationSeconds;

    @JsonProperty("audio_sample_rate")
    private int audioSampleRate = 16000;

    @JsonProperty("media_type")
    private String mediaType = "AUDIO";

    private Map<String, Object> details = Collections.emptyMap();

    public TranscriptEvidenceDto() {
    }

    public TranscriptEvidenceDto(
            String modelName,
            String modelSize,
            String computeType,
            String device,
            String detectedLanguage,
            double languageProbability,
            double durationSeconds,
            int audioSampleRate,
            String mediaType,
            Map<String, Object> details) {
        this.modelName = modelName;
        this.modelSize = modelSize;
        this.computeType = computeType;
        this.device = device;
        this.detectedLanguage = detectedLanguage;
        this.languageProbability = languageProbability;
        this.durationSeconds = durationSeconds;
        this.audioSampleRate = audioSampleRate;
        this.mediaType = mediaType;
        this.details = details != null ? details : Collections.emptyMap();
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getModelSize() {
        return modelSize;
    }

    public void setModelSize(String modelSize) {
        this.modelSize = modelSize;
    }

    public String getComputeType() {
        return computeType;
    }

    public void setComputeType(String computeType) {
        this.computeType = computeType;
    }

    public String getDevice() {
        return device;
    }

    public void setDevice(String device) {
        this.device = device;
    }

    public String getDetectedLanguage() {
        return detectedLanguage;
    }

    public void setDetectedLanguage(String detectedLanguage) {
        this.detectedLanguage = detectedLanguage;
    }

    public double getLanguageProbability() {
        return languageProbability;
    }

    public void setLanguageProbability(double languageProbability) {
        this.languageProbability = languageProbability;
    }

    public double getDurationSeconds() {
        return durationSeconds;
    }

    public void setDurationSeconds(double durationSeconds) {
        this.durationSeconds = durationSeconds;
    }

    public int getAudioSampleRate() {
        return audioSampleRate;
    }

    public void setAudioSampleRate(int audioSampleRate) {
        this.audioSampleRate = audioSampleRate;
    }

    public String getMediaType() {
        return mediaType;
    }

    public void setMediaType(String mediaType) {
        this.mediaType = mediaType;
    }

    public Map<String, Object> getDetails() {
        return details;
    }

    public void setDetails(Map<String, Object> details) {
        this.details = details != null ? details : Collections.emptyMap();
    }
}
