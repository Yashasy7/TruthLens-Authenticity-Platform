package com.truthlens.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
 * JPA entity representing extracted forensic metadata and anomaly findings for an ingested media item.
 *
 * <p>Mapped to the {@code metadata} table. Stores normalized EXIF/container headers, camera profiles,
 * timestamps, GPS coordinates, editing software tags, video/audio technical stream parameters,
 * raw hierarchical JSON metadata trees, and flagged forensic anomalies with computed suspicion scores.</p>
 */
@Entity
@Table(name = "metadata")
public class MediaMetadata {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "media_id", nullable = false, unique = true)
    private Media media;

    @Column(name = "camera_make", length = 100)
    private String cameraMake;

    @Column(name = "camera_model", length = 100)
    private String cameraModel;

    @Column(name = "lens_model", length = 150)
    private String lensModel;

    @Column(name = "software_tag", length = 255)
    private String softwareTag;

    @Column(name = "captured_at")
    private OffsetDateTime capturedAt;

    @Column(name = "modified_at")
    private OffsetDateTime modifiedAt;

    @Column(name = "gps_latitude")
    private Double gpsLatitude;

    @Column(name = "gps_longitude")
    private Double gpsLongitude;

    @Column(name = "gps_altitude")
    private Double gpsAltitude;

    @Column(name = "width")
    private Integer width;

    @Column(name = "height")
    private Integer height;

    @Column(name = "duration_seconds")
    private Double durationSeconds;

    @Column(name = "bitrate")
    private Long bitrate;

    @Column(name = "frame_rate")
    private Double frameRate;

    @Column(name = "video_codec", length = 50)
    private String videoCodec;

    @Column(name = "audio_codec", length = 50)
    private String audioCodec;

    @Column(name = "audio_sample_rate")
    private Integer audioSampleRate;

    @Column(name = "audio_channels")
    private Integer audioChannels;

    @Column(name = "container_format", length = 50)
    private String containerFormat;

    @Column(name = "raw_json", columnDefinition = "TEXT")
    private String rawJson;

    @Column(name = "anomaly_flags", columnDefinition = "TEXT")
    private String anomalyFlags;

    @Column(name = "has_anomalies", nullable = false)
    private boolean hasAnomalies = false;

    @Column(name = "anomaly_count", nullable = false)
    private int anomalyCount = 0;

    @Column(name = "forensic_score", nullable = false)
    private double forensicScore = 0.0;

    @Column(name = "extraction_engine", nullable = false, length = 50)
    private String extractionEngine = "JAVA_METADATA_EXTRACTOR";

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public MediaMetadata() {
    }

    public MediaMetadata(Media media) {
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

    public String getCameraMake() {
        return cameraMake;
    }

    public void setCameraMake(String cameraMake) {
        this.cameraMake = cameraMake;
    }

    public String getCameraModel() {
        return cameraModel;
    }

    public void setCameraModel(String cameraModel) {
        this.cameraModel = cameraModel;
    }

    public String getLensModel() {
        return lensModel;
    }

    public void setLensModel(String lensModel) {
        this.lensModel = lensModel;
    }

    public String getSoftwareTag() {
        return softwareTag;
    }

    public void setSoftwareTag(String softwareTag) {
        this.softwareTag = softwareTag;
    }

    public OffsetDateTime getCapturedAt() {
        return capturedAt;
    }

    public void setCapturedAt(OffsetDateTime capturedAt) {
        this.capturedAt = capturedAt;
    }

    public OffsetDateTime getModifiedAt() {
        return modifiedAt;
    }

    public void setModifiedAt(OffsetDateTime modifiedAt) {
        this.modifiedAt = modifiedAt;
    }

    public Double getGpsLatitude() {
        return gpsLatitude;
    }

    public void setGpsLatitude(Double gpsLatitude) {
        this.gpsLatitude = gpsLatitude;
    }

    public Double getGpsLongitude() {
        return gpsLongitude;
    }

    public void setGpsLongitude(Double gpsLongitude) {
        this.gpsLongitude = gpsLongitude;
    }

    public Double getGpsAltitude() {
        return gpsAltitude;
    }

    public void setGpsAltitude(Double gpsAltitude) {
        this.gpsAltitude = gpsAltitude;
    }

    public Integer getWidth() {
        return width;
    }

    public void setWidth(Integer width) {
        this.width = width;
    }

    public Integer getHeight() {
        return height;
    }

    public void setHeight(Integer height) {
        this.height = height;
    }

    public Double getDurationSeconds() {
        return durationSeconds;
    }

    public void setDurationSeconds(Double durationSeconds) {
        this.durationSeconds = durationSeconds;
    }

    public Long getBitrate() {
        return bitrate;
    }

    public void setBitrate(Long bitrate) {
        this.bitrate = bitrate;
    }

    public Double getFrameRate() {
        return frameRate;
    }

    public void setFrameRate(Double frameRate) {
        this.frameRate = frameRate;
    }

    public String getVideoCodec() {
        return videoCodec;
    }

    public void setVideoCodec(String videoCodec) {
        this.videoCodec = videoCodec;
    }

    public String getAudioCodec() {
        return audioCodec;
    }

    public void setAudioCodec(String audioCodec) {
        this.audioCodec = audioCodec;
    }

    public Integer getAudioSampleRate() {
        return audioSampleRate;
    }

    public void setAudioSampleRate(Integer audioSampleRate) {
        this.audioSampleRate = audioSampleRate;
    }

    public Integer getAudioChannels() {
        return audioChannels;
    }

    public void setAudioChannels(Integer audioChannels) {
        this.audioChannels = audioChannels;
    }

    public String getContainerFormat() {
        return containerFormat;
    }

    public void setContainerFormat(String containerFormat) {
        this.containerFormat = containerFormat;
    }

    public String getRawJson() {
        return rawJson;
    }

    public void setRawJson(String rawJson) {
        this.rawJson = rawJson;
    }

    public String getAnomalyFlags() {
        return anomalyFlags;
    }

    public void setAnomalyFlags(String anomalyFlags) {
        this.anomalyFlags = anomalyFlags;
    }

    public boolean isHasAnomalies() {
        return hasAnomalies;
    }

    public void setHasAnomalies(boolean hasAnomalies) {
        this.hasAnomalies = hasAnomalies;
    }

    public int getAnomalyCount() {
        return anomalyCount;
    }

    public void setAnomalyCount(int anomalyCount) {
        this.anomalyCount = anomalyCount;
    }

    public double getForensicScore() {
        return forensicScore;
    }

    public void setForensicScore(double forensicScore) {
        this.forensicScore = forensicScore;
    }

    public String getExtractionEngine() {
        return extractionEngine;
    }

    public void setExtractionEngine(String extractionEngine) {
        this.extractionEngine = extractionEngine;
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
        if (!(o instanceof MediaMetadata that)) return false;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
