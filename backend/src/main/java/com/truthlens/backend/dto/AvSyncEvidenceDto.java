package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

/**
 * Data transfer object representing granular explainable evidence for AV sync analysis (Module 08).
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AvSyncEvidenceDto {

    @JsonProperty("detected_faces_count")
    private int detectedFacesCount;

    @JsonProperty("selected_face_track_id")
    private int selectedFaceTrackId;

    @JsonProperty("video_duration_seconds")
    private double videoDurationSeconds;

    @JsonProperty("audio_duration_seconds")
    private double audioDurationSeconds;

    @JsonProperty("fps")
    private double fps;

    @JsonProperty("envelope_correlation")
    private double envelopeCorrelation;

    @JsonProperty("syncnet_min_distance")
    private double syncnetMinDistance;

    @JsonProperty("syncnet_confidence")
    private double syncnetConfidence;

    @JsonProperty("tracking_stability")
    private double trackingStability;

    @JsonProperty("is_development_model")
    private boolean isDevelopmentModel;

    @JsonProperty("details")
    private Map<String, Object> details;

    public AvSyncEvidenceDto() {
    }

    public int getDetectedFacesCount() {
        return detectedFacesCount;
    }

    public void setDetectedFacesCount(int detectedFacesCount) {
        this.detectedFacesCount = detectedFacesCount;
    }

    public int getSelectedFaceTrackId() {
        return selectedFaceTrackId;
    }

    public void setSelectedFaceTrackId(int selectedFaceTrackId) {
        this.selectedFaceTrackId = selectedFaceTrackId;
    }

    public double getVideoDurationSeconds() {
        return videoDurationSeconds;
    }

    public void setVideoDurationSeconds(double videoDurationSeconds) {
        this.videoDurationSeconds = videoDurationSeconds;
    }

    public double getAudioDurationSeconds() {
        return audioDurationSeconds;
    }

    public void setAudioDurationSeconds(double audioDurationSeconds) {
        this.audioDurationSeconds = audioDurationSeconds;
    }

    public double getFps() {
        return fps;
    }

    public void setFps(double fps) {
        this.fps = fps;
    }

    public double getEnvelopeCorrelation() {
        return envelopeCorrelation;
    }

    public void setEnvelopeCorrelation(double envelopeCorrelation) {
        this.envelopeCorrelation = envelopeCorrelation;
    }

    public double getSyncnetMinDistance() {
        return syncnetMinDistance;
    }

    public void setSyncnetMinDistance(double syncnetMinDistance) {
        this.syncnetMinDistance = syncnetMinDistance;
    }

    public double getSyncnetConfidence() {
        return syncnetConfidence;
    }

    public void setSyncnetConfidence(double syncnetConfidence) {
        this.syncnetConfidence = syncnetConfidence;
    }

    public double getTrackingStability() {
        return trackingStability;
    }

    public void setTrackingStability(double trackingStability) {
        this.trackingStability = trackingStability;
    }

    public boolean isDevelopmentModel() {
        return isDevelopmentModel;
    }

    public void setDevelopmentModel(boolean developmentModel) {
        isDevelopmentModel = developmentModel;
    }

    public Map<String, Object> getDetails() {
        return details;
    }

    public void setDetails(Map<String, Object> details) {
        this.details = details;
    }
}
