package com.truthlens.backend.service.metadata;

import java.time.OffsetDateTime;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Carrier class holding normalized metadata values and raw hierarchical directory structures
 * extracted from a media asset.
 */
public class ExtractedMetadata {

    private String cameraMake;
    private String cameraModel;
    private String lensModel;
    private String softwareTag;
    private OffsetDateTime capturedAt;
    private OffsetDateTime modifiedAt;
    private Double gpsLatitude;
    private Double gpsLongitude;
    private Double gpsAltitude;
    private Integer width;
    private Integer height;
    private Double durationSeconds;
    private Long bitrate;
    private Double frameRate;
    private String videoCodec;
    private String audioCodec;
    private Integer audioSampleRate;
    private Integer audioChannels;
    private String containerFormat;

    private Map<String, Map<String, String>> rawMetadataTree = new LinkedHashMap<>();
    private String rawJson;
    private String extractionEngine = "JAVA_METADATA_EXTRACTOR";
    private boolean exifPresent = false;

    public ExtractedMetadata() {
    }

    public void addDirectoryTag(String directoryName, String tagName, String tagValue) {
        if (directoryName == null || tagName == null) {
            return;
        }
        rawMetadataTree
                .computeIfAbsent(directoryName, k -> new LinkedHashMap<>())
                .put(tagName, tagValue != null ? tagValue : "");
    }

    // Getters and Setters

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

    public Map<String, Map<String, String>> getRawMetadataTree() {
        return Collections.unmodifiableMap(rawMetadataTree);
    }

    public void setRawMetadataTree(Map<String, Map<String, String>> rawMetadataTree) {
        this.rawMetadataTree = rawMetadataTree != null ? new LinkedHashMap<>(rawMetadataTree) : new LinkedHashMap<>();
    }

    public String getRawJson() {
        return rawJson;
    }

    public void setRawJson(String rawJson) {
        this.rawJson = rawJson;
    }

    public String getExtractionEngine() {
        return extractionEngine;
    }

    public void setExtractionEngine(String extractionEngine) {
        this.extractionEngine = extractionEngine;
    }

    public boolean isExifPresent() {
        return exifPresent;
    }

    public void setExifPresent(boolean exifPresent) {
        this.exifPresent = exifPresent;
    }
}
