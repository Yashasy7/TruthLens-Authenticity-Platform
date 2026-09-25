package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Payload mapping the JSON response from internal FastAPI Audio Service (Module 07).
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FastApiAudioAnalysisResponse {

    @JsonProperty("synthetic_voice_prob")
    private double syntheticVoiceProb;

    @JsonProperty("spectrogram_url")
    private String spectrogramUrl;

    @JsonProperty("spectrogram_base64")
    private String spectrogramBase64;

    @JsonProperty("pitch_variance")
    private double pitchVariance;

    @JsonProperty("splice_markers")
    private List<AudioSpliceMarkerDto> spliceMarkers;

    @JsonProperty("model_name")
    private String modelName;

    @JsonProperty("model_version")
    private String modelVersion;

    @JsonProperty("evidence")
    private AudioEvidenceDto evidence;

    @JsonProperty("status")
    private String status;

    public FastApiAudioAnalysisResponse() {
    }

    public FastApiAudioAnalysisResponse(
            double syntheticVoiceProb,
            String spectrogramUrl,
            String spectrogramBase64,
            double pitchVariance,
            List<AudioSpliceMarkerDto> spliceMarkers,
            String modelName,
            String modelVersion,
            AudioEvidenceDto evidence,
            String status) {
        this.syntheticVoiceProb = syntheticVoiceProb;
        this.spectrogramUrl = spectrogramUrl;
        this.spectrogramBase64 = spectrogramBase64;
        this.pitchVariance = pitchVariance;
        this.spliceMarkers = spliceMarkers;
        this.modelName = modelName;
        this.modelVersion = modelVersion;
        this.evidence = evidence;
        this.status = status;
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

    public String getSpectrogramBase64() {
        return spectrogramBase64;
    }

    public void setSpectrogramBase64(String spectrogramBase64) {
        this.spectrogramBase64 = spectrogramBase64;
    }

    public double getPitchVariance() {
        return pitchVariance;
    }

    public void setPitchVariance(double pitchVariance) {
        this.pitchVariance = pitchVariance;
    }

    public List<AudioSpliceMarkerDto> getSpliceMarkers() {
        return spliceMarkers;
    }

    public void setSpliceMarkers(List<AudioSpliceMarkerDto> spliceMarkers) {
        this.spliceMarkers = spliceMarkers;
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

    public AudioEvidenceDto getEvidence() {
        return evidence;
    }

    public void setEvidence(AudioEvidenceDto evidence) {
        this.evidence = evidence;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
